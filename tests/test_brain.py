"""Tests post_brain — memoire et raisonnement, zero reseau (LLM moque)."""

import json
import os
import sys
import types

import post_brain as pb


def _no_llm(monkeypatch):
    fake = types.ModuleType("kuro_llm")

    def _boom(*a, **k):
        raise RuntimeError("pas de moteur")
    fake.ask = _boom
    monkeypatch.setitem(sys.modules, "kuro_llm", fake)


def test_score_deterministe():
    s, issues = pb.deterministic_score("Helium", "x" * 200, ["A", "B"])
    assert s >= 70 and issues == []
    s2, issues2 = pb.deterministic_score("Helium", "court", [])
    assert s2 < s and issues2


def test_review_sans_llm(monkeypatch, tmp_path):
    _no_llm(monkeypatch)
    monkeypatch.setattr(pb, "HISTORY", tmp_path / "h.jsonl")
    rep = pb.review_draft("Helium", "Un vrai sujet explique clairement ici, avec du contexte utile.")
    assert rep["score_llm"] is None and rep["score"] == rep["score_det"]
    pb.append_history(rep, path=tmp_path / "h.jsonl")
    notes = pb.learn(history_path=tmp_path / "h.jsonl")
    assert any("Helium" in n for n in notes)


def test_llm_critique_en(monkeypatch):
    import types
    fake = types.ModuleType("kuro_llm")
    seen = {}

    def _ask(prompt, system=""):
        seen["prompt"] = prompt
        seen["system"] = system
        return '{"score": 88, "issues": ["ok"], "rewrite": null}'
    fake.ask = _ask
    monkeypatch.setitem(sys.modules, "kuro_llm", fake)
    rep = pb.review_draft("Helium", "A clear post about mesh progress here.", lang="en")
    assert rep["score_llm"] == 88
    assert "editor" in seen["system"].lower()


def test_flag_et_overrides(monkeypatch, tmp_path):
    ov = tmp_path / "ov.json"
    assert pb.flag_term("OpenQuant", "contrefactuel", path=ov) is True
    assert pb.flag_term("OpenQuant", "contrefactuel", path=ov) is False
    data = json.loads(ov.read_text(encoding="utf-8"))
    assert data == {"OpenQuant": {"never_add": ["contrefactuel"]}}
    monkeypatch.setattr(pb, "load_overrides",
                        lambda path=None: {"OpenQuant": {"never_add": ["contrefactuel"]}})
    strat = {"openquant": {"never": ["edge"]}}
    pb.apply_overrides(strat)
    assert sorted(strat["openquant"]["never"]) == ["contrefactuel", "edge"]


def test_ingest_sans_cle(monkeypatch):
    monkeypatch.delenv("BUFFER_API_KEY", raising=False)
    assert "error" in pb.ingest_delivery()


def test_ingest_statuts(monkeypatch, tmp_path):
    import buffer_post as bp
    monkeypatch.setenv("BUFFER_API_KEY", "k")
    monkeypatch.setattr(bp, "list_organizations", lambda k: [{"id": "o", "name": "O"}])

    def _fake_gql(q, k):
        if "scheduled" in q:
            return {"posts": {"edges": [{"node": {"id": "p1"}}]}}
        return {"posts": {"edges": [{"node": {"id": "p2"}}]}}
    monkeypatch.setattr(bp, "gql", _fake_gql)
    state = tmp_path / "st.json"
    state.write_text(json.dumps({"hub": [
        {"date": "2026-09-21", "projet": "A", "hash": "h", "id": "p1"},
        {"date": "2026-09-21", "projet": "B", "hash": "h", "id": "p2"},
        {"date": "2026-09-21", "projet": "C", "hash": "h", "id": "px"}]}),
        encoding="utf-8")
    out = pb.ingest_delivery(state_path=state, out_path=tmp_path / "d.json")
    assert out["p1"]["statut"] == "scheduled"
    assert out["p2"]["statut"] == "sent"
    assert out["px"]["statut"] == "gone"


# --- Raisonnement global (P1) -------------------------------------------


def test_global_context_lecture_seule(tmp_path, monkeypatch):
    """global_context() lit logs/overrides/learn sans crash, zero reseau."""
    xlog = tmp_path / "x_posts_log.md"
    xlog.write_text(
        "| Date | Compte | Projet | Post |\n"
        "|---|---|---|---|\n"
        "| 2026-10-19 | Kuro | Helium | Lumiere du jour sur le mesh |\n",
        encoding="utf-8")
    monkeypatch.setattr(pb, "XLOG", xlog)
    monkeypatch.setattr(pb, "OVERRIDES", tmp_path / "missing.json")
    monkeypatch.setattr(pb, "learn", lambda *a, **k: ["constat A", "constat B"])
    ctx = pb.global_context()
    assert ctx["recent"] and ctx["recent"][0]["projet"] == "Helium"
    assert ctx["learn"] == ["constat A", "constat B"]
    block = pb.context_block(ctx, lang="fr")
    assert "Lumiere du jour" in block and "constat A" in block


def test_contexte_injecte_dans_prompt_llm(monkeypatch):
    """llm_critique append le contexte global au prompt (raisonnement batch)."""
    fake = types.ModuleType("kuro_llm")
    seen = {}

    def _ask(prompt, system=""):
        seen["prompt"] = prompt
        return '{"score": 70, "issues": [], "rewrite": null}'
    fake.ask = _ask
    monkeypatch.setitem(sys.modules, "kuro_llm", fake)
    ctx = {"recent": [{"date": "2026-10-19", "compte": "Kuro",
                       "projet": "Helium", "texte": "post deja vu"}],
           "learn": ["eviter le jargon"], "muted": {"Helium": ["edge"]}}
    pb.llm_critique("Helium", "Un post neuf sur un sujet neuf, assez long.",
                    lang="fr", ctx=ctx)
    assert "post deja vu" in seen["prompt"]
    assert "eviter le jargon" in seen["prompt"]
    assert "edge" in seen["prompt"]


def test_review_draft_partage_le_ctx(monkeypatch):
    """review_draft transmet bien le ctx a llm_critique (un seul build/jour)."""
    captured = {}

    def _crit(project, text, lang="fr", ctx=None):
        captured["ctx"] = ctx
        return {"score": 60, "issues": [], "rewrite": None}
    monkeypatch.setattr(pb, "llm_critique", _crit)
    shared = {"recent": [], "learn": [], "muted": {}}
    rep = pb.review_draft("Helium", "texte de test assez long pour score ok.",
                          ctx=shared)
    assert captured["ctx"] is shared
    assert rep["score_llm"] == 60


def test_batch_review_contexte_partage(monkeypatch, tmp_path):
    """review-all note tous les drafts avec UN contexte partage + lint."""
    import gen_x_posts as gx
    _no_llm(monkeypatch)  # zero reseau : score deterministe seul
    today = "2026-10-20"
    for name in (f"x_post_{today}.md", f"x_post_{today}-helium.md"):
        (tmp_path / name).write_text(
            "Lumiere sur un vrai sujet tech, explique clairement avec du "
            "contexte utile et une metrique 42%.\n", encoding="utf-8")
    monkeypatch.setattr(pb, "OUTPUTS", tmp_path)
    monkeypatch.setattr(pb, "HISTORY", tmp_path / "h.jsonl")
    builds = {"n": 0}

    def _ctx(*a, **k):
        builds["n"] += 1
        return {"recent": [], "learn": [], "muted": {}}
    monkeypatch.setattr(pb, "global_context", _ctx)
    monkeypatch.setattr(gx, "lint_post", lambda p, t: [])
    notes, pires = pb.batch_review(pattern="x_post_*.md")
    assert len(notes) == 2
    assert builds["n"] == 1  # un seul contexte pour tout le batch
    assert (tmp_path / "h.jsonl").exists()  # historique alimente (learn possible)
    # filtre projet : ne garde que helium
    notes2, _ = pb.batch_review(pattern="x_post_*.md", project_filter="helium")
    assert len(notes2) == 1 and notes2[0]["projet"] == "helium"


# --- Boucle de retour metrics (ingest_metrics -> learn) --------------------


def test_get_post_metrics_parse(monkeypatch):
    """buffer_post.get_post_metrics parse le schema Buffer {type,value}."""
    import buffer_post as bp

    def _gql(q, k):
        assert "GetPostMetrics" in q
        return {"post": {"id": "p1", "metrics": [
            {"type": "reactions", "value": 4.0},
            {"type": "comments", "value": 1.0},
            {"type": "bogus", "value": None}]}}
    monkeypatch.setattr(bp, "gql", _gql)
    m = bp.get_post_metrics("p1", "k")
    assert m == {"reactions": 4.0, "comments": 1.0}  # value None ignoree


def test_ingest_metrics_sans_cle(tmp_path, monkeypatch):
    """Sans BUFFER_API_KEY : no-op totale, zero appel reseau."""
    monkeypatch.delenv("BUFFER_API_KEY", raising=False)
    (tmp_path / "st.json").write_text(
        json.dumps({"a": {"statut": "sent", "projet": "Helium"}}), encoding="utf-8")
    out = pb.ingest_metrics(state_path=tmp_path / "st.json",
                            metrics_path=tmp_path / "m.json")
    assert out == {} and not (tmp_path / "m.json").exists()


def test_ingest_metrics_merge_et_filtre_sent(monkeypatch, tmp_path):
    """Interroge uniquement les 'sent' (8 derniers) et merge dans l'existant."""
    calls = []

    def _metrics(pid, key):
        calls.append(pid)
        return {"reactions": {"value": 2}.get("value")}
    monkeypatch.setattr("os.environ", dict(os.environ, BUFFER_API_KEY="k"))
    state = {f"p{i}": {"statut": "sent" if i >= 5 else "scheduled",
                       "projet": "Helium"} for i in range(10)}
    sp = tmp_path / "st.json"
    sp.write_text(json.dumps(state), encoding="utf-8")
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps({"ancien": {"projet": "Forma", "metrics": {"reactions": 9}}}),
                  encoding="utf-8")
    # buffer_post reel (import reussi) : on mocke juste get_post_metrics
    import buffer_post as bp
    monkeypatch.setattr(bp, "get_post_metrics", _metrics)
    out = pb.ingest_metrics(state_path=sp, metrics_path=mp)
    assert calls and all(c.startswith("p") and int(c[1:]) >= 5 for c in calls)  # sent only
    assert len(calls) <= 8  # fenetre glissante
    assert "ancien" in out  # merge conserve l'historique
    saved = json.loads(mp.read_text(encoding="utf-8"))
    assert "ancien" in saved and saved["p5"]["metrics"]["reactions"] == 2


def test_learn_constats_engagement(tmp_path):
    """learn() ajoute les constats d'engagement reel quand METRICS existe."""
    h = tmp_path / "h.jsonl"
    h.write_text(json.dumps({"projet": "Helium", "score": 80, "issues": []}) + "\n",
                 encoding="utf-8")
    m = tmp_path / "m.json"
    m.write_text(json.dumps({
        "p1": {"projet": "Helium", "metrics": {"reactions": 10.0, "comments": 2.0}},
        "p2": {"projet": "Forma", "metrics": {"reactions": 1.0, "reposts": 1.0}}}),
        encoding="utf-8")
    notes = pb.learn(history_path=h, metrics_path=m)
    joined = " ".join(notes)
    assert "engagement reel moyen" in joined
    assert "meilleur terrain : Helium" in joined


def test_learn_sans_metrics_regress_pas(tmp_path):
    """Sans metrics : learn garde son ancien comportement (pas de crash)."""
    h = tmp_path / "h.jsonl"
    h.write_text(json.dumps({"projet": "Helium", "score": 40, "issues": ["jargon"]}) + "\n",
                 encoding="utf-8")
    notes = pb.learn(history_path=h, metrics_path=tmp_path / "absent.json")
    assert any("score moyen 40" in n for n in notes)
    assert not any("engagement" in n for n in notes)
