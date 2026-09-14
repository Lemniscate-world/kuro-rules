"""Tests kuro_watchdog — merges recents + echecs (logique pure, sans reseau)."""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_watchdog as kw  # noqa: E402


def _pr(number, merged_hours_ago=None):
    from datetime import timedelta
    when = (datetime.now(timezone.utc) - timedelta(hours=merged_hours_ago)).isoformat() \
        if merged_hours_ago is not None else None
    return {"number": number, "merged_at": when, "merge_commit_sha": f"sha{number}"}


def test_recent_merges_fenetre_48h(monkeypatch):
    data = [_pr(1, 5), _pr(2, 100), {"number": 3, "merged_at": None, "merge_commit_sha": "x"}]
    monkeypatch.setattr(kw, "api", lambda *a, **k: (200, data))
    out = kw.recent_merges("o/r", "t")
    assert [p["number"] for p in out] == [1]


def test_merge_failures_filtre(monkeypatch):
    data = {"check_runs": [{"name": "a", "conclusion": "success"},
                           {"name": "b", "conclusion": "failure"},
                           {"name": "c", "conclusion": "cancelled"}]}
    monkeypatch.setattr(kw, "api", lambda *a, **k: (200, data))
    assert kw.merge_failures("o/r", "sha", "t") == ["b"]
    monkeypatch.setattr(kw, "api", lambda *a, **k: (500, None))
    assert kw.merge_failures("o/r", "sha", "t") == []
