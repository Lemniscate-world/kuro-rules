"""Tests generate_targets.py — canonical generator for kuro-rules distribution."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

# Garde R116 : sans PyYAML, ce module doit être SKIPÉ, jamais collection-error.
# Une erreur de collection interrompt pytest (exit 2) et fait échouer TOUT le job
# kuro.yml — publication du portfolio comprise. Convention : test_packaging.py.
yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import generate_targets as gt

REDIRECTOR_LINE_RE = re.compile(r"^-\s+\*\*(rule_[A-Za-z0-9_]+)\*\*", flags=re.M)


def test_collect_targets_count():
    targets = gt.collect_targets(REPO)
    # 62 rules x2 formats + 7 stubs + marketplace = 132
    assert len(targets) >= 130
    assert "AGENTS.md" in targets
    assert "CLAUDE.md" in targets
    assert "GEMINI.md" in targets
    assert ".cursor-plugin/marketplace.json" in targets


def test_agents_index_covers_all_active_rules():
    targets = gt.collect_targets(REPO)
    index = targets["AGENTS.md"]
    entries = set(REDIRECTOR_LINE_RE.findall(index))
    rule_files = {p.stem for p in gt.list_rule_files(REPO)}
    defaults, overrides = gt.load_metadata(REPO)
    metas = {b: gt.rule_meta(b, defaults, overrides, b)
             for b in rule_files}
    active = {b for b, m in metas.items() if m["status"] == "active"}
    assert entries == active
    # file on disk matches generator (no drift)
    on_disk = (REPO / "AGENTS.md").read_text(encoding="utf-8-sig")
    assert on_disk == index


def test_version_consistent():
    version = gt.load_version(REPO)
    assert re.match(r"^\d+\.\d+\.\d+$", version)
    targets = gt.collect_targets(REPO)
    assert f"v{version}" in targets["AGENTS.md"]
    mp = json.loads(targets[".cursor-plugin/marketplace.json"])
    assert mp["version"] == version


def _split_frontmatter(text: str):
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    fm = yaml.safe_load(text[4:end])
    return fm, text[end + 5:]


def test_mdc_frontmatter_valid():
    targets = gt.collect_targets(REPO)
    key = ".cursor/rules/rule_05_06_18_19_38_58_59.mdc"
    assert key in targets
    fm, body = _split_frontmatter(targets[key])
    assert fm["description"]
    assert len(fm["description"]) <= 120
    assert "alwaysApply" in fm
    assert "rules/rule_05_06_18_19_38_58_59.md" in body


def test_agents_rule_frontmatter_valid():
    targets = gt.collect_targets(REPO)
    key = ".agents/rules/rule_119_marketing_technique.md"
    assert key in targets
    fm, body = _split_frontmatter(targets[key])
    assert fm["trigger"] == "manual"
    assert fm["scope"] == "team"
    assert fm["status"] == "active"
    assert fm["priority"] == 1
    assert "docs/**" in (fm.get("paths") or [])


def test_resolve_order_excludes_non_active():
    metas = {
        "a": {"scope": "company", "priority": 2, "status": "active"},
        "b": {"scope": "company", "priority": 2, "status": "draft"},
        "c": {"scope": "team", "priority": 1, "status": "deprecated"},
        "d": {"scope": "service", "priority": 5, "status": "active"},
    }
    ordered = gt.resolve_order(metas)
    assert "b" not in ordered and "c" not in ordered
    assert set(ordered) == {"a", "d"}
    # more specific scope first
    assert ordered[0] == "d"


def test_resolve_order_priority_within_scope():
    metas = {
        "low": {"scope": "company", "priority": 1, "status": "active"},
        "high": {"scope": "company", "priority": 9, "status": "active"},
    }
    ordered = gt.resolve_order(metas)
    assert ordered[0] == "high"


def test_check_mode_clean():
    r = subprocess.run([sys.executable, "scripts/generate_targets.py", "--check"],
                       capture_output=True, text=True, cwd=REPO, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr


def test_metadata_values_valid():
    defaults, overrides = gt.load_metadata(REPO)
    for name, meta in overrides.items():
        if "scope" in meta:
            assert meta["scope"] in gt.VALID_SCOPES, name
        if "status" in meta:
            assert meta["status"] in gt.VALID_STATUS, name
        if "trigger" in meta:
            assert meta["trigger"] in gt.VALID_TRIGGERS, name
