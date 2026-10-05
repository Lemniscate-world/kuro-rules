"""Tests kuro_state — snapshot DB locale, lecture seule, zero daemon requis."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import kuro_state  # noqa: E402


def _make_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE projects (id INTEGER, name TEXT)")
    conn.execute("CREATE TABLE sessions (id INTEGER)")
    conn.execute(
        "CREATE TABLE alerts (id INTEGER, alert_type TEXT, message TEXT,"
        " severity TEXT, acknowledged INTEGER, created_at TEXT, project_id INTEGER)"
    )
    conn.execute("CREATE TABLE memory_nodes (id INTEGER)")
    conn.execute("CREATE TABLE heartbeat (timestamp TEXT)")
    conn.execute("INSERT INTO projects VALUES (1, 'a'), (2, 'b')")
    conn.execute("INSERT INTO sessions VALUES (1)")
    conn.execute(
        "INSERT INTO alerts VALUES (1, 't', 'boom', 'high', 0,"
        " '2026-10-03 10:00:00', 1)"
    )
    conn.execute(
        "INSERT INTO alerts VALUES (2, 't', 'vieux', 'low', 1,"
        " '2026-09-01 10:00:00', 1)"
    )
    # battement futur = age bloque a 0 (deterministe, pas de flaky)
    conn.execute("INSERT INTO heartbeat VALUES ('2099-01-01 00:00:00')")
    conn.commit()
    conn.close()


def test_full_snapshot(monkeypatch, tmp_path):
    db = tmp_path / "kuro.db"
    _make_db(db)
    monkeypatch.setattr(kuro_state, "DB_PATH", db)
    snap = kuro_state.collect_kuro_snapshot()
    assert snap["db_present"] is True
    assert snap["projects"] == 2
    assert snap["sessions"] == 1
    assert snap["alerts_open"] == 1
    assert snap["memory_nodes"] == 0
    assert snap["heartbeat_age_min"] == 0.0
    assert len(snap["recent_alerts"]) == 1
    assert snap["recent_alerts"][0]["message"] == "boom"


def test_missing_db(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_state, "DB_PATH", tmp_path / "nope.db")
    snap = kuro_state.collect_kuro_snapshot()
    assert snap["db_present"] is False
    assert snap["projects"] == 0
    assert snap["recent_alerts"] == []


def test_db_path_env_override(monkeypatch, tmp_path):
    db = tmp_path / "autre.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE projects (id INTEGER)")
    conn.execute("INSERT INTO projects VALUES (1)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("KURO_DB_PATH", str(db))
    snap = kuro_state.collect_kuro_snapshot()
    assert snap["db_present"] is True
    assert snap["projects"] == 1
    assert snap["db_path"] == str(db)
    assert isinstance(snap["file_age_min"], float)


def _make_projects(path: Path, n: int) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE projects (id INTEGER)")
    for i in range(n):
        conn.execute("INSERT INTO projects VALUES (?)", (i,))
    conn.commit()
    conn.close()


def test_replica_absent(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_state, "DB_PATH", tmp_path / "live.db")
    monkeypatch.setenv("KURO_REPLICA_PATH", str(tmp_path / "nope.db"))
    snap = kuro_state.collect_kuro_snapshot()
    assert snap["replica"] is None


def test_replica_lu_si_different(monkeypatch, tmp_path):
    live = tmp_path / "live.db"
    rep = tmp_path / "rep.db"
    _make_projects(live, 1)
    _make_projects(rep, 63)
    monkeypatch.setattr(kuro_state, "DB_PATH", live)
    monkeypatch.setenv("KURO_REPLICA_PATH", str(rep))
    snap = kuro_state.collect_kuro_snapshot()
    assert snap["projects"] == 1
    assert snap["replica"]["projects"] == 63
    assert isinstance(snap["replica"]["file_age_min"], float)


def test_replica_ignore_si_meme_fichier(monkeypatch, tmp_path):
    db = tmp_path / "same.db"
    _make_projects(db, 2)
    monkeypatch.setattr(kuro_state, "DB_PATH", db)
    monkeypatch.setenv("KURO_REPLICA_PATH", str(db))
    snap = kuro_state.collect_kuro_snapshot()
    assert snap["replica"] is None
