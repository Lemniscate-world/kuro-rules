"""Tests agents.py : parse JSON OpenClaw, cache 60 s, CLI absent."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import agents  # noqa: E402


def _save_cache():
    return dict(agents._AGENTS_CACHE)


def _restore_cache(saved):
    agents._AGENTS_CACHE.clear()
    agents._AGENTS_CACHE.update(saved)


def test_rel_time():
    now = 1_000_000_000_000.0
    assert agents._rel(None, now) == "jamais"
    assert agents._rel(now + 10 * 60000, now) == "dans 10 min"
    assert agents._rel(now - 12 * 60000, now) == "il y a 12 min"
    assert agents._rel(now - 3 * 3600000, now) == "il y a 3 h"
    assert agents._rel(now + 2 * 86400000, now) == "dans 2 j"


def test_short_model():
    assert agents._short_model("deepseek/deepseek-v4-pro@deepseek:setup-1") == "deepseek-v4-pro"
    assert agents._short_model(None) == "?"
    assert agents._short_model("") == "?"


def test_collect_trie_problemes_dabord(monkeypatch):
    monkeypatch.setattr(agents.shutil, "which", lambda name: "/bin/openclaw")

    def _fake(*args):
        if args[0] == "agents":
            return [{"id": "main", "identityName": "Kuro",
                     "model": "deepseek/deepseek-v4-pro@x"}]
        jobs = {"jobs": [
            {"name": "ok-job", "agentId": "main", "enabled": True,
             "state": {"nextRunAtMs": 1, "lastRunAtMs": 1, "lastRunStatus": "ok"}},
            {"name": "bad-job", "agentId": "main", "enabled": True,
             "state": {"nextRunAtMs": 2, "lastRunAtMs": 2, "lastRunStatus": "error (9x)"}},
        ]}
        return jobs

    monkeypatch.setattr(agents, "_openclaw_json", _fake)
    data = agents.collect_agents()
    assert data["present"] is True
    assert data["agents"][0]["model"] == "deepseek-v4-pro"
    assert data["crons"][0]["name"] == "bad-job"
    assert data["crons"][0]["status"].startswith("error")


def test_collect_sans_cli(monkeypatch):
    monkeypatch.setattr(agents.shutil, "which", lambda name: None)
    data = agents.collect_agents()
    assert data == {"present": False, "agents": [], "crons": [],
                    "agents_ok": False, "crons_ok": False}


def test_cache_60s(monkeypatch):
    saved = _save_cache()
    try:
        calls = []
        monkeypatch.setattr(agents, "collect_agents",
                            lambda: calls.append(1) or {"present": False,
                                                       "agents": [], "crons": []})
        agents._AGENTS_CACHE["ts"] = 0.0
        agents._AGENTS_CACHE["lines"] = []
        first = agents.agents_lines()
        second = agents.agents_lines()
        assert calls == [1]
        assert first == second
        assert "openclaw indisponible" in first[0]
    finally:
        _restore_cache(saved)


def test_sec_agents_rendu(monkeypatch):
    import kuro_dashboard.tui as tui

    monkeypatch.setattr(tui, "agents_lines", lambda: ["agents : x"])
    rows = tui.sec_agents()
    assert rows[0] == "AGENTS" and "agents : x" in rows
