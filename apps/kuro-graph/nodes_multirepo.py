"""Noeuds multi-repo Q7 : fan-out lecture seule + matrice d'impact R105.

Aucune ecriture dans les repos membres. EXTERNAL/UNKNOWN = skip avec trace (R87).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ecosystem as eco


def node_fanout(state: dict[str, Any]) -> dict[str, Any]:
    repos: dict[str, Any] = dict(state.get("repos", {}))
    steps = dict(state.get("steps", {}))
    fails = int(state.get("fails", 0))
    audited = 0
    try:
        paths = eco.pilot_paths()
    except Exception as exc:
        steps["multirepo:fanout"] = {"ok": False, "detail": f"error: {exc}"[:500]}
        return {**state, "steps": steps, "fails": fails + 1}
    for path in paths:
        name = path.name
        try:
            label, remote = eco.classify_repo(path)
        except Exception as exc:
            repos[name] = {"label": "UNKNOWN", "remote": "", "audited": False,
                           "detail": f"classify error: {exc}"[:300]}
            steps[f"multirepo:{name}"] = {"ok": False, "detail": "classify error"}
            fails += 1
            continue
        scope = eco.sync_scope(label)
        if label != "OWNED":
            repos[name] = {"label": label, "remote": remote, "audited": False,
                           "scope": scope, "detail": f"skipped: {label} gets AGENTS.md only"}
            steps[f"multirepo:{name}"] = {"ok": True, "detail": f"skipped {label}"}
            continue
        ok, head = eco.session_summary_head(path)
        repos[name] = {"label": label, "remote": remote, "audited": ok,
                       "scope": scope, "summary_chars": len(head) if ok else 0,
                       "detail": ("audited" if ok else head[:300])}
        steps[f"multirepo:{name}"] = {"ok": ok, "detail": f"OWNED summary_chars={len(head) if ok else 0}"}
        if ok:
            audited += 1
        else:
            fails += 1
    steps["multirepo:fanout"] = {"ok": True, "detail": f"audited={audited}/{len(paths)}"}
    return {**state, "repos": repos, "steps": steps, "fails": fails}


def node_impact(state: dict[str, Any]) -> dict[str, Any]:
    change = str(state.get("multirepo_change", "kuro-graph Q7 read-only audit"))
    impact = eco.build_impact(change, dict(state.get("repos", {})))
    steps = dict(state.get("steps", {}))
    audited = [k for k, v in state.get("repos", {}).items() if v.get("audited")]
    steps["multirepo:impact"] = {"ok": True, "detail": f"impacted={impact['impacted']} breaking={impact['breaking']}"}
    return {**state, "steps": steps, "ecosystem_impact": impact,
            "multirepo_audited": audited}


def route_after_fanout(state: dict[str, Any]) -> str:
    repos = state.get("repos", {})
    if any(v.get("audited") for v in repos.values()):
        return "impact"
    return "end"
