"""Tests kuro_omnigraph_branch — logique pure + runner mocke, zero binaire, zero reseau."""

from unittest.mock import patch

import kuro_omnigraph_branch as kb


NODE = '{"type": "Decision", "data": {"slug": "d1", "statement": "s"}}'
EDGE = '{"edge": "Makes", "from": "neuraldbg", "to": "d1"}'


def test_parse_delta_ok():
    records = kb.parse_delta(NODE + "\n" + EDGE + "\n")
    assert len(records) == 2


def test_parse_delta_vide_refuse():
    for bad in ["", "   \n  "]:
        try:
            kb.parse_delta(bad)
            raise AssertionError("HarvestError attendu")
        except kb.HarvestError:
            pass


def test_parse_delta_formes_invalides():
    for bad in [
        '{"oops": 1}',
        '{"type": "X"}',
        '{"type": "X", "data": {"name": "sans-slug"}}',
        '{"edge": "Makes", "from": "a"}',
        "[1, 2]",
        "{oops",
    ]:
        try:
            kb.parse_delta(bad)
            raise AssertionError(f"HarvestError attendu pour {bad}")
        except kb.HarvestError:
            pass


def test_parse_delta_cles_privees_refusees():
    for bad in [
        '{"type": "Project", "data": {"slug": "x", "mrr": 10}}',
        '{"type": "Project", "data": {"slug": "x", "expenses": []}}',
        '{"type": "Rule", "data": {"slug": "y", "token": "abc"}}',
    ]:
        try:
            kb.parse_delta(bad)
            raise AssertionError(f"HarvestError attendu pour {bad}")
        except kb.HarvestError as exc:
            assert "R111" in str(exc)


def test_diff_entities():
    main = [
        '{"type": "Project", "id": "a"}',
        '{"type": "Project", "id": "b"}',
    ]
    branch = [
        '{"type": "Project", "id": "b"}',
        '{"type": "Project", "id": "c"}',
    ]
    result = kb.diff_entities(main, branch)
    assert result["added"] == ["Project:c"]
    assert result["removed"] == ["Project:a"]
    assert result["added_count"] == 1 and result["removed_count"] == 1


def test_diff_vide():
    result = kb.diff_entities([], [])
    assert result["added_count"] == 0 and result["removed_count"] == 0


def test_merge_sans_review_refuse():
    for bad in [None, "", "   "]:
        try:
            kb.check_reviewed(bad)
            raise AssertionError("HarvestError attendu")
        except kb.HarvestError as exc:
            assert "review" in str(exc).lower()


def test_resolve_bin_priorites(tmp_path, monkeypatch):
    fake = tmp_path / "omnigraph.exe"
    fake.write_text("x", encoding="utf-8")
    monkeypatch.setenv("OMNIGRAPH_BIN", str(fake))
    assert kb.resolve_bin() == str(fake)
    assert kb.resolve_bin("explicit") == "explicit"


def test_resolve_bin_absent(monkeypatch):
    monkeypatch.delenv("OMNIGRAPH_BIN", raising=False)
    with patch("shutil.which", return_value=None):
        try:
            kb.resolve_bin()
            raise AssertionError("HarvestError attendu")
        except kb.HarvestError:
            pass


def test_cmd_harvest_appelle_binaire(tmp_path):
    delta = tmp_path / "d.jsonl"
    delta.write_text(NODE + "\n", encoding="utf-8")
    calls = []
    with patch.object(kb, "run_omnigraph", side_effect=lambda b, a: calls.append(a) or ""):
        msg = kb.cmd_harvest("bin", "g.omni", "agent/h1", delta, "main")
    assert "1 entites stagees" in msg
    assert calls[0][:3] == ["branch", "create", "agent/h1"]
    assert calls[1][:2] == ["load", "--data"]


def test_cmd_merge_gate(tmp_path):
    with patch.object(kb, "run_omnigraph", return_value=""):
        try:
            kb.cmd_merge("bin", "g.omni", "agent/h1", "main", None)
            raise AssertionError("HarvestError attendu")
        except kb.HarvestError:
            pass
        msg = kb.cmd_merge("bin", "g.omni", "agent/h1", "main", "vu: ok")
    assert "merge dans main" in msg
