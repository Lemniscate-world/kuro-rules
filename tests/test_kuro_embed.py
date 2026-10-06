"""Tests kuro_embed — dim fixe 1024 + chaine sans cle + garde bad-dim (hermetique)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_embed as emb  # noqa: E402


def test_dimensions_fixes_1024():
    assert emb.dimensions() == 1024
    assert emb.DIMENSIONS == 1024


def test_sans_cle_retourne_none_sans_crasher(monkeypatch):
    for var in ("VOYAGE_API_KEY", "OPENAI_API_KEY", "KURO_EMBED_BASE",
                "KURO_EMBED_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9")  # port ferme
    monkeypatch.delenv("KURO_EMBED_OLLAMA_MODEL", raising=False)
    assert emb.embed(["hello"]) is None
    assert emb.embed_one("hello") is None
    assert emb.available() is None


def test_voyage_ok_transmet_input_type(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    seen = {}

    def fake_post(url, payload, headers, timeout):
        seen["url"] = url
        seen["payload"] = payload
        assert payload["input_type"] in ("query", "document")
        assert payload["output_dimension"] == 1024
        n = len(payload["input"])
        return {"data": [{"embedding": [0.1] * 1024} for _ in range(n)]}

    monkeypatch.setattr(emb, "_post", fake_post)
    vecs = emb.embed(["doc1", "doc2"], input_type="document")
    assert vecs is not None and len(vecs) == 2
    assert all(len(v) == 1024 for v in vecs)
    assert seen["payload"]["input_type"] == "document"
    vecs_q = emb.embed(["q"], input_type="query")
    assert vecs_q is not None and len(vecs_q[0]) == 1024


def test_bad_dim_refuse_repli_mot_cle(monkeypatch):
    # Voyage renvoie 384 dims (all-minilm) -> refuse, autres jambes absentes -> None
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("KURO_EMBED_BASE", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(
        emb, "_post",
        lambda url, payload, headers, timeout:
        {"data": [{"embedding": [0.1] * 384}]} if "voyage" in url or "embeddings" in url else None,
    )
    monkeypatch.setattr(emb, "_get_json", lambda url, timeout=5: {})
    assert emb.embed(["hello"]) is None


def test_check_dim():
    assert emb._check_dim([[0.0] * 1024]) is True
    assert emb._check_dim([[0.0] * 384]) is False
    assert emb._check_dim([]) is False
