#!/usr/bin/env python3
"""kuro_memory.py — recherche hybride memoire Kuro (zero dependance, sidecar).

Sidecar, jamais d'ALTER sur `memory_nodes` (table du daemon, schema hors repo) :
tables annexes creees IF NOT EXISTS dans la meme base :
    memory_embeddings(node_key TEXT PK, title TEXT, summary TEXT,
                      vec TEXT JSON, dim INT, model TEXT, updated_at TEXT)
    memory_fts FTS5(node_key, title, summary) ou table LIKE si FTS5 absent.

Pipeline : keyword top-20 (FTS5/LIKE) + vector top-20 (cosine pur python)
+ fusion RRF (k=60) + rerank Voyage (`kuro_embed.rerank`) ou heuristique locale.
Sans vecteur ni cle : recherche mot-cle seule. Jamais d'exception.
"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import time

try:
    import kuro_embed as _emb
except Exception:  # hermetique : module absent -> repli local
    _emb = None

DIMENSIONS = 1024
_RRF_K = 60

_TOKEN = re.compile(r"[a-z0-9\u00e0\u00e2\u00e4\u00e7\u00e9\u00e8\u00ea\u00eb\u00ee\u00ef\u00f4\u00f6\u00fb\u00f9]+", re.I)


def _tokens(text: str) -> list[str]:
    try:
        return _TOKEN.findall(str(text or "").lower())
    except Exception:
        return []


def ensure_schema(conn: sqlite3.Connection) -> str:
    """Cree les tables annexes. Retourne 'fts5' | 'like' | 'none'."""
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS memory_embeddings(
                 node_key TEXT PRIMARY KEY, title TEXT, summary TEXT,
                 vec TEXT, dim INTEGER, model TEXT, updated_at TEXT)"""
        )
        try:
            conn.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts"
                " USING fts5(node_key, title, summary)"
            )
            return "fts5"
        except Exception:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS memory_fts(
                     node_key TEXT PRIMARY KEY, title TEXT, summary TEXT)"""
            )
            return "like"
    except Exception:
        return "none"


def _fts_mode(conn: sqlite3.Connection) -> str:
    try:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='memory_fts'").fetchone()
        sql = (row[0] if row else "") or ""
        return "fts5" if "fts5" in sql.lower() else "like"
    except Exception:
        return "like"


def upsert(conn: sqlite3.Connection, node_key: str, title: str = "",
           summary: str = "", vec: list | None = None,
           model: str = "") -> bool:
    """Stocke titre+resume+vec 1024-d. Vec de mauvaise dim -> texte seul."""
    try:
        mode = ensure_schema(conn)
        if mode == "none" or not node_key:
            return False
        good_vec = None
        if isinstance(vec, list) and len(vec) == DIMENSIONS:
            try:
                good_vec = json.dumps([float(x) for x in vec])
            except Exception:
                good_vec = None
        conn.execute(
            """INSERT INTO memory_embeddings(node_key,title,summary,vec,dim,model,updated_at)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(node_key) DO UPDATE SET
                 title=excluded.title, summary=excluded.summary, vec=excluded.vec,
                 dim=excluded.dim, model=excluded.model, updated_at=excluded.updated_at""",
            (str(node_key), str(title)[:500], str(summary)[:2000], good_vec,
             DIMENSIONS if good_vec else 0, str(model)[:80],
             time.strftime("%Y-%m-%d %H:%M:%S")),
        )
        if _fts_mode(conn) == "fts5":
            conn.execute("DELETE FROM memory_fts WHERE node_key=?", (str(node_key),))
            conn.execute("INSERT INTO memory_fts(node_key,title,summary) VALUES(?,?,?)",
                         (str(node_key), str(title)[:500], str(summary)[:2000]))
        else:
            conn.execute(
                """INSERT INTO memory_fts(node_key,title,summary) VALUES(?,?,?)
                   ON CONFLICT(node_key) DO UPDATE SET
                     title=excluded.title, summary=excluded.summary""",
                (str(node_key), str(title)[:500], str(summary)[:2000]),
            )
        try:
            conn.commit()
        except Exception:
            pass
        return True
    except Exception:
        return False


def _cosine(a: list, b: list) -> float:
    try:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else 0.0
    except Exception:
        return 0.0


def vector_search(conn: sqlite3.Connection, query_vec: list,
                  top_k: int = 20) -> list[tuple[str, float]]:
    """Top cosine sur les embeddings stockes. [] si rien."""
    try:
        if not isinstance(query_vec, list) or len(query_vec) != DIMENSIONS:
            return []
        rows = conn.execute(
            "SELECT node_key, vec FROM memory_embeddings WHERE vec IS NOT NULL"
            " LIMIT 2000").fetchall()
        scored: list[tuple[str, float]] = []
        for key, blob in rows:
            try:
                v = json.loads(blob)
            except Exception:
                continue
            if not isinstance(v, list) or len(v) != DIMENSIONS:
                continue
            scored.append((str(key), _cosine(query_vec, v)))
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[: max(1, top_k)]
    except Exception:
        return []


def keyword_search(conn: sqlite3.Connection, query: str,
                   top_k: int = 20) -> list[tuple[str, float]]:
    """FTS5 MATCH ou LIKE. Score heuristique (nb tokens couverts)."""
    try:
        toks = [t for t in _tokens(query) if len(t) > 1][:10]
        if not toks:
            return []
        ensure_schema(conn)
        if _fts_mode(conn) == "fts5":
            match = " OR ".join(f'"{t}"' for t in toks)
            try:
                rows = conn.execute(
                    """SELECT node_key, title, summary FROM memory_fts
                       WHERE memory_fts MATCH ? LIMIT ?""",
                    (match, max(1, top_k * 2))).fetchall()
            except Exception:
                rows = []
        else:
            like = "%" + "%".join(toks[:3]) + "%"
            try:
                rows = conn.execute(
                    """SELECT node_key, title, summary FROM memory_fts
                       WHERE title LIKE ? OR summary LIKE ? LIMIT ?""",
                    (like, like, max(1, top_k * 2))).fetchall()
            except Exception:
                rows = []
        scored = []
        for key, title, summary in rows:
            hay = f"{title} {summary}".lower()
            hits = sum(1 for t in toks if t in hay)
            if hits:
                scored.append((str(key), float(hits)))
        scored.sort(key=lambda p: p[1], reverse=True)
        return scored[: max(1, top_k)]
    except Exception:
        return []


def _rrf(lists: list[list[tuple[str, float]]], top_k: int) -> list[str]:
    fused: dict[str, float] = {}
    for ranked in lists:
        for rank, (key, _s) in enumerate(ranked):
            fused[key] = fused.get(key, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return [k for k, _ in sorted(fused.items(), key=lambda p: p[1], reverse=True)[: max(1, top_k)]]


def hybrid_search(conn: sqlite3.Connection, query: str,
                  query_vec: list | None = None,
                  top_k: int = 5) -> list[str]:
    """RRF(keyword top-20, vector top-20). Sans vec : mot-cle seul."""
    try:
        kw = keyword_search(conn, query, 20)
        lists: list[list[tuple[str, float]]] = [kw] if kw else []
        if isinstance(query_vec, list) and len(query_vec) == DIMENSIONS:
            vs = vector_search(conn, query_vec, 20)
            if vs:
                lists.append(vs)
        if not lists:
            return []
        if len(lists) == 1:
            return [k for k, _ in lists[0][: max(1, top_k)]]
        return _rrf(lists, top_k)
    except Exception:
        return []


def local_rerank(query: str, docs: list[tuple[str, str, str]]) -> list[str]:
    """Heuristique locale : recouvrement tokens + bonus titre. Repli sans cle."""
    try:
        toks = set(_tokens(query))
        if not toks or not docs:
            return [k for k, _t, _s in docs]
        scored = []
        for key, title, summary in docs:
            tt, st = set(_tokens(title)), set(_tokens(summary))
            overlap = len(toks & (tt | st))
            title_hit = len(toks & tt) * 0.5
            scored.append((str(key), overlap + title_hit))
        scored.sort(key=lambda p: p[1], reverse=True)
        return [k for k, _ in scored]
    except Exception:
        return [k for k, _t, _s in docs]


def search_with_rerank(conn: sqlite3.Connection, query: str,
                       query_vec: list | None = None,
                       top_k: int = 5) -> list[str]:
    """Hybrid puis Voyage rerank si cle, sinon heuristique locale."""
    try:
        cands = hybrid_search(conn, query, query_vec, max(10, top_k * 2))
        if not cands:
            return []
        cands = cands[:20]
        placeholders = ",".join("?" for _ in cands)
        try:
            rows = {r[0]: (r[1], r[2]) for r in conn.execute(
                f"SELECT node_key, title, summary FROM memory_embeddings"
                f" WHERE node_key IN ({placeholders})", cands).fetchall()}
        except Exception:
            rows = {}
        docs = [(k, (rows.get(k) or ("", ""))[0], (rows.get(k) or ("", ""))[1])
                for k in cands]
        order = None
        try:
            if _emb is not None:
                order = _emb.rerank(query, [f"{t} {s}" for _k, t, s in docs],
                                    top_n=top_k)
        except Exception:
            order = None
        if order:
            return [cands[i] for i in order if 0 <= i < len(cands)][:top_k]
        return local_rerank(query, docs)[:top_k]
    except Exception:
        return []
