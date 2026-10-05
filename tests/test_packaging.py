"""Tests packaging kuro-dashboard : version, static sync, scan smoke."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import kuro_dashboard  # noqa: E402
from kuro_dashboard import api, scan, system  # noqa: E402


def test_version_pep440():
    import re

    assert re.fullmatch(r"\d+\.\d+\.\d+", kuro_dashboard.__version__), \
        "version PyPI doit etre PEP 440 (tag git vX.Y.Z-kuro a part, R19)"


def test_console_entry_points_exist():
    assert callable(api.main)  # kuro-dashboard
    assert callable(system.main)  # kuro-system


def test_static_copies_in_sync():
    """Garde-fou anti-drift : src static = copies exactes de dashboard/."""
    repo = Path(__file__).resolve().parent.parent
    for name in ("index.html", "app.js", "styles.css"):
        packaged = repo / "src" / "kuro_dashboard" / "static" / name
        canonical = repo / "dashboard" / name
        assert packaged.exists(), f"copie manquante: {packaged}"
        assert packaged.read_bytes() == canonical.read_bytes(), \
            f"drift: recopier dashboard/{name} vers src/kuro_dashboard/static/"


def test_scan_smoke_empty_dirs(monkeypatch, tmp_path):
    """build_payload sur dossiers vides : cles presentes, zero crash."""
    monkeypatch.setattr(scan, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(scan, "DASHBOARD_DIR", tmp_path / "dashboard")
    monkeypatch.setattr(scan, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(scan, "KNOWLEDGE_DIR", tmp_path / "kb")
    monkeypatch.setattr(scan, "PROJECTS_FILE", tmp_path / "projects.txt")
    monkeypatch.setattr(scan, "EXCLUDE_FILE", tmp_path / "exclude.txt")
    monkeypatch.setattr(scan, "AGENTS_FILE", tmp_path / "AGENTS.md")
    monkeypatch.setattr(scan, "SYNC_LOG_FILE", tmp_path / "SYNC_LOG.md")
    monkeypatch.setattr(scan, "KURO_DB_FILE", tmp_path / "kuro.db")
    payload = scan.build_payload()
    assert payload["summary"]["trackedProjects"] == 0
    assert payload["kuroDaemon"]["status"] in ("inactive", "error")
    assert "generatedAt" in payload


def test_litellm_example_valide():
    yaml = pytest.importorskip("yaml")
    repo = Path(__file__).resolve().parent.parent
    cfg = yaml.safe_load(
        (repo / "litellm-config.example.yaml").read_text(encoding="utf-8"))
    models = [m["model_name"] for m in cfg["model_list"]]
    assert "kuro-brain" in models
    assert len(cfg["model_list"]) >= 3
    assert cfg["router_settings"]["fallbacks"]


def _save_scan_cache():
    return dict(scan._PAYLOAD_CACHE)


def _restore_scan_cache(saved):
    scan._PAYLOAD_CACHE.clear()
    scan._PAYLOAD_CACHE.update(saved)


def test_build_payload_cache_hit():
    saved = _save_scan_cache()
    try:
        scan._PAYLOAD_CACHE["payload"] = {"ok": True}
        import time as _time
        scan._PAYLOAD_CACHE["ts"] = _time.monotonic()
        assert scan.build_payload() == {"ok": True}
    finally:
        _restore_scan_cache(saved)


def test_build_payload_stale_rebuilds(monkeypatch):
    saved = _save_scan_cache()
    try:
        scan._PAYLOAD_CACHE["payload"] = {"ok": "stale"}
        scan._PAYLOAD_CACHE["ts"] = 0.0
        monkeypatch.setattr(scan, "parse_list_file", lambda path: [])
        monkeypatch.setattr(scan, "detect_git_repositories", lambda: [])
        payload = scan.build_payload()
        assert payload.get("ok") is None
        assert "generatedAt" in payload
    finally:
        _restore_scan_cache(saved)


def test_run_git_timeout(monkeypatch):
    import subprocess as _sp

    def _boom(*a, **k):
        raise _sp.TimeoutExpired(cmd="git", timeout=1)

    monkeypatch.setattr(scan.subprocess, "run", _boom)
    result = scan.run_git(Path("."))
    assert result.ok is False and "timeout" in result.output
