"""Tests scoping — triggers, paths/globs, local overrides (SPEC + agent-rules-spec)."""

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent


def _fm(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    assert text.startswith("---\n")
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end])


def test_manual_rules_never_auto_applied():
    for stem in ("rule_119_marketing_technique", "rule_120_kuro_marketing",
                 "rule_121_pr_fix_marketing"):
        agents_fm = _fm(REPO / ".agents" / "rules" / f"{stem}.md")
        assert agents_fm["trigger"] == "manual", stem
        mdc_fm = _fm(REPO / ".cursor" / "rules" / f"{stem}.mdc")
        assert mdc_fm["alwaysApply"] is False, stem


def test_auto_rules_carry_paths_and_globs():
    agents_fm = _fm(REPO / ".agents" / "rules" / "rule_05_06_18_19_38_58_59.md")
    assert agents_fm["trigger"] == "auto"
    assert any("**/*.py" in p for p in agents_fm.get("paths", []))
    mdc_fm = _fm(REPO / ".cursor" / "rules" / "rule_05_06_18_19_38_58_59.mdc")
    assert mdc_fm["alwaysApply"] is False
    assert "**/*.py" in (mdc_fm.get("globs") or [])


def test_always_rules_have_no_path_restriction():
    agents_fm = _fm(REPO / ".agents" / "rules" / "rule_01_foundation.md")
    assert agents_fm["trigger"] == "always"
    assert agents_fm.get("paths") in (None, [])


def test_local_overrides_gitignored():
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert ".agents/local/" in gitignore
    assert (REPO / ".agents" / "local" / ".gitkeep").exists()


def test_generated_dirs_match_metadata_count():
    meta = yaml.safe_load((REPO / "rules" / "_metadata.yaml").read_text(encoding="utf-8"))
    overrides = meta.get("overrides", {})
    # every override with default active status must have generated files
    for name, m in overrides.items():
        if m.get("status", "active") != "active":
            continue
        assert (REPO / ".agents" / "rules" / f"{name}.md").exists(), name
        assert (REPO / ".cursor" / "rules" / f"{name}.mdc").exists(), name
