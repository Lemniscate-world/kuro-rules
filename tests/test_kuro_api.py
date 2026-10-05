"""Tests kuro_api — get_status tolerant + get_system, zero reseau, zero DB reelle."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import api as kuro_api  # noqa: E402
from kuro_dashboard import system as kuro_system  # noqa: E402


def _empty_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    return conn


def test_get_status_fresh_db_zeros_no_crash(monkeypatch):
    monkeypatch.setattr(kuro_api, "db", _empty_db)
    status = kuro_api.get_status()
    assert status["projects"] == 0
    assert status["sessions"] == 0
    assert status["alerts_open"] == 0
    assert status["memory_nodes"] == 0
    assert status["heartbeat"] is None


def test_get_status_counts_when_tables_exist(monkeypatch):
    conn = _empty_db()
    conn.execute("CREATE TABLE projects (name TEXT)")
    conn.execute("CREATE TABLE sessions (id INTEGER)")
    conn.execute("CREATE TABLE alerts (acknowledged INTEGER)")
    conn.execute("CREATE TABLE memory_nodes (id INTEGER)")
    conn.execute("CREATE TABLE heartbeat (timestamp TEXT)")
    conn.execute("INSERT INTO projects VALUES ('a'), ('b')")
    monkeypatch.setattr(kuro_api, "db", lambda: conn)
    status = kuro_api.get_status()
    assert status["projects"] == 2
    assert status["sessions"] == 0


def test_get_system_snapshot_shape(monkeypatch):
    monkeypatch.setattr(kuro_system, "_gpu", lambda: [])
    monkeypatch.setattr(kuro_system, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    kuro_system._SNAP_CACHE.clear()
    payload = kuro_api.get_system()
    for key in ("generated_at", "host", "cpu", "memory", "disk",
                "network", "sensors", "gpu", "docker", "processes"):
        assert key in payload


def test_count_helper_tolerant():
    conn = _empty_db()
    assert kuro_api._count(conn, "SELECT COUNT(*) AS n FROM nope") == 0
