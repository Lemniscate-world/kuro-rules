"""Noeuds daily : wrappers import-first des scripts existants.

Chaque noeud ne fait qu'une chose (SRP), ne leve jamais d'exception
(R7 : echec explicite dans l'etat), et respecte dry-run/write.
"""

from __future__ import annotations

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


def node_doctor(state: dict[str, Any]) -> dict[str, Any]:
    try:
        import kuro_doctor as doc

        rc = doc.main(fix=False)
        ok = rc in (None, 0)
        out = _record(state, "doctor", ok, f"rc={rc}")
        out["doctor_ok"] = ok
        return out
    except SystemExit as exc:
        ok = exc.code in (None, 0)
        out = _record(state, "doctor", ok, f"SystemExit code={exc.code}")
        out["doctor_ok"] = ok
        return out
    except Exception as exc:
        out = _record(state, "doctor", False, f"error: {exc}")
        out["doctor_ok"] = False
        return out


def node_truth(state: dict[str, Any]) -> dict[str, Any]:
    # Si doctor KO, on continue en lecture seule mais on le trace.
    # Le HALT dur est reserve au graphe validation, pas au daily.
    try:
        import audit_truth_daily as truth

        # audit_truth_daily.main() lit argv ; on l'appelle en mode
        # programmatique minimal via sa fonction run() si dispo.
        if hasattr(truth, "run") and False:  # garde-fou : ne pas deviner l'API
            pass
        rc = truth.main()
        ok = rc in (None, 0)
        out = _record(state, "truth", ok, f"rc={rc}")
        out["truth_ok"] = ok
        return out
    except SystemExit as exc:
        ok = exc.code in (None, 0)
        out = _record(state, "truth", ok, f"SystemExit code={exc.code}")
        out["truth_ok"] = ok
        return out
    except Exception as exc:
        out = _record(state, "truth", False, f"error: {exc}")
        out["truth_ok"] = False
        return out


def node_portfolio(state: dict[str, Any]) -> dict[str, Any]:
    try:
        import generate_portfolio as portfolio

        rc = portfolio.main()
        ok = rc in (None, 0)
        out = _record(state, "portfolio", ok, f"rc={rc}")
        out["portfolio_ok"] = ok
        return out
    except SystemExit as exc:
        ok = exc.code in (None, 0)
        out = _record(state, "portfolio", ok, f"SystemExit code={exc.code}")
        out["portfolio_ok"] = ok
        return out
    except Exception as exc:
        out = _record(state, "portfolio", False, f"error: {exc}")
        out["portfolio_ok"] = False
        return out


def node_strategy(state: dict[str, Any]) -> dict[str, Any]:
    # Lecture seule par defaut : kuro_strategy.main() sans --discord.
    # L'envoi Discord reste derriere write=True et sera ajoute en Q4 (human-in-loop).
    try:
        import kuro_strategy as strategy

        rc = strategy.main()
        ok = rc in (None, 0)
        out = _record(state, "strategy", ok, f"rc={rc}")
        out["strategy_ok"] = ok
        return out
    except SystemExit as exc:
        ok = exc.code in (None, 0)
        out = _record(state, "strategy", ok, f"SystemExit code={exc.code}")
        out["strategy_ok"] = ok
        return out
    except Exception as exc:
        out = _record(state, "strategy", False, f"error: {exc}")
        out["strategy_ok"] = False
        return out


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
