"""Tests kuro_mirror_cron_usage — pur + idempotence, zero reseau."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_mirror_cron_usage as mm  # noqa: E402


def _fake_openclaw(agents, cron):
    def _run(cmd, **kwargs):
        class _Done:
            returncode = 0
            stdout = ""
        if cmd[:3] == ["openclaw", "agents", "list"]:
            _Done.stdout = json.dumps(agents)
            return _Done()
        if cmd[:3] == ["openclaw", "cron", "list"]:
            _Done.stdout = json.dumps(cron)
            return _Done()
        _Done.returncode = 1
        return _Done()

    return _run


def _runs(now_ms):
    return {"jobs": [
        {"id": "j1", "name": "bon-job", "agentId": "main",
         "state": {"lastRunStatus": "ok", "lastRunAtMs": now_ms,
                   "lastDurationMs": 71000}},
        {"id": "j2", "name": "rate", "agentId": "main",
         "state": {"lastRunStatus": "error", "lastRunAtMs": now_ms,
                   "lastDurationMs": 1000}},
        {"id": "j3", "name": "vieux", "agentId": "main",
         "state": {"lastRunStatus": "ok",
                   "lastRunAtMs": now_ms - 10 * 24 * 3600000,
                   "lastDurationMs": 1000}},
    ]}


def test_leg_and_model():
    assert mm._leg_and_model("deepseek/x@deepseek:setup-1") == ("deepseek", "deepseek/x")
    assert mm._leg_and_model("") == ("?", "")
    assert mm._leg_and_model(None) == ("?", "")


def test_collect_filtre_statuts_et_fenetre(monkeypatch):
    import time as _t
    now_ms = int(_t.time() * 1000)
    monkeypatch.setattr(mm.subprocess, "run",
                        _fake_openclaw([{"id": "main",
                                         "model": "deepseek/deepseek-v4-pro@deepseek:s"}],
                                       _runs(now_ms)))
    monkeypatch.setattr(mm.shutil, "which", lambda n: "/bin/openclaw")
    runs = mm.collect_recent_runs(window_hours=48)
    assert [r["name"] for r in runs] == ["bon-job"]
    assert runs[0]["engine"] == "deepseek" and runs[0]["latency_s"] == 71.0


def test_mirror_idempotent(tmp_path, monkeypatch):
    import time as _t
    now_ms = int(_t.time() * 1000)
    usage = tmp_path / "llm_usage.jsonl"
    monkeypatch.setattr(mm, "USAGE_FILE", usage)
    monkeypatch.setattr(mm.subprocess, "run",
                        _fake_openclaw([{"id": "main", "model": "ollama-local"}],
                                       _runs(now_ms)))
    monkeypatch.setattr(mm.shutil, "which", lambda n: "/bin/openclaw")
    first = mm.mirror()
    assert first == {"runs_seen": 1, "added": 1, "names": ["bon-job"]}
    assert mm.mirror()["added"] == 0, "2e passage : rien a ajouter"
    entry = json.loads(usage.read_text(encoding="utf-8").splitlines()[-1])
    assert entry["source"] == "openclaw-cron"
    assert entry["est_cost_usd"] is None and entry["tokens_reels"] is False


def test_sans_openclaw(monkeypatch, tmp_path):
    monkeypatch.setattr(mm.shutil, "which", lambda n: None)
    monkeypatch.setattr(mm, "USAGE_FILE", tmp_path / "u.jsonl")
    assert mm.mirror() == {"runs_seen": 0, "added": 0, "names": []}


def test_mirror_rafraichit_cerveau_sans_reculer(tmp_path, monkeypatch):
    import time as _t
    now_ms = int(_t.time() * 1000)
    usage = tmp_path / "llm_usage.jsonl"
    brain = tmp_path / "llm_last.json"
    monkeypatch.setattr(mm, "USAGE_FILE", usage)
    monkeypatch.setattr(mm, "BRAIN_FILE", brain)
    monkeypatch.setattr(mm.subprocess, "run",
                        _fake_openclaw([{"id": "main", "model": "deepseek/x"}],
                                       _runs(now_ms)))
    monkeypatch.setattr(mm.shutil, "which", lambda n: "/bin/openclaw")
    mm.mirror()
    first = json.loads(brain.read_text(encoding="utf-8"))
    assert first["engine"] == "deepseek" and first["via"] == "openclaw-cron"
    # un cerveau plus recent (vrai appel) n est jamais ecrase
    brain.write_text(json.dumps({"engine": "openrouter", "at": "2099-01-01 00:00:00"}),
                     encoding="utf-8")
    mm.mirror()
    assert json.loads(brain.read_text(encoding="utf-8"))["engine"] == "openrouter"
