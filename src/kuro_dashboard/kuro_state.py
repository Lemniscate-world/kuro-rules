#!/usr/bin/env python3
"""kuro_state.py — etat Kuro lu depuis ~/.kuro/kuro.db (lecture seule).

Utilise par Xenon (ex kuro-glances) : marche meme si l API est eteinte,
aucun reseau, aucune ecriture, jamais d exception levee.
"""

from __future__ import annotations

import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path.home() / ".kuro" / "kuro.db"


def _db_path() -> Path:
    """Base lue : $KURO_DB_PATH si defini (replica), sinon la base locale."""
    env = os.environ.get("KURO_DB_PATH")
    return Path(env) if env else DB_PATH


def _connect() -> sqlite3.Connection | None:
    try:
        db = _db_path()
        if not db.exists():
            return None
        conn = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception:
        return None


def _rows(conn: sqlite3.Connection, sql: str, params: tuple = ()) -> list[dict]:
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except Exception:
        return []


def _count(conn: sqlite3.Connection, sql: str) -> int:
    found = _rows(conn, sql)
    try:
        return int(found[0].get("n", 0)) if found else 0
    except Exception:
        return 0


def _heartbeat(conn: sqlite3.Connection) -> tuple[dict | None, float | None]:
    found = _rows(conn, "SELECT * FROM heartbeat ORDER BY timestamp DESC LIMIT 1")
    if not found:
        return None, None
    hb = found[0]
    try:
        # battement ecrit en heure locale par le daemon (datetime('now'))
        ts = datetime.strptime(str(hb.get("timestamp"))[:19], "%Y-%m-%d %H:%M:%S")
        age = max(0.0, (datetime.now() - ts).total_seconds() / 60)
        return hb, age
    except Exception:
        return hb, None


# Dossiers regenerables ou hors sujet : jamais descendus (un rglob naif
# met 60 s+ : target/ de 13 Go, node_modules, .git...).
_SKIP_WALK = {"target", "node_modules", ".venv", "venv", "dist", "build",
              ".next", ".pytest_cache", ".mypy_cache", ".hypothesis",
              ".tox", ".eggs", "__pycache__", ".idea", ".vscode",
              ".obsidian", ".trash", ".tmp.driveupload", "coverage"}
_FS_CACHE: dict[str, Any] = {"ts": 0.0, "signals": {}}
_FS_TTL = 120.0


def _count_summaries(base: Path) -> int:
    """SESSION_SUMMARY.md sous base, walk elague (jamais d exception)."""
    found = 0
    try:
        stack = [base]
        while stack:
            cur = stack.pop()
            try:
                with os.scandir(cur) as it:
                    entries = list(it)
            except Exception:
                continue
            for entry in entries:
                try:
                    if entry.is_dir(follow_symlinks=False):
                        name = entry.name
                        if name in _SKIP_WALK or name.startswith("."):
                            continue
                        stack.append(entry.path)
                    elif (entry.is_file(follow_symlinks=False)
                          and entry.name == "SESSION_SUMMARY.md"):
                        found += 1
                except Exception:
                    continue
    except Exception:  # pragma: no cover - boucle protegee partout dedans
        pass
    return found


def _count_git_dirs(roots: list[Path]) -> int:
    """Depots git un niveau sous les racines (rapide, sans sous-processus).

    ~/repos n'existe pas sur toutes les machines (Windows : tout est sous
    ~/Documents) — compter ses dossiers bruts affichait "0 repos" alors que
    le sensing git en voyait 50+. On compte les enfants avec un .git.
    """
    seen: set[str] = set()
    try:
        for root in roots:
            try:
                if not root.is_dir():
                    continue
                children = list(root.iterdir())
            except Exception:
                continue
            for child in children:
                try:
                    if not child.is_dir() or (child / ".git").is_file():
                        continue
                    if not (child / ".git").exists():
                        continue
                    try:
                        key = str(child.resolve())
                    except Exception:
                        key = str(child)
                    seen.add(key)
                except Exception:
                    continue
    except Exception:
        pass
    return len(seen)


def _project_roots() -> list[Path]:
    """Racines scannees : env KURO_PROJECTS_ROOTS sinon ~/repos + ~/Documents."""
    try:
        from .projects import roots as _roots
        return list(_roots())
    except Exception:
        pass
    try:
        raw = os.environ.get("KURO_PROJECTS_ROOTS")
        if raw:
            return [Path(p.strip()).expanduser()
                    for p in raw.split(os.pathsep) if p.strip()]
    except Exception:
        pass
    try:
        return [Path.home() / "repos", Path.home() / "Documents"]
    except Exception:
        return []


def _fs_signals() -> dict[str, Any]:
    """Signaux reels disque (jamais d exception) : depots git + SESSION_SUMMARY."""
    now = time.monotonic()
    try:
        if _FS_CACHE["signals"] and (now - _FS_CACHE["ts"]) < _FS_TTL:
            return dict(_FS_CACHE["signals"])
    except Exception:
        pass
    repos = 0
    summaries = 0
    try:
        repos = _count_git_dirs(_project_roots())
    except Exception:  # pragma: no cover - _project_roots() ne leve plus
        repos = 0
    try:
        for base in (Path.home() / "Documents", Path.home() / "repos"):
            if base.is_dir():
                summaries += _count_summaries(base)
    except Exception:
        pass
    signals = {"repos_fs": repos, "summaries_fs": summaries}
    _FS_CACHE.update({"ts": now, "signals": signals})
    return dict(signals)


def _hb_detail(hb: dict | None) -> dict[str, Any]:
    """Champs utiles du battement daemon (tolerant, cles absentes -> None)."""
    if not isinstance(hb, dict):
        return {"hb_projects_scanned": None, "hb_alerts_active": None,
                "hb_hostname": None, "hb_status": None}
    try:
        scanned = hb.get("projects_scanned")
        scanned = int(scanned) if scanned is not None else None
    except Exception:
        scanned = None
    try:
        active = hb.get("alerts_active")
        active = int(active) if active is not None else None
    except Exception:
        active = None
    return {"hb_projects_scanned": scanned, "hb_alerts_active": active,
            "hb_hostname": hb.get("hostname"), "hb_status": hb.get("status")}


def _file_age_min() -> float | None:
    """Age du fichier DB en minutes (fraicheur du replica)."""
    try:
        return max(0.0, (datetime.now() - datetime.fromtimestamp(
            _db_path().stat().st_mtime)).total_seconds() / 60)
    except Exception:
        return None


def _replica_snapshot(live: Path) -> dict | None:
    """La copie du primaire, si elle existe et differe du live (lecture seule)."""
    try:
        env = os.environ.get("KURO_REPLICA_PATH")
        replica = Path(env) if env else Path.home() / ".kuro" / "kuro-replica.db"
        if not replica.exists() or replica.resolve() == live.resolve():
            return None
        conn = sqlite3.connect(f"file:{replica}?mode=ro", uri=True, timeout=5)
        try:
            row = conn.execute("SELECT COUNT(*) FROM projects").fetchone()
            projects = int(row[0]) if row else 0
        finally:
            try:
                conn.close()
            except Exception:
                pass
        age = max(0.0, (datetime.now() - datetime.fromtimestamp(
            replica.stat().st_mtime)).total_seconds() / 60)
        return {"projects": projects, "file_age_min": age}
    except Exception:
        return None


def collect_kuro_snapshot() -> dict[str, Any]:
    """Etat Kuro : battement daemon + compteurs + 5 dernieres alertes + signaux disque.

    CONTRAT (precedence assumee, voir tests/test_kuro_state.py) :
    - les cles projects/sessions/alerts_open/memory_nodes refletent la DB
      legacy (daemon v1) ; le daemon actuel n y ecrit plus -> souvent 0 ;
    - repos_fs/summaries_fs/hb_* sont les signaux reels (disque + battement) ;
    - l affichage (tui.sec_kuro) montre les comptes EFFECTIFS
      (max DB, disque) et ne depend jamais d une table seule.
    """
    live = _db_path()
    base = {"db_present": False, "heartbeat": None, "heartbeat_age_min": None,
            "projects": 0, "sessions": 0, "alerts_open": 0,
            "memory_nodes": 0, "recent_alerts": [],
            "db_path": str(live), "file_age_min": _file_age_min(),
            "replica": _replica_snapshot(live)}
    base.update(_fs_signals())
    base.update(_hb_detail(None))
    conn = _connect()
    if conn is None:
        return base
    try:
        hb, age = _heartbeat(conn)
        alerts = _rows(
            conn,
            """SELECT a.severity, a.message, a.created_at, p.name AS project
               FROM alerts a LEFT JOIN projects p ON p.id = a.project_id
               WHERE a.acknowledged = 0 ORDER BY a.created_at DESC LIMIT 5""",
        )
        out = {
            **base,
            "db_present": True,
            "heartbeat": hb,
            "heartbeat_age_min": age,
            "projects": _count(conn, "SELECT COUNT(*) AS n FROM projects"),
            "sessions": _count(conn, "SELECT COUNT(*) AS n FROM sessions"),
            "alerts_open": _count(
                conn, "SELECT COUNT(*) AS n FROM alerts WHERE acknowledged = 0"),
            "memory_nodes": _count(conn, "SELECT COUNT(*) AS n FROM memory_nodes"),
            "recent_alerts": alerts,
        }
        out.update(_hb_detail(hb))
        return out
    finally:
        try:
            conn.close()
        except Exception:
            pass
