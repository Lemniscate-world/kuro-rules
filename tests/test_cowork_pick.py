"""Tests cowork_pick — score, ranking, rendu Discord (logique pure)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import cowork_pick as cp  # noqa: E402


def test_score_ordonne_velocite_haute():
    a = cp.score_project(velocity=2.4, ci_failures=0, progress_pct=72,
                         alerts_open=0, days_inactive=1)
    b = cp.score_project(velocity=0.0, ci_failures=0, progress_pct=10,
                         alerts_open=0, days_inactive=60)
    assert a > b


def test_score_penalise_ci_et_alertes():
    base = cp.score_project(velocity=2.0, ci_failures=0, progress_pct=50,
                            alerts_open=0, days_inactive=0)
    degrade = cp.score_project(velocity=2.0, ci_failures=2, progress_pct=50,
                               alerts_open=2, days_inactive=0)
    assert degrade < base


def test_build_ranking_trie_et_exclut():
    payload = {"projects": [
        {"name": "Low", "velocity_per_week": 0.0, "ci_failures": 0,
         "ci_checks_total": 2, "last_commit_at": None},
        {"name": "High", "velocity_per_week": 3.0, "ci_failures": 0,
         "ci_checks_total": 2, "last_commit_at": None},
    ]}
    ctx = {"low": {"progress": 10, "status": "actif", "days_inactive": 5, "alerts": 0},
           "high": {"progress": 70, "status": "actif", "days_inactive": 1, "alerts": 0}}
    ranked = cp.build_ranking(payload, ctx)
    assert [r["name"] for r in ranked] == ["High", "Low"]
    ranked_ex = cp.build_ranking(payload, ctx, {"High"})
    assert [r["name"] for r in ranked_ex] == ["Low"]


def test_render_pick_explique_choix():
    ranking = [
        {"name": "High", "velocity": 2.4, "ci_failures": 0, "ci_total": 4,
         "progress": 72, "alerts": 0, "days_inactive": 1, "status": "actif", "score": 8.5},
        {"name": "Low", "velocity": 0.0, "ci_failures": 1, "ci_total": 2,
         "progress": 10, "alerts": 1, "days_inactive": 60, "status": "actif", "score": -10.5},
    ]
    text = cp.render_pick(ranking[0], ranking)
    assert "COWORK PICK" in text
    assert "High" in text
    assert "score 8.5" in text
    assert "Plan worker" in text
    assert len(text) <= 1900


def test_render_velocity_moyenne():
    ranking = [
        {"name": "A", "velocity": 2.0, "ci_failures": 0, "ci_total": 1,
         "progress": None, "alerts": 0, "days_inactive": 0, "status": None, "score": 4.0},
        {"name": "B", "velocity": 0.0, "ci_failures": 0, "ci_total": 0,
         "progress": None, "alerts": 0, "days_inactive": 0, "status": None, "score": 0.0},
    ]
    text = cp.render_velocity(ranking)
    assert "VELOCITE" in text
    assert "Moyenne : 1.0 c/sem" in text


def test_post_discord_noop_sans_webhook(monkeypatch):
    monkeypatch.setattr(cp, "load_dotenv", lambda: None)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert cp.post_discord("hello") is False


def test_post_discord_succes_mock(monkeypatch):
    import urllib.request

    monkeypatch.setattr(cp, "load_dotenv", lambda: None)
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "http://hook.invalid")

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=15: FakeResp())
    assert cp.post_discord("hello") is True


def test_bot_dispatch_velocity_et_pick(monkeypatch):
    import kuro_bot as bot
    import kuro_metrics

    fake = {"projects": [
        {"name": "High", "velocity_per_week": 2.0, "ci_failures": 0,
         "ci_checks_total": 1, "last_commit_at": None},
    ]}
    monkeypatch.setattr(kuro_metrics, "build_payload", lambda **k: fake)
    monkeypatch.setattr(cp, "load_db_context", lambda: {})
    out_v = bot.dispatch("!velocity")
    assert out_v is not None and "VELOCITE" in out_v
    out_p = bot.dispatch("!pick")
    assert out_p is not None and "COWORK PICK" in out_p
    assert "!velocity" in bot.dispatch("!aide")
    assert "!pick" in bot.dispatch("!aide")


def test_necessity_gate_ci_puis_cout():
    need, cost = cp.necessity_gate({"name": "R", "velocity": 5.0, "ci_failures": 2,
                                    "alerts": 0, "days_inactive": 0})
    assert "CI en echec" in need
    assert "R105" in cost


def test_necessity_gate_refuse_grab_sans_signal():
    need, _ = cp.necessity_gate({"name": "R", "velocity": 0.0, "ci_failures": 0,
                                 "alerts": 0, "days_inactive": 2})
    assert "Non demontre" in need


def test_render_pick_contient_gate():
    best = {"name": "High", "velocity": 2.4, "ci_failures": 0, "ci_total": 4,
            "progress": 72, "alerts": 1, "days_inactive": 1, "status": "actif", "score": 8.5}
    text = cp.render_pick(best, [best])
    assert "Gate" in text and "Consequences" in text


def test_score_plafonne_velocite():
    assert cp.score_project(velocity=40.0) == cp.score_project(velocity=10.0)
    assert cp.score_project(velocity=10.0) > cp.score_project(velocity=3.0)


def test_drop_duplicates_meme_historique():
    a = {"name": "A", "velocity": 3.0, "last_commit": "2026-09-20T10:00:00+00:00", "score": 6.0}
    b = {"name": "A-copy", "velocity": 3.0, "last_commit": "2026-09-20T10:00:00+00:00", "score": 5.0}
    c = {"name": "C", "velocity": 3.0, "last_commit": "2026-09-19T10:00:00+00:00", "score": 4.0}
    out = cp.drop_duplicates([a, b, c])
    assert [r["name"] for r in out] == ["A", "C"]
    assert "doublon probable" in b.get("note", "")


def test_rotation_saute_dernier_pick(tmp_path, monkeypatch):
    import datetime as dt
    f = tmp_path / "last.json"
    f.write_text('{"name": "Top", "date": "' +
                 dt.datetime.now().astimezone().isoformat() + '"}', encoding="utf-8")
    monkeypatch.setattr(cp, "LAST_PICK_FILE", f)
    ranking = [{"name": "Top", "score": 9.0}, {"name": "Second", "score": 5.0}]
    best, note = cp.apply_rotation(ranking)
    assert best["name"] == "Second" and "rotation" in note
    monkeypatch.setattr(cp, "LAST_PICK_FILE", tmp_path / "absent.json")
    best, note = cp.apply_rotation(ranking)
    assert best["name"] == "Top" and note == ""


def test_fmt_alert_types():
    assert cp.fmt_alert_types({}) == ""
    assert cp.fmt_alert_types({"missing_summary": 2, "inactivity": 1}) == \
        "inactivity x1, missing_summary x2"


def test_suggest_tasks_couverture(tmp_path, monkeypatch):
    f = tmp_path / "cov.json"
    import json as js
    f.write_text(js.dumps({"repos": [{"name": "R",
                                      "untested": [{"path": "m.py", "pct": 0}]}]}),
                 encoding="utf-8")
    monkeypatch.setattr(cp, "COVERAGE_FILE", f)
    tasks = cp.suggest_tasks({"name": "R", "ci_failures": 0, "alerts": 0, "days_inactive": 0})
    assert any("m.py (0%)" in t for t in tasks)
