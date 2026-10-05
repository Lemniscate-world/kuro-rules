"""Tests kuro_memory + rerank — sidecar hybride, 100% hermetique."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_embed as emb  # noqa: E402
import kuro_memory as mem  # noqa: E402


def _db():
    conn = sqlite3.connect(":memory:")
    return conn


def _e1():
    return [1.0] + [0.0] * 1023


def _e2():
    return [0.0, 1.0] + [0.0] * 1022


def test_schema_idempotent():
    conn = _db()
    assert mem.ensure_schema(conn) in ("fts5", "like")
    assert mem.ensure_schema(conn) in ("fts5", "like")


def test_upsert_keyword_vector_hybrid():
    conn = _db()
    assert mem.upsert(conn, "n1", "panne CI runner", "le runner windows timeout", _e1(), "test")
    assert mem.upsert(conn, "n2", "recette gateau", "farine sucre four", _e2(), "test")
    kw = mem.keyword_search(conn, "runner windows timeout")
    assert kw and kw[0][0] == "n1"
    vs = mem.vector_search(conn, _e1())
    assert vs and vs[0][0] == "n1" and vs[0][1] > 0.99
    hy = mem.hybrid_search(conn, "runner timeout", _e1(), top_k=2)
    assert hy[0] == "n1"
    # sans vecteur : mot-cle seul, sans crash
    assert mem.hybrid_search(conn, "gateau", None, top_k=2)[0] == "n2"
    # requete vide -> []
    assert mem.hybrid_search(conn, "", None) == []


def test_bad_dim_texte_seul():
    conn = _db()
    assert mem.upsert(conn, "n3", "titre", "resume court", [0.1] * 384, "test")
    assert mem.vector_search(conn, [0.1] * 384) == []
    assert mem.keyword_search(conn, "resume") != []


def test_local_rerank_heuristique():
    docs = [("a", "gateau chocolat", "four"), ("b", "runner CI timeout", "windows")]
    assert mem.local_rerank("runner timeout windows", docs)[0] == "b"


def test_search_with_rerank_sans_cle_repli_local(monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    conn = _db()
    mem.upsert(conn, "n1", "panne CI runner", "timeout windows", _e1(), "test")
    mem.upsert(conn, "n2", "recette gateau", "four", _e2(), "test")
    out = mem.search_with_rerank(conn, "runner timeout", _e1(), top_k=2)
    assert out and out[0] == "n1"


def test_rerank_sans_cle_none(monkeypatch):
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    assert emb.rerank("q", ["a", "b"]) is None
    assert emb.rerank("", ["a"]) is None


def test_rerank_voyage_mock(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")

    def fake_post(url, payload, headers, timeout):
        assert "rerank" in url
        assert payload["query"] == "runner ?"
        return {"data": [{"index": 1, "relevance_score": 0.9},
                         {"index": 0, "relevance_score": 0.1}]}

    monkeypatch.setattr(emb, "_post", fake_post)
    assert emb.rerank("runner ?", ["gateau", "runner CI"]) == [1, 0]
