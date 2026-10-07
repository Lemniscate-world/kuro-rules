"""Tests projects.py — sensing git generique (repos temporaires, hermetique)."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import (
    projects,  # noqa: E402
    tui,  # noqa: E402
)

git = pytest.mark.skipif(not shutil.which("git"), reason="git requis")


@pytest.fixture(autouse=True)
def _fresh_cache():
    projects._CACHE.update({"ts": 0.0, "repos": []})
    yield
    projects._CACHE.update({"ts": 0.0, "repos": []})


def _repo(path: Path, dirty: bool = False) -> None:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=path, check=True)
    if dirty:
        (path / "f.txt").write_text("x-modifie", encoding="utf-8")


@git
def test_discover_counts_and_dirty(tmp_path, monkeypatch):
    _repo(tmp_path / "clean")
    _repo(tmp_path / "sale", dirty=True)
    (tmp_path / "nogit").mkdir()
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    projects._CACHE.update({"ts": 0.0, "repos": []})
    found = projects.discover(force=True)
    by_name = {r["name"]: r for r in found}
    assert set(by_name) == {"clean", "sale"}
    assert by_name["sale"]["dirty"] >= 1
    assert by_name["clean"]["dirty"] == 0
    info = projects.summary()
    assert info["count"] == 2 and info["dirty"] == 1


@git
def test_quick_lines_shape(tmp_path, monkeypatch):
    _repo(tmp_path / "sale", dirty=True)
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    projects._CACHE.update({"ts": 0.0, "repos": []})
    lines = projects.quick_lines()
    assert lines[0].startswith("PROJETS git : 1 (1 sales)")
    assert "sale" in lines[1]


def test_sec_projects_hidden_when_db_full():
    kuro = {"db_present": True, "projects": 5}
    assert tui.sec_projects(kuro) == []


def test_sec_projects_never_raises(monkeypatch, tmp_path):
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path / "vide-inexistant"))
    projects._CACHE.update({"ts": 0.0, "repos": []})
    assert tui.sec_projects(None) == ["PROJETS git : 0 (0 sales)"]
