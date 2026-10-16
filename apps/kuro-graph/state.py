"""Etat partage des graphes Kuro. Un seul TypedDict versionne."""

from __future__ import annotations

from typing import Any, TypedDict


STATE_VERSION = 3


class KuroState(TypedDict, total=False):
    state_version: int
    write: bool
    dry_run: bool
    fails: int
    halted: bool
    halt_reason: str
    steps: dict[str, Any]
    metrics: dict[str, Any]
    retries: dict[str, int]
    human_approved: bool
    thread_id: str
    doctor_ok: bool
    truth_ok: bool
    portfolio_ok: bool
    strategy_ok: bool
    validation_stage: str
    validation_results: dict[str, Any]
    radar_signals: list[dict[str, Any]]
    radar_decision: str
    repos: dict[str, Any]
    ecosystem_impact: dict[str, Any]
    multirepo_change: str
    multirepo_audited: list[str]


def new_state(write: bool = False, dry_run: bool = True) -> KuroState:
    return {
        "state_version": STATE_VERSION,
        "write": write,
        "dry_run": dry_run,
        "fails": 0,
        "halted": False,
        "halt_reason": "",
        "steps": {},
        "metrics": {"durations": {}},
        "retries": {},
        "human_approved": False,
        "thread_id": "",
        "doctor_ok": False,
        "truth_ok": False,
        "portfolio_ok": False,
        "strategy_ok": False,
        "validation_stage": "",
        "validation_results": {},
        "radar_signals": [],
        "radar_decision": "undecided",
        "repos": {},
        "ecosystem_impact": {},
        "multirepo_change": "",
        "multirepo_audited": [],
    }
