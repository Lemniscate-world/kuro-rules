"""Tests doctor dashboard + allowlist autodebug (pur, sans reseau sauf loopback)."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_autodebug as autodebug  # noqa: E402
import kuro_doctor as doctor  # noqa: E402


def test_allowlist_couvre_src_pas_packaging():
    ok, _ = autodebug.is_allowed_path("src/kuro_dashboard/tui.py")
    assert ok is True
    ok, _ = autodebug.is_allowed_path("dashboard/app.js")
    assert ok is True
    for banned in ("packaging/deb/control", "src/x/../.env", ".env",
                   "finances.local.json"):
        ok, _ = autodebug.is_allowed_path(banned)
        assert ok is False, banned


def _suspend_package():
    """Retire kuro_dashboard* de sys.modules en gardant les originaux."""
    return {m: sys.modules.pop(m) for m in list(sys.modules)
            if m == "kuro_dashboard" or m.startswith("kuro_dashboard.")}


def _restore_package(stashed):
    """Vire les faux modules importes entre-temps, restaure les originaux."""
    for m in list(sys.modules):
        if m == "kuro_dashboard" or m.startswith("kuro_dashboard."):
            del sys.modules[m]
    sys.modules.update(stashed)


def test_package_ok_et_ko(tmp_path, monkeypatch):
    pkg = tmp_path / "src" / "kuro_dashboard"
    pkg.mkdir(parents=True)
    # __init__.py OBLIGATOIRE : sinon paquet namespace, et le vrai paquet
    # (regulier) du repo gagne toujours sur le faux (PEP 420).
    (pkg / "__init__.py").write_text('__version__ = "0.0"\n', encoding="utf-8")
    for mod in ("api", "face", "kuro_state", "scan", "system", "tui"):
        (pkg / f"{mod}.py").write_text("X = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path / "src"))
    stashed = _suspend_package()
    try:
        ok, detail = doctor.dashboard_package_ok(tmp_path)
        assert ok is True and "6 modules" in detail
        (pkg / "tui.py").write_text("def broken(:\n", encoding="utf-8")
        _suspend_package()  # vire les faux modules caches (taille changee)
        ok, _ = doctor.dashboard_package_ok(tmp_path)
        assert ok is False
    finally:
        _restore_package(stashed)


def test_commands_ok():
    ok, detail = doctor.tui_commands_ok()
    assert isinstance(ok, bool) and isinstance(detail, str)


def test_resync_et_purge(tmp_path):
    dash = tmp_path / "dashboard"
    static = tmp_path / "src" / "kuro_dashboard" / "static"
    static.mkdir(parents=True)
    dash = tmp_path / "dashboard"
    dash.mkdir(parents=True, exist_ok=True)
    (dash / "index.html").write_text("<p>v2</p>", encoding="utf-8")
    (static / "index.html").write_text("<p>v1</p>", encoding="utf-8")
    assert doctor.resync_static(tmp_path) is True
    assert (static / "index.html").read_text(encoding="utf-8") == "<p>v2</p>"
    cache = tmp_path / "x" / "__pycache__"
    cache.mkdir(parents=True)
    assert doctor.purge_pycache(tmp_path) >= 1
    assert not cache.exists()


def test_live_offline(tmp_path, monkeypatch):
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "src" / "kuro_dashboard" / "static").mkdir(parents=True)
    monkeypatch.setattr(doctor, "DASHBOARD_FILES", ())
    monkeypatch.setattr(doctor, "DASHBOARD_GLOBS", ())
    ok, detail = doctor.dashboard_live_ok(tmp_path, api_base="http://127.0.0.1:9")
    assert ok is False and "injoignable" in detail


def test_live_null_bytes(tmp_path, monkeypatch):
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "src" / "kuro_dashboard" / "static").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "x.py").write_bytes(b"a = 1\n\x00\x01\x02")
    monkeypatch.setattr(doctor, "DASHBOARD_FILES", ())
    ok, detail = doctor.dashboard_live_ok(tmp_path, api_base="http://127.0.0.1:9")
    assert ok is False and "octets nuls: x.py" in detail


def test_push_frais(tmp_path):
    log = tmp_path / "replica-push.log"
    log.write_text("[replica-push] replica a jour (04:00:00Z)\n", encoding="utf-8")
    ok, detail = doctor.push_freshness(log, 3.0)
    assert ok is True and "replica distant" in detail


def test_push_jamais(tmp_path):
    ok, detail = doctor.push_freshness(tmp_path / "nope.log", None)
    assert ok is False and "aucun push" in detail


def test_push_vieux(tmp_path):
    log = tmp_path / "replica-push.log"
    log.write_text("x\n", encoding="utf-8")
    vieux = time.time() - 2 * 3600
    os.utime(log, (vieux, vieux))
    ok, detail = doctor.push_freshness(log, 1.0)
    assert ok is False and "min" in detail


def test_push_silencieux_malgre_log_frais(tmp_path):
    log = tmp_path / "replica-push.log"
    log.write_text("x\n", encoding="utf-8")
    ok, detail = doctor.push_freshness(log, 99.0)
    assert ok is False and "n arrive pas" in detail
