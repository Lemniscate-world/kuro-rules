"""Tests post_brain — memoire et raisonnement, zero reseau (LLM moque)."""

import json
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
    import json as _j

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
