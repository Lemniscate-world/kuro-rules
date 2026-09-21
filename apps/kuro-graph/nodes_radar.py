"""Noeuds radar : veille -> scoring LLM -> decision conditionnelle.

Entrees : signaux publics (HN/Reddit/GitHub/arXiv) deja filtres par
kuro_radar.py (MIN_HN_POINTS, MIN_REDDIT_SCORE, MIN_GH_STARS).
Aucune donnee finance R111 ni secret n'entre ici.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def node_collect(state: dict[str, Any]) -> dict[str, Any]:
    try:
        import kuro_radar as radar

        signals: list[dict[str, Any]] = []
        # Reutilise les fetchers existants, jamais de scraping ad hoc.
        for query in getattr(radar, "HN_QUERIES", ["LLM"])[:3]:
            try:
                for hit in radar.fetch_hn(query)[:5]:
                    signals.append({"source": "hn", "query": query, **hit})
            except Exception:
                continue
        for sub in getattr(radar, "REDDIT_SUBS", ["MachineLearning"])[:3]:
            try:
                for post in radar.fetch_reddit(sub)[:5]:
                    signals.append({"source": "reddit", "sub": sub, **post})
            except Exception:
                continue
        steps = dict(state.get("steps", {}))
        steps["radar:collect"] = {"ok": True, "detail": f"{len(signals)} signals"}
        return {**state, "steps": steps, "radar_signals": signals[:30]}
    except Exception as exc:
        steps = dict(state.get("steps", {}))
        steps["radar:collect"] = {"ok": False, "detail": f"error: {exc}"[:500]}
        return {**state, "steps": steps, "radar_signals": [], "fails": int(state.get("fails", 0)) + 1}


def _score_with_llm(title: str) -> tuple[str, str]:
    """Retourne (label, detail). Jamais d'exception vers l'appelant."""
    try:
        import kuro_llm as llm

        prompt = (
            "Classe ce signal de veille en un mot : keep / discard. "
            f"Titre : {title[:300]}"
        )
        reply = llm.ask(prompt, system="Tu es le filtre veille lambda-Section. Reponds keep ou discard puis une courte raison.")
        if not reply:
            return "unscored", "llm-unavailable deterministic fallback"
        low = reply.lower()
        if "keep" in low:
            return "keep", reply[:300]
        return "discard", reply[:300]
    except Exception as exc:
        return "unscored", f"llm-error: {exc}"[:300]


def node_score(state: dict[str, Any]) -> dict[str, Any]:
    signals = list(state.get("radar_signals", []))
    kept: list[dict[str, Any]] = []
    for sig in signals[:30]:
        label, detail = _score_with_llm(str(sig.get("title", "")))
        sig2 = {**sig, "llm_label": label, "llm_detail": detail}
        if label == "keep":
            kept.append(sig2)
    steps = dict(state.get("steps", {}))
    steps["radar:score"] = {"ok": True, "detail": f"kept={len(kept)}/{len(signals)}"}
    return {**state, "steps": steps, "radar_signals": kept if kept else signals}


def route_radar(state: dict[str, Any]) -> str:
    signals = state.get("radar_signals", [])
    kept = [s for s in signals if s.get("llm_label") == "keep"]
    # Seuil POC : >=2 keeps => draft, 0 signal => end silencieux, sinon archive.
    if len(kept) >= 2:
        return "draft"
    if not signals:
        return "end"
    return "archive"


DRAFT_STEP = "radar:draft"


def node_draft(state: dict[str, Any]) -> dict[str, Any]:
    steps = dict(state.get("steps", {}))
    kept = [s for s in state.get("radar_signals", []) if s.get("llm_label") == "keep"]
    steps[DRAFT_STEP] = {"ok": True, "detail": f"draft for {len(kept)} signals, no Discord without write=True"}
    out = {**state, "steps": steps, "radar_decision": "draft"}
    if not state.get("write") or state.get("dry_run", True):
        return out
    try:
        import utils as guards

        if guards.vacances_on():
            steps[DRAFT_STEP] = {"ok": True, "detail": "skipped Discord: vacances"}
            return {**out, "steps": steps}
        if not guards.is_approved(state):
            steps[DRAFT_STEP] = {"ok": True, "detail": "skipped Discord: human approval missing"}
            return {**out, "steps": steps}
        import kuro_proposals as proposals

        lines = [f"{s.get('title', '')[:140]} — {s.get('url', '')}" for s in kept[:5]]
        ok = proposals.post_discord("Veille Kuro-graph", lines)
        steps[DRAFT_STEP] = {"ok": True, "detail": f"Discord post={ok} for {len(kept)} signals"}
        return {**out, "steps": steps}
    except Exception as exc:
        steps[DRAFT_STEP] = {"ok": False, "detail": f"Discord error: {exc}"[:500]}
        out2 = {**out, "steps": steps}
        out2["fails"] = int(out2.get("fails", 0)) + 1
        return out2


def node_archive(state: dict[str, Any]) -> dict[str, Any]:
    steps = dict(state.get("steps", {}))
    steps["radar:archive"] = {"ok": True, "detail": f"archived {len(state.get('radar_signals', []))} signals"}
    return {**state, "steps": steps, "radar_decision": "archived"}
