"""Noeuds validation R115 : 5 gates avec HALT reel.

Seuils repris a l'identique de rules/rule_115_validation_pipeline.md.
Aucun seuil invente ici : les stages recoivent leurs metriques en entree
et appliquent uniquement la comparaison gate.
"""

from __future__ import annotations

from typing import Any

# Gates R115 : nom stage -> (metrique attendue, predicat de succes).
# Les valeurs d'entree viennent des rapports JSON existants
# (fuzzer_results.json, stress_results.json, ...). Ici on ne fait que decider.
GATES = (
    "fuzzer",
    "stress",
    "combinatorial",
    "oos",
    "benchmark",
)


def _halt(state: dict[str, Any], stage: str, reason: str, results: dict[str, Any]) -> dict[str, Any]:
    merged = dict(state.get("validation_results", {}))
    merged[stage] = results
    steps = dict(state.get("steps", {}))
    steps[f"validation:{stage}"] = {"ok": False, "detail": reason[:500]}
    return {
        **state,
        "steps": steps,
        "validation_stage": stage,
        "validation_results": merged,
        "halted": True,
        "halt_reason": f"{stage}: {reason}"[:500],
        "fails": int(state.get("fails", 0)) + 1,
    }


def _pass(state: dict[str, Any], stage: str, results: dict[str, Any]) -> dict[str, Any]:
    merged = dict(state.get("validation_results", {}))
    merged[stage] = results
    steps = dict(state.get("steps", {}))
    steps[f"validation:{stage}"] = {"ok": True, "detail": "gate passed"}
    return {
        **state,
        "steps": steps,
        "validation_stage": stage,
        "validation_results": merged,
    }


def check_gate(stage: str, metrics: dict[str, Any]) -> tuple[bool, str]:
    """Retourne (ok, reason). Logique pure, testable sans I/O."""
    if stage == "fuzzer":
        rate = float(metrics.get("detection_rate", 0))
        ok = rate >= 0.80
        return ok, f"detection_rate={rate} gate>=0.80"
    if stage == "stress":
        passed = int(metrics.get("passed", 0))
        total = int(metrics.get("total", 15))
        crashes = int(metrics.get("crashes", 1))
        fps = int(metrics.get("false_positives", 1))
        ok = passed == total and crashes == 0 and fps == 0
        return ok, f"passed={passed}/{total} crashes={crashes} fp={fps}"
    if stage == "combinatorial":
        overall = float(metrics.get("overall", 0))
        worst_family = float(metrics.get("worst_family", 0))
        ok = overall >= 0.85 and worst_family >= 0.70
        return ok, f"overall={overall} worst_family={worst_family}"
    if stage == "oos":
        detected = int(metrics.get("detected", 0))
        total = int(metrics.get("total", 6))
        fp_events = int(metrics.get("fp_events", 99))
        ok = detected == total and fp_events <= 10
        # Anti-overfitting gate : echec ici = STOP tout (R115).
        return ok, f"detected={detected}/{total} fp_events={fp_events} OVERFITTING_GATE"
    if stage == "benchmark":
        gain = float(metrics.get("detection_gain_vs_best", 0))
        ok = gain >= 0.50
        return ok, f"detection_gain_vs_best={gain} gate>=0.50"
    return False, f"unknown stage {stage}"


def make_stage_node(stage: str):
    def _node(state: dict[str, Any]) -> dict[str, Any]:
        if state.get("halted"):
            return state
        metrics = dict(state.get("validation_results", {}).get(stage, {}))
        # En POC, les metriques arrivent via l'etat initial (rapports JSON).
        # Si absentes, on ne devine pas : echec explicite, pas de silencieux.
        if not metrics and stage not in state.get("validation_results", {}):
            return _halt(state, stage, "no metrics provided for gate", {})
        ok, reason = check_gate(stage, metrics)
        if ok:
            return _pass(state, stage, {**metrics, "gate": reason})
        return _halt(state, stage, reason, {**metrics, "gate": reason})

    _node.__name__ = f"validation_{stage}"
    return _node


def next_after(stage: str) -> str:
    order = list(GATES)
    idx = order.index(stage)
    if idx + 1 < len(order):
        return order[idx + 1]
    return "end"
