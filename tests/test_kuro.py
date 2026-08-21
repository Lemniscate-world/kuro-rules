"""Tests Kuro — logique pure, sans réseau ni DB réelle."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import ci_guardian  # noqa: E402
import kuro_llm  # noqa: E402
import weekly_report  # noqa: E402


# ---------- kuro_llm ----------

def test_cloud_candidates_priorise_et_filtre_locaux(monkeypatch):
    fake = {
        "models": [
            {"name": "qwen3.8:latest"},
            {"name": "minimax-m3:cloud"},
            {"name": "kimi-k2.7-code:cloud"},
            {"name": "gemma3:1b-it-qat"},
        ]
    }
    monkeypatch.setattr(kuro_llm, "_get_json", lambda url, timeout=5: fake)
    candidates = kuro_llm.cloud_candidates("http://x")
    assert candidates[0] == "minimax-m3:cloud"
    assert all(n.endswith(":cloud") for n in candidates)
    assert "gemma3:1b-it-qat" not in candidates


def test_cloud_candidates_vide_sans_cloud(monkeypatch):
    monkeypatch.setattr(
        kuro_llm, "_get_json", lambda url, timeout=5: {"models": [{"name": "qwen3.8:latest"}]}
    )
    assert kuro_llm.cloud_candidates("http://x") == []


def test_ask_ollama_puis_none_declenche_pas_erreur(monkeypatch):
    appels = []

    def fake_openrouter(prompt, system):
        appels.append("openrouter")
        return None, "no-key"

    def fake_ollama(prompt, system):
        appels.append("ollama")
        return "ok", "ok"

    monkeypatch.setattr(kuro_llm, "_openrouter", fake_openrouter)
    monkeypatch.setattr(kuro_llm, "_ollama", fake_ollama)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert kuro_llm.ask("test") == "ok"
    assert appels == ["openrouter", "ollama"]


def test_ask_echec_total_alerte_throttle(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: (None, "error"))
    monkeypatch.setattr(kuro_llm, "_ollama", lambda p, s: (None, "unreachable"))
    poste = []
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "http://wh")
    monkeypatch.setattr(kuro_llm, "_alert_brain_down", lambda: poste.append(1))
    assert kuro_llm.ask("test") is None
    assert len(poste) == 1


# ---------- ci_guardian ----------

def _run(attempt=1):
    return {
        "name": "Build",
        "conclusion": "failure",
        "run_attempt": attempt,
        "id": 42,
        "html_url": "http://x",
    }


def test_remediate_premier_echec_relaunch(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "")
    called = {}
    monkeypatch.setattr(ci_guardian, "rerun_failed_jobs", lambda r, i, t: called.setdefault("rerun", True) or True)
    action = ci_guardian.remediate("o/r", _run(1), token="t", dry_run=False)
    assert action["action"] == "rerun_triggered"
    assert called.get("rerun")


def test_remediate_echec_persistant_issue(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "")
    monkeypatch.setattr(ci_guardian, "find_open_issue", lambda r, w, t: 7)
    sent = {}
    monkeypatch.setattr(ci_guardian, "comment_issue", lambda r, n, b, t: sent.setdefault("n", n) and True or True)
    action = ci_guardian.remediate("o/r", _run(2), token="t", dry_run=False)
    assert action["action"] == "issue_updated"
    assert sent["n"] == 7


def test_rerun_impossible_escalade_issue(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "")
    monkeypatch.setattr(ci_guardian, "rerun_failed_jobs", lambda r, i, t: False)
    monkeypatch.setattr(ci_guardian, "find_open_issue", lambda r, w, t: None)
    created = {}
    monkeypatch.setattr(ci_guardian, "open_issue", lambda r, t_, b, tok: created.setdefault("title", t_) or 12)
    action = ci_guardian.remediate("o/r", _run(1), token="t", dry_run=False)
    assert action["action"] == "issue_opened"
    assert "[Kuro Sentinel]" in created["title"]


# ---------- weekly_report ----------

def test_ci_summary_compte_les_verts():
    ci = {
        "repos": [
            {
                "name": "a",
                "health": "green",
                "workflows": [{"conclusion": "success"}, {"conclusion": "success"}],
            },
            {
                "name": "b",
                "health": "red",
                "workflows": [{"name": "Build", "conclusion": "failure"}],
            },
        ]
    }
    ok, total, reds = weekly_report.ci_summary(ci)
    assert (ok, total, len(reds)) == (2, 3, 1)
    assert reds[0].startswith("b (")


def test_ci_summary_vide():
    assert weekly_report.ci_summary(None) == (0, 0, [])
