"""Tests check_rule_spec.py — SPEC enforcement (errors vs migration warnings)."""

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import check_rule_spec as spec


def test_metadata_valid_on_repo():
    assert spec.check_metadata(REPO) == []


def test_runbooks_valid_on_repo():
    assert spec.check_runbooks(REPO) == []


def test_memories_valid_on_repo():
    assert spec.check_memories(REPO) == []


def test_metadata_rejects_bad_scope(tmp_path):
    (tmp_path / "rules").mkdir()
    (tmp_path / "rules" / "_metadata.yaml").write_text(
        "overrides:\n  rule_x:\n    scope: galaxy\n", encoding="utf-8")
    (tmp_path / "rules" / "rule_x.md").write_text("# x\n", encoding="utf-8")
    errors = spec.check_metadata(tmp_path)
    assert any("scope" in e for e in errors)


def test_runbook_requires_steps(tmp_path):
    (tmp_path / "runbooks").mkdir()
    (tmp_path / "runbooks" / "demo.md").write_text("# Demo\nno steps\n", encoding="utf-8")
    errors = spec.check_runbooks(tmp_path)
    assert any("Steps" in e for e in errors)


def test_memory_requires_frontmatter(tmp_path):
    (tmp_path / "memories").mkdir()
    (tmp_path / "memories" / "2026-01-01-x.md").write_text("# no fm\n", encoding="utf-8")
    errors = spec.check_memories(tmp_path)
    assert any("frontmatter" in e for e in errors)


def test_legacy_audit_flags_long_code_block(tmp_path):
    (tmp_path / "rules").mkdir()
    long_block = "```\n" + "\n".join(f"line {i}" for i in range(12)) + "\n```\n"
    (tmp_path / "rules" / "rule_big.md").write_text("# Big\n" + long_block, encoding="utf-8")
    warnings = spec.audit_legacy_rules(tmp_path)
    assert any("rule_big.md" in w and ">10" in w for w in warnings)
