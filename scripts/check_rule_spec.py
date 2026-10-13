#!/usr/bin/env python3
"""check_rule_spec.py — enforce SPEC.md (rules vs runbooks vs memories).

Hard errors (exit 1):
  - rules/_metadata.yaml: unknown scope/status/trigger, bad types
  - runbooks/*.md: missing Steps section
  - memories/*.md (except README.md): missing/invalid frontmatter
  - generated drift is NOT checked here (use generate_targets.py --check)

Warnings (exit 0, legacy migration aid):
  - rules/rule_*.md over 1000 lines
  - fenced code block over 10 lines
  - procedure markers ("Step 1" + "Step 2") suggesting runbook extraction

Usage:
  python scripts/check_rule_spec.py [--strict]  # --strict: warnings become errors
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

REPO = Path(__file__).resolve().parent.parent

VALID_SCOPES = {"company", "team", "service"}
VALID_STATUS = {"active", "draft", "deprecated"}
VALID_TRIGGERS = {"always", "auto", "manual"}
VALID_MEMORY_TYPES = {"lesson", "gotcha", "decision"}

FENCE_RE = re.compile(r"^```")


def check_metadata(root: Path) -> list[str]:
    errors = []
    p = root / "rules" / "_metadata.yaml"
    if not p.exists():
        return ["rules/_metadata.yaml missing"]
    if yaml is None:
        return ["pyyaml required"]
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    overrides = data.get("overrides", {}) or {}
    for name, meta in overrides.items():
        if not (root / "rules" / (name + ".md")).exists():
            errors.append(f"metadata: {name} has no matching rules/{name}.md")
        if "scope" in meta and meta["scope"] not in VALID_SCOPES:
            errors.append(f"metadata: {name}.scope={meta['scope']!r} invalid")
        if "status" in meta and meta["status"] not in VALID_STATUS:
            errors.append(f"metadata: {name}.status={meta['status']!r} invalid")
        if "trigger" in meta and meta["trigger"] not in VALID_TRIGGERS:
            errors.append(f"metadata: {name}.trigger={meta['trigger']!r} invalid")
        for key in ("paths", "globs"):
            if key in meta and not isinstance(meta[key], list):
                errors.append(f"metadata: {name}.{key} must be a list")
        if "priority" in meta and not isinstance(meta["priority"], int):
            errors.append(f"metadata: {name}.priority must be int")
    return errors


def check_runbooks(root: Path) -> list[str]:
    errors = []
    d = root / "runbooks"
    if not d.exists():
        return ["runbooks/ missing"]
    for f in sorted(d.glob("*.md")):
        if f.name.upper() == "README.MD":
            continue
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        if "## Steps" not in text and "## steps" not in text.lower():
            errors.append(f"runbooks/{f.name}: missing '## Steps' section")
        if "## Prerequisites" not in text and "prereq" not in text.lower():
            errors.append(f"runbooks/{f.name}: missing prerequisites")
    return errors


def check_memories(root: Path) -> list[str]:
    errors = []
    d = root / "memories"
    if not d.exists():
        return ["memories/ missing"]
    for f in sorted(d.glob("*.md")):
        if f.name.upper() == "README.MD" or f.name.startswith("_"):
            continue
        text = f.read_text(encoding="utf-8-sig", errors="replace")
        if not text.startswith("---\n"):
            errors.append(f"memories/{f.name}: missing YAML frontmatter")
            continue
        end = text.find("\n---\n", 4)
        if end < 0:
            errors.append(f"memories/{f.name}: unclosed frontmatter")
            continue
        if yaml is None:
            continue
        fm = yaml.safe_load(text[4:end]) or {}
        if fm.get("type") not in VALID_MEMORY_TYPES:
            errors.append(f"memories/{f.name}: type must be one of {sorted(VALID_MEMORY_TYPES)}")
        if "why" not in fm or not fm["why"]:
            errors.append(f"memories/{f.name}: frontmatter needs 'why'")
    return errors


def audit_legacy_rules(root: Path) -> list[str]:
    """Migration aid only — always warnings, never errors (unless --strict)."""
    warnings = []
    for f in sorted((root / "rules").glob("rule_*.md")):
        lines = f.read_text(encoding="utf-8-sig", errors="replace").splitlines()
        if len(lines) > 1000:
            warnings.append(f"{f.name}: {len(lines)} lines (>1000, split)")
        # longest fenced code block
        in_fence = False
        block_len = 0
        longest = 0
        for line in lines:
            if FENCE_RE.match(line.strip()):
                if in_fence:
                    longest = max(longest, block_len)
                    block_len = 0
                    in_fence = False
                else:
                    in_fence = True
            elif in_fence:
                block_len += 1
        if longest > 10:
            warnings.append(f"{f.name}: code block of {longest} lines (>10, externalize to runbooks/)")
        text = "\n".join(lines)
        if "Step 1" in text and "Step 2" in text:
            warnings.append(f"{f.name}: procedure markers (Step 1/Step 2, consider runbooks/)")
    return warnings


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Enforce SPEC.md.")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--root", default=str(REPO))
    args = ap.parse_args(argv)
    root = Path(args.root)

    errors = check_metadata(root) + check_runbooks(root) + check_memories(root)
    warnings = audit_legacy_rules(root)

    for w in warnings:
        print(f"WARN: {w}")
    if errors:
        for e in errors:
            print(f"ERROR: {e}")
        print(f"FAIL: {len(errors)} error(s), {len(warnings)} warning(s).")
        return 1
    if args.strict and warnings:
        print(f"FAIL(strict): {len(warnings)} warning(s).")
        return 1
    print(f"OK: spec checks passed ({len(warnings)} migration warning(s)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
