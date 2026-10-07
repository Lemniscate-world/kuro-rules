"""Tests post_policy — decision principal/annexes, pure, zero reseau."""

import os
from datetime import datetime, timedelta, timezone

import post_policy as pp


def _entry(name, score, h="abc1234", themes=("Sujet publiable",)):
    return {"project": {"name": name, "pct": 10, "status": "Actif", "desc": ""},
            "facts": {"hash": h, "date": "2026-09-21", "msg": "x",
                      "c30": 5, "c7": 2, "branch": "main", "dirty": False,
                      "themes": list(themes)},
            "ownership": "OWNED", "score": score}


def test_hub_un_par_jour_top_dabord():
    sel = [_entry("Alpha", 40), _entry("Beta", 30)]
    plan, _ = pp.decide(sel, {}, hub="hub", today="2026-09-21")
    assert [(i["account"], i["project"]) for i in plan] == [("hub", "Alpha")]


def test_hub_skip_si_deja_poste_aujourdhui():
    sel = [_entry("Alpha", 40)]
    state = {"hub": [{"date": "2026-09-21T08:00:00+00:00", "projet": "Z", "hash": "zzz"}]}
    plan, raisons = pp.decide(sel, state, hub="hub", today="2026-09-21")
    assert plan == []  # quota 1/jour atteint


def test_hub_saute_hash_deja_poste():
    sel = [_entry("Alpha", 40, h="h1"), _entry("Beta", 30, h="h2")]
    state = {"hub": [{"date": "2026-09-01T08:00:00+00:00", "projet": "A", "hash": "h1"}]}
    plan, _ = pp.decide(sel, state, hub="hub", today="2026-09-21")
    assert [i["project"] for i in plan if i["account"] == "hub"] == ["Beta"]


def test_hub_saute_sans_theme_publiable():
    sel = [_entry("Alpha", 40, h="h1", themes=[]), _entry("Beta", 30, h="h2")]
    plan, raisons = pp.decide(sel, {}, hub="hub", today="2026-09-21")
    assert [i["project"] for i in plan if i["account"] == "hub"] == ["Beta"]
    assert ("Alpha", "hub-rien-de-publiable") in raisons


def test_annexe_score_cooldown_dedupe():
    sel = [_entry("Helium", 19, h="h9")]
    def annex(plan):
        return [i for i in plan if i["account"] == "helium"]
    # score insuffisant
    plan, raisons = pp.decide(sel, {}, annex_accounts=["Helium"], min_score=20)
    assert annex(plan) == [] and raisons == [("Helium", "annexe-score-19<20")]
    # ok
    plan, _ = pp.decide(sel, {}, annex_accounts=["Helium"], min_score=15)
    assert [(i["account"], i["project"]) for i in annex(plan)] == [("helium", "Helium")]
    # cooldown
    now = datetime.now(timezone.utc).isoformat()
    state = {"helium": [{"date": now, "projet": "Helium", "hash": "old"}]}
    plan, raisons = pp.decide(sel, state, annex_accounts=["Helium"], min_score=15)
    assert annex(plan) == [] and raisons == [("Helium", "annexe-cooldown")]
    # hash deja poste (hors cooldown)
    old = (datetime.now(timezone.utc) - timedelta(hours=100)).isoformat()
    state = {"helium": [{"date": old, "projet": "Helium", "hash": "h9"}]}
    plan, raisons = pp.decide(sel, state, annex_accounts=["Helium"], min_score=15)
    assert annex(plan) == [] and raisons == [("Helium", "annexe-deja-poste")]


def test_x_posting_enabled_selon_plan(monkeypatch):
    monkeypatch.setenv("X_PLAN", "free")
    assert pp.x_posting_enabled() is False
    monkeypatch.setenv("X_PLAN", "basic")
    assert pp.x_posting_enabled() is True
    monkeypatch.delenv("X_PLAN", raising=False)
    assert pp.x_posting_enabled() is False


def test_discord_notify_ok_et_sans_webhook(monkeypatch, tmp_path):
    import sys
    import types
    fake = types.ModuleType("kuro_discord")
    fake.load_channel_map = lambda: {"helium": "https://wh/h"}
    fake.webhook_for = lambda p, m: m.get("helium", "") if p == "Helium" else ""
    posted = []
    fake.post_webhook = lambda u, t, b: posted.append((u, t))
    monkeypatch.setitem(sys.modules, "kuro_discord", fake)
    f = tmp_path / "x_long.md"
    f.write_text("update", encoding="utf-8")
    assert pp.discord_notify("Helium", str(f)) is True
    assert posted and posted[0][0] == "https://wh/h"
    assert pp.discord_notify("Inconnu", str(f)) is False


def test_publish_via_buffer_ok_et_sans_canal(monkeypatch):
    import sys
    import types
    fake = types.ModuleType("buffer_post")

    class FakeErr(Exception):  # noqa: N818 - mime BufferError du module moqué
        pass
    fake.BufferError = FakeErr
    fake.create_post = lambda t, c, k, mode="addToQueue", due_at="": {"id": "b1"}
    fake.next_slot_utc = lambda hour=None, now=None: "2026-09-21T20:00:00.000Z"
    monkeypatch.setitem(sys.modules, "buffer_post", fake)
    monkeypatch.setenv("BUFFER_API_KEY", "k")
    monkeypatch.setenv("BUFFER_CHANNEL_HUB", "ch-hub")
    assert pp.publish_via_buffer("hello", "hub") == "b1"
    assert pp.buffer_channel_for("Helium") == os.environ.get("BUFFER_CHANNEL_HELIUM", "")
    monkeypatch.delenv("BUFFER_CHANNEL_HUB", raising=False)
    try:
        pp.publish_via_buffer("hello", "hub")
    except FakeErr as exc:
        assert "non configure" in str(exc)
        return
    raise AssertionError("BufferError attendue")


def test_record_post_et_state(tmp_path):
    assert pp.account_lang("hub") == "en"
    assert pp.account_lang("helium") == "fr"
    assert pp.account_lang("") == "en"
    state = pp.record_post({}, "helium", "Helium", "h9", "tid1")
    assert state["helium"][0]["hash"] == "h9"
    assert "h9" in pp.posted_hashes(state, "helium")
    assert pp.last_post_time(state, "helium") is not None
    assert pp.last_post_time({}, "helium") is None
    log = tmp_path / "posts.md"
    pp.append_posts_log("helium", "Helium", "texte | pipe", "tid1", path=log)
    assert log.exists()


def test_maybe_rewrite_garde_fous(monkeypatch):
    import sys
    import types
    fake_brain = types.ModuleType("post_brain")
    fake_brain.review_draft = lambda p, t, th=(), lang="fr": {
        "rewrite": "Version humaine avec 12 commits et https://github.com/x/y",
        "score_llm": 90}
    fake_brain.deterministic_score = lambda p, t, th=(), lang="fr": (80, [])
    fake_gx = types.ModuleType("gen_x_posts")
    fake_gx.x_len = lambda t: len(t)
    fake_gx.lint_post = lambda p, t: []
    monkeypatch.setitem(sys.modules, "post_brain", fake_brain)
    monkeypatch.setitem(sys.modules, "gen_x_posts", fake_gx)
    orig = "12 commits et https://github.com/x/y"
    new, ok = pp.maybe_rewrite("P", orig)
    assert ok is True and "humaine" in new


def test_maybe_rewrite_refuse_hallucination(monkeypatch):
    import sys
    import types
    fake_brain = types.ModuleType("post_brain")
    fake_brain.review_draft = lambda p, t, th=(), lang="fr": {
        "rewrite": "Version avec 999 commits inventes",
        "score_llm": 95}
    fake_brain.deterministic_score = lambda p, t, th=(), lang="fr": (80, [])
    fake_gx = types.ModuleType("gen_x_posts")
    fake_gx.x_len = lambda t: len(t)
    fake_gx.lint_post = lambda p, t: []
    monkeypatch.setitem(sys.modules, "post_brain", fake_brain)
    monkeypatch.setitem(sys.modules, "gen_x_posts", fake_gx)
    orig = "12 commits reels ici"
    new, ok = pp.maybe_rewrite("P", orig)
    assert ok is False and new == orig
