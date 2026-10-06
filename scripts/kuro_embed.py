#!/usr/bin/env python3
"""kuro_embed.py — client embeddings unifie pour la memoire Kuro (zero dependance).

Appris de tinyhumansai/openhuman (clone lecture seule autorise par R69
"en apprendre") : `crates/openhuman-core/src/inference/embedding_host`
(factory + managed Voyage-backed + Voyage/OpenAI/Cohere/Ollama/Custom/Noop).

Chaine Kuro (defaut, sans routeur) :
    1. Voyage direct ($VOYAGE_API_KEY, modele $KURO_EMBED_MODEL defaut voyage-4)
    2. OpenAI ($OPENAI_API_KEY, dimensions forcees 1024)
    3. Ollama local bge-m3 ($KURO_EMBED_OLLAMA_MODEL defaut bge-m3, 1024 dims)
    4. Custom OpenAI-compatible ($KURO_EMBED_BASE + $KURO_EMBED_KEY)
    5. Aucun -> retourne None ; l'appelant reste en recherche mot-cle (Noop).

Format disque fixe a 1024 dims (comme OpenHuman Memory Tree) : tout vecteur
d'une autre taille est refuse (bad-dim) pour garder un seul espace d'embedding.
input_type query|document (recommandation Voyage pour le RAG).

Usage:
    from kuro_embed import embed, embed_one, available
    vecs = embed(["titre + resume"], input_type="document")
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DIMENSIONS = 1024
DEFAULT_VOYAGE_MODEL = "voyage-4"
DEFAULT_VOYAGE_BASE = "https://api.voyageai.com/v1"
DEFAULT_OPENAI_MODEL = "text-embedding-3-small"
DEFAULT_OPENAI_BASE = "https://api.openai.com/v1"
DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "bge-m3"


def dimensions() -> int:
    """Dimension fixe de l'espace d'embedding Kuro."""
    return DIMENSIONS


def _post(url: str, payload: dict, headers: dict, timeout: int) -> dict | None:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _get_json(url: str, timeout: int = 5) -> dict | None:
    req = urllib.request.Request(url, headers={"User-Agent": "Kuro/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def _check_dim(vecs) -> bool:
    """Tous les vecteurs font exactement 1024 dims."""
    try:
        return bool(vecs) and all(len(v) == DIMENSIONS for v in vecs)
    except Exception:
        return False


def _voyage(texts: list[str], input_type: str) -> tuple[list | None, str]:
    key = os.environ.get("VOYAGE_API_KEY")
    if not key:
        return None, "no-key"
    base = os.environ.get("KURO_EMBED_VOYAGE_BASE", DEFAULT_VOYAGE_BASE)
    model = os.environ.get("KURO_EMBED_MODEL", DEFAULT_VOYAGE_MODEL)
    itype = input_type if input_type in ("query", "document") else "document"
    data = _post(
        f"{base}/embeddings",
        {"input": texts, "model": model, "input_type": itype,
         "output_dimension": DIMENSIONS, "truncation": True},
        {"Authorization": f"Bearer {key}"},
        timeout=60,
    )
    if not data:
        return None, "error"
    try:
        vecs = [d["embedding"] for d in data["data"]]
        if _check_dim(vecs):
            return vecs, "ok"
        return None, "bad-dim"
    except Exception:
        return None, "bad-shape"


def _openai(texts: list[str]) -> tuple[list | None, str]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None, "no-key"
    base = os.environ.get("OPENAI_BASE", DEFAULT_OPENAI_BASE)
    model = os.environ.get("KURO_EMBED_OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
    data = _post(
        f"{base}/embeddings",
        {"input": texts, "model": model, "dimensions": DIMENSIONS},
        {"Authorization": f"Bearer {key}"},
        timeout=60,
    )
    if not data:
        return None, "error"
    try:
        vecs = [d["embedding"] for d in data["data"]]
        if _check_dim(vecs):
            return vecs, "ok"
        return None, "bad-dim"
    except Exception:
        return None, "bad-shape"


def _ollama(texts: list[str]) -> tuple[list | None, str]:
    model = os.environ.get("KURO_EMBED_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    base = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    tags = _get_json(f"{base}/api/tags") or {}
    names = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]
    if model not in names:
        return None, "not-pulled" if names else "unreachable"
    vecs: list = []
    for t in texts:
        data = _post(f"{base}/api/embed",
                     {"model": model, "input": t}, {}, timeout=60)
        if not data:
            return None, "error"
        try:
            v = data.get("embeddings", [data.get("embedding")])[0]
        except Exception:
            return None, "bad-shape"
        if not isinstance(v, list) or len(v) != DIMENSIONS:
            return None, "bad-dim"
        vecs.append(v)
    return (vecs, "ok") if vecs else (None, "empty")


def _custom(texts: list[str]) -> tuple[list | None, str]:
    base = os.environ.get("KURO_EMBED_BASE")
    key = os.environ.get("KURO_EMBED_KEY", "")
    if not base:
        return None, "no-base"
    model = os.environ.get("KURO_EMBED_CUSTOM_MODEL", DEFAULT_OLLAMA_MODEL)
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    data = _post(f"{base.rstrip('/')}/embeddings",
                 {"input": texts, "model": model, "dimensions": DIMENSIONS},
                 headers, timeout=60)
    if not data:
        return None, "error"
    try:
        vecs = [d["embedding"] for d in data["data"]]
        if _check_dim(vecs):
            return vecs, "ok"
        return None, "bad-dim"
    except Exception:
        return None, "bad-shape"


def embed(texts: list[str], input_type: str = "document") -> list | None:
    """Vecteurs 1024-d pour `texts`, ou None (repli mot-cle). Jamais d'exception."""
    try:
        if not texts or not isinstance(texts, list):
            return None
        clean = [str(t)[:8000] for t in texts if str(t).strip()][:100]
        if not clean:
            return None
        for fn in (_voyage_with_type(input_type), _openai, _ollama, _custom):
            try:
                vecs, status = fn(clean)
            except Exception:
                continue
            if vecs:
                return vecs
        return None
    except Exception:
        return None


def _voyage_with_type(input_type: str):
    return lambda texts: _voyage(texts, input_type)


def embed_one(text: str, input_type: str = "document") -> list | None:
    """Un seul vecteur, ou None."""
    try:
        vecs = embed([text], input_type=input_type)
        return vecs[0] if vecs else None
    except Exception:
        return None


def available() -> str | None:
    """Nom du moteur dispo sans consommer d'appel reseau payant."""
    if os.environ.get("VOYAGE_API_KEY"):
        return "voyage"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("KURO_EMBED_BASE"):
        return "custom"
    model = os.environ.get("KURO_EMBED_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
    tags = _get_json(os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL) + "/api/tags") or {}
    names = [m.get("name", "") for m in tags.get("models", [])]
    if model in names:
        return "ollama-local"
    return None


DEFAULT_RERANK_MODEL = "rerank-2.5-lite"


def rerank(query: str, docs: list[str], top_n: int | None = None) -> list[int] | None:
    """Indices de `docs` tries par pertinence (Voyage rerank), ou None.

    $VOYAGE_API_KEY absente -> None (l'appelant bascule sur heuristique locale).
    Jamais d'exception, jamais plus de 100 docs.
    """
    try:
        if not query or not docs:
            return None
        if not os.environ.get("VOYAGE_API_KEY"):
            return None
        clean = [str(d)[:4000] for d in docs[:100]]
        base = os.environ.get("KURO_EMBED_VOYAGE_BASE", DEFAULT_VOYAGE_BASE)
        model = os.environ.get("KURO_RERANK_MODEL", DEFAULT_RERANK_MODEL)
        payload: dict = {"query": str(query)[:8000], "documents": clean, "model": model}
        if top_n:
            payload["top_k"] = max(1, min(int(top_n), len(clean)))
        data = _post(
            f"{base}/rerank", payload,
            {"Authorization": f"Bearer {os.environ['VOYAGE_API_KEY']}"},
            timeout=60,
        )
        if not data:
            return None
        order = sorted(data.get("data", []),
                       key=lambda r: float(r.get("relevance_score", 0)), reverse=True)
        idx = [int(r["index"]) for r in order if 0 <= int(r["index"]) < len(clean)]
        return idx if idx else None
    except Exception:
        return None


if __name__ == "__main__":
    print(f"dimensions: {dimensions()}")
    print(f"moteur disponible: {available() or 'aucun (repli mot-cle)'}")
