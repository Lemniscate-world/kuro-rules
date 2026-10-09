"""Tests upstream_watch — qualification pure R119 + rendu file (aucun appel reseau)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import upstream_watch as uw


def _now():
    return datetime(2026, 10, 8, 12, 0, 0, tzinfo=timezone.utc)


def _item(n, comments, updated, kind="issue", is_pr=False):
    return {"number": n, "title": f"t{n}", "commentsCount": comments,
            "updatedAt": updated, "url": f"https://example.com/{n}",
            "kind": kind, "isPullRequest": is_pr, "repo": "O/R"}


def test_qualify_garde_0_a_2_reponses():
    items = [_item(1, 0, "2026-10-08T10:00:00Z"),
             _item(2, 2, "2026-10-08T10:00:00Z"),
             _item(3, 3, "2026-10-08T10:00:00Z")]
    out = uw.qualify(items, now=_now())
    assert [x["number"] for x in out] == [1, 2]


def test_qualify_rejette_stale():
    items = [_item(1, 0, "2026-10-08T10:00:00Z"),
             _item(2, 0, "2026-01-01T10:00:00Z")]
    out = uw.qualify(items, max_age_days=180, now=_now())
    assert [x["number"] for x in out] == [1]


def test_qualify_exclut_pr_du_flux_issues():
    items = [_item(1, 0, "2026-10-08T10:00:00Z", is_pr=True)]
    assert uw.qualify(items, now=_now()) == []


def test_qualify_trie_plus_recent_d_abord():
    items = [_item(1, 0, "2026-10-01T10:00:00Z"),
             _item(2, 0, "2026-10-08T10:00:00Z")]
    out = uw.qualify(items, now=_now())
    assert [x["number"] for x in out] == [2, 1]


def test_render_queue_contient_gate_et_url():
    c = _item(685, 1, "2026-10-07T15:30:12Z")
    c["body_excerpt"] = "resume"
    md = uw.render_queue([c], "2026-10-08T12:00:00+00:00", ["O/R"])
    assert "NE JAMAIS POSTER SANS RELECTURE HUMAINE" in md
    assert "https://example.com/685" in md
    assert "R120" in md


def test_render_queue_vide_sans_crash():
    md = uw.render_queue([], "2026-10-08T12:00:00+00:00", ["O/R"])
    assert "aucun candidat" in md
