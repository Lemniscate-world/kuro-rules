"""Tests kuro_promote.sh : check lecture seule, promote avec backup, refus si vieux."""

import os
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "kuro_promote.sh"


def _bash_candidates():
    candidates = []
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    if git_bash.exists():
        candidates.append(str(git_bash))
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    return candidates


def _run_promote(home: Path, *args: str):
    env = dict(os.environ)
    env["KURO_HOME"] = str(home)
    env["KURO_NO_RESTART"] = "1"
    for bash in _bash_candidates():
        try:
            return subprocess.run([bash, str(SCRIPT), *args], capture_output=True,
                                  text=True, timeout=120, env=env)
        except Exception:
            continue
    pytest.skip("aucun bash executable")


def _require_user_manager():
    """do_verify exige 'systemctl --user' FONCTIONNEL (bus user actif).

    Binaire present mais bus absent (conteneur CI) -> is-active echoue et
    le promote rend 3 (partiel) alors que les fichiers sont bons : on skippe,
    la verif services se fait sur machine avec systemd --user reel.
    """
    if not shutil.which("systemctl"):
        return  # Windows : do_verify court-circuite sans systemd, tests valides
    for bash in _bash_candidates():
        try:
            r = subprocess.run([bash, "-c", "systemctl --user list-units >/dev/null 2>&1"],
                               capture_output=True, timeout=30)
            if r.returncode == 0:
                return
        except Exception:
            continue
    pytest.skip("pas de systemd --user fonctionnel ici")


def _make_db(path: Path, projects: int = 1) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE IF NOT EXISTS projects (id INTEGER)")
    for i in range(projects):
        conn.execute("INSERT INTO projects VALUES (?)", (i,))
    conn.commit()
    conn.close()


def _count(path: Path) -> int:
    conn = sqlite3.connect(path)
    n = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]
    conn.close()
    return n


def test_check_sans_replica(tmp_path):
    home = tmp_path / "home"
    (home / ".kuro").mkdir(parents=True)
    r = _run_promote(home, "--check")
    assert r.returncode == 1 and "NO-GO" in r.stdout


def test_promote_echange_avec_backup(tmp_path):
    _require_user_manager()
    home = tmp_path / "home"
    (home / ".kuro").mkdir(parents=True)
    _make_db(home / ".kuro" / "kuro.db", projects=1)
    _make_db(home / ".kuro" / "kuro-replica.db", projects=7)
    r = _run_promote(home, "--promote")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _count(home / ".kuro" / "kuro.db") == 7
    backups = list((home / ".kuro").glob("kuro.db.pre-promote-*"))
    assert len(backups) == 1
    assert _count(backups[0]) == 1


def test_promote_replica_vieux_refuse(tmp_path):
    _require_user_manager()
    home = tmp_path / "home"
    (home / ".kuro").mkdir(parents=True)
    _make_db(home / ".kuro" / "kuro.db", projects=1)
    replica = home / ".kuro" / "kuro-replica.db"
    _make_db(replica, projects=9)
    vieux = time.time() - 3 * 3600
    os.utime(replica, (vieux, vieux))
    r = _run_promote(home, "--promote")
    assert r.returncode == 2
    assert _count(home / ".kuro" / "kuro.db") == 1
    r = _run_promote(home, "--promote", "--force")
    assert r.returncode == 0
    assert _count(home / ".kuro" / "kuro.db") == 9
