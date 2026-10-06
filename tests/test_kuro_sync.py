"""Tests sync serveur : format liste + syntaxe bash + dry-run sans ecriture."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "kuro_sync_server.sh"
LIST = REPO / "scripts" / "sync-repos.txt"


def _entries():
    out = []
    for raw in LIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        name, _, url = line.partition(" ")
        out.append((name.strip(), url.strip()))
    return out


def test_liste_format():
    entries = _entries()
    assert len(entries) >= 2
    names = [n for n, _ in entries]
    assert len(set(names)) == len(names), "doublon dans sync-repos.txt"
    assert "kuro" in names and "kuro-rules" in names
    for name, url in entries:
        assert name and "/" not in name and " " not in name
        assert url.startswith("https://") and url.endswith(".git")


def _find_bash():
    """Premier bash capable de lire le script (Git Bash prefere sous Windows,
    le bash WSL ne voit pas les chemins Windows)."""
    candidates = []
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    if git_bash.exists():
        candidates.append(str(git_bash))
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    for candidate in candidates:
        try:
            r = subprocess.run([candidate, "-n", str(SCRIPT)], capture_output=True,
                               text=True, timeout=60)
        except Exception:
            continue
        if r.returncode == 0:
            return candidate
    return None


def test_bash_syntax():
    assert _find_bash() is not None, "aucun bash capable de lire le script"


def test_dry_run_ne_touche_rien(tmp_path, monkeypatch):
    if sys.platform == "win32":
        pytest.skip("dry-run POSIX : couvert sur le serveur (bash+git natifs)")
    git = shutil.which("git")
    if git is None:
        pytest.skip("git absent")
    home = tmp_path / "home"
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    lst = tmp_path / "sync-repos.txt"
    lst.write_text("demo https://example.invalid/demo.git\n", encoding="utf-8")
    env = dict(os.environ)
    env.update({"HOME": str(home),
                "KURO_DOCS_DIR": str(docs),
                "KURO_SYNC_LIST": str(lst)})
    r = subprocess.run(["bash", str(SCRIPT), "--dry-run"], capture_output=True,
                       text=True, timeout=120, env=env)
    assert "would-clone" in r.stdout
    assert list(docs.iterdir()) == [], "dry-run a ecrit dans DOCS_DIR !"
