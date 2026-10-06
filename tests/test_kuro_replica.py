"""Tests replica push (PC) : backup API + commandes scp/ssh, jamais de reseau."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_replica_push as push  # noqa: E402


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE projects (id INTEGER, name TEXT)")
    conn.execute("INSERT INTO projects VALUES (1, 'a'), (2, 'b')")
    conn.commit()
    conn.close()


def test_snapshot_copie_coherente(tmp_path):
    src = tmp_path / "kuro.db"
    dst = tmp_path / "snap.db"
    _make_db(src)
    assert push.snapshot_db(src, dst) is True
    conn = sqlite3.connect(dst)
    assert conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 2
    conn.close()


def test_snapshot_source_absente(tmp_path):
    assert push.snapshot_db(tmp_path / "nope.db", tmp_path / "snap.db") is False


def test_push_dry_run_sans_reseau(monkeypatch, tmp_path):
    src = tmp_path / "kuro.db"
    _make_db(src)
    monkeypatch.setattr(push, "SRC_DB", src)

    def _boom(*a, **k):
        raise AssertionError("aucun reseau en dry-run")

    monkeypatch.setattr(push.subprocess, "run", _boom)
    assert push.push("hote", dry_run=True) == 0


def test_push_succes_commandes(monkeypatch, tmp_path):
    src = tmp_path / "kuro.db"
    _make_db(src)
    monkeypatch.setattr(push, "SRC_DB", src)
    calls = []

    class _Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake(cmd, **kwargs):
        calls.append(cmd)
        return _Done()

    monkeypatch.setattr(push.subprocess, "run", _fake)
    assert push.push("hote") == 0
    scp = next(c for c in calls if c[0] == "scp")
    ssh = next(c for c in calls if c[0] == "ssh")
    assert "BatchMode=yes" in scp
    assert scp[-1].endswith("kuro-replica.db.tmp")
    assert "mv" in ssh[-1] and "kuro-replica.db.tmp" in ssh[-1]


def test_push_scp_echec(monkeypatch, tmp_path):
    src = tmp_path / "kuro.db"
    _make_db(src)
    monkeypatch.setattr(push, "SRC_DB", src)

    class _Fail:
        returncode = 1
        stdout = ""
        stderr = "erreur"

    monkeypatch.setattr(push.subprocess, "run", lambda *a, **k: _Fail())
    assert push.push("hote") == 1


def test_push_sans_source(monkeypatch, tmp_path):
    monkeypatch.setattr(push, "SRC_DB", tmp_path / "nope.db")
    assert push.push("hote") == 1
