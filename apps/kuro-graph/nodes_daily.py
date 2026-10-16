"""Noeuds daily : wrappers import-first des scripts existants.

Chaque noeud ne fait qu'une chose (SRP), ne leve jamais d'exception
(R7 : echec explicite dans l'etat), et respecte dry-run/write.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _record(state: dict[str, Any], name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    steps = dict(state.get("steps", {}))
    steps[name] = {"ok": ok, "detail": detail[:500]}
    fails = int(state.get("fails", 0)) + (0 if ok else 1)
    return {**state, "steps": steps, "fails": fails}


def _safe_call(state: dict[str, Any], name: str, flag: str, modname: str, **kwargs) -> dict[str, Any]:
    """Appelle modname.main() sans jamais lever : echec explicite dans l'etat (R7)."""
    try:
        rc = importlib.import_module(modname).main(**kwargs)
    except SystemExit as exc:  # NOSONAR S5754 - contrat noeud : capter l'exit, pas le propager
        rc = exc.code
    except Exception as exc:
        out = _record(state, name, False, f"error: {exc}")
        out[flag] = False
        return out
    ok = rc in (None, 0)
    out = _record(state, name, ok, f"rc={rc}")
    out[flag] = ok
    return out


def node_doctor(state: dict[str, Any]) -> dict[str, Any]:
    return _safe_call(state, "doctor", "doctor_ok", "kuro_doctor", fix=False)


def node_truth(state: dict[str, Any]) -> dict[str, Any]:
    # Si doctor KO, on continue en lecture seule mais on le trace.
    # Le HALT dur est reserve au graphe validation, pas au daily.
    return _safe_call(state, "truth", "truth_ok", "audit_truth_daily")


def node_portfolio(state: dict[str, Any]) -> dict[str, Any]:
    return _safe_call(state, "portfolio", "portfolio_ok", "generate_portfolio")


def node_strategy(state: dict[str, Any]) -> dict[str, Any]:
    # Lecture seule : kuro_strategy.main() sans --discord.
    return _safe_call(state, "strategy", "strategy_ok", "kuro_strategy")


def should_publish(state: dict[str, Any]) -> str:
    """Branche conditionnelle : publish seulement si write + etapes critiques OK."""
    if state.get("halted"):
        return "end"
    if state.get("write") and state.get("doctor_ok") and state.get("truth_ok"):
        return "publish"
    return "end"


def node_publish(state: dict[str, Any]) -> dict[str, Any]:
    # Garde-fou : en dry-run on ne pousse jamais.
    if state.get("dry_run", True) or not state.get("write", False):
        return _record(state, "publish", True, "skipped: dry-run or write=False")
    try:
        import utils as guards

        if guards.vacances_on():
            return _record(state, "publish", True, "skipped: vacances mode lecture seule")
        if not guards.is_approved(state):
            return _record(state, "publish", True, "skipped: human approval missing (--approve)")
    except Exception:
        return _record(state, "publish", True, "skipped: approval check unavailable")
    # Le push reel reste dans kuro_automate.git_publish (Q8 avant tout remplacement).
    return _record(state, "publish", True, "approved but push deferred to kuro_automate.git_publish")
