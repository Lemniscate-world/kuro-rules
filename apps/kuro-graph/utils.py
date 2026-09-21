"""Utilitaires transverses kuro-graph : retry, timers, checkpoint, gardes.

Stdlib uniquement ici. LangGraph/SQLite optionnels resolus au runtime
pour ne jamais casser scripts/ ni le POC sans dependances.
"""

from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def vacances_on() -> bool:
    try:
        import kuro_proposals as proposals

        return bool(proposals.vacances())
    except Exception:
        return os.environ.get("KURO_VACANCES") == "1"


def approval_required(state: dict[str, Any]) -> bool:
    # Toute ecriture reelle exige approbation explicite + hors vacances.
    if not state.get("write"):
        return False
    if state.get("dry_run", True):
        return False
    if vacances_on():
        return False
    return True


def is_approved(state: dict[str, Any]) -> bool:
    if not approval_required(state):
        return False
    return bool(state.get("human_approved"))


def with_retry(fn: Callable[[dict[str, Any]], dict[str, Any]], attempts: int = 2):
    """Wrapper retry 1x sur echec marque (ok=False), sans exception masquee."""

    def _wrapped(state: dict[str, Any]) -> dict[str, Any]:
        out = fn(state)
        steps = out.get("steps", {})
        name = getattr(fn, "__name__", "node")
        info = steps.get(name, {}) if isinstance(steps, dict) else {}
        if info.get("ok", True):
            return out
        if attempts <= 1:
            return out
        retries = dict(out.get("retries", {}))
        retries[name] = retries.get(name, 0) + 1
        out2 = {**out, "retries": retries}
        second = fn(out2)
        steps2 = dict(second.get("steps", {}))
        prev = dict(steps2.get(name, {}))
        prev["retried"] = True
        steps2[name] = prev
        return {**second, "steps": steps2}

    _wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    return _wrapped


def timed(fn: Callable[[dict[str, Any]], dict[str, Any]]):
    """Mesure duree par noeud en secondes, stockee dans metrics.durations."""

    def _wrapped(state: dict[str, Any]) -> dict[str, Any]:
        start = time.monotonic()
        out = fn(state)
        elapsed = round(time.monotonic() - start, 3)
        metrics = dict(out.get("metrics", {}))
        durations = dict(metrics.get("durations", {}))
        durations[getattr(fn, "__name__", "node")] = elapsed
        metrics["durations"] = durations
        return {**out, "metrics": metrics}

    _wrapped.__name__ = getattr(fn, "__name__", "timed")
    return _wrapped


def checkpoint_path(custom: str | None = None) -> Path:
    if custom:
        return Path(custom)
    base = Path(os.environ.get("KURO_GRAPH_STATE_DIR", str(ROOT / "logs")))
    base.mkdir(parents=True, exist_ok=True)
    return base / "kuro-graph-checkpoints.sqlite3"


def save_checkpoint(path: Path, thread_id: str, state: dict[str, Any]) -> bool:
    try:
        import json

        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path))
        conn.execute("CREATE TABLE IF NOT EXISTS checkpoints (thread_id TEXT PRIMARY KEY, state TEXT)")
        conn.execute(
            "INSERT OR REPLACE INTO checkpoints (thread_id, state) VALUES (?, ?)",
            (thread_id, json.dumps(state, default=str)),
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def load_checkpoint(path: Path, thread_id: str) -> dict[str, Any] | None:
    try:
        import json

        if not path.exists():
            return None
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        row = conn.execute("SELECT state FROM checkpoints WHERE thread_id = ?", (thread_id,)).fetchone()
        conn.close()
        if not row:
            return None
        data = json.loads(row[0])
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def merge_metrics(state: dict[str, Any]) -> dict[str, Any]:
    """Resume metriques pour logs : durees + fails + halt."""
    metrics = dict(state.get("metrics", {}).get("durations", {}))
    return {
        "durations": metrics,
        "fails": int(state.get("fails", 0)),
        "halted": bool(state.get("halted")),
        "retries": dict(state.get("retries", {})),
    }
