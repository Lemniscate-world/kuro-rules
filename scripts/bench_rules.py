#!/usr/bin/env python3
"""bench_rules.py — controlled mini-benchmark for kuro-rules distribution.

AIGX-inspired: instead of claiming "rules work", assert 10 load-bearing
properties of the generated targets on every run. Deterministic, offline.

Usage:
  python scripts/bench_rules.py [--root PATH]

Exit 0 if 10/10, exit 1 otherwise. Prints one line per check (PASS/FAIL).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

REPO = Path(__file__).resolve().parent.parent


def _fm(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    assert text.startswith("---\n"), f"{path}: missing frontmatter"
    end = text.index("\n---\n", 4)
    return yaml.safe_load(text[4:end]) or {}


def run_bench(root: Path = REPO) -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = ""):
        results.append((name, bool(ok), detail))

    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    agents = (root / "AGENTS.md").read_text(encoding="utf-8-sig")
    rule_files = sorted((root / "rules").glob("rule_*.md"))

    # 1. AGENTS.md covers every rule file
    entries = [line for line in agents.splitlines() if line.startswith("- **rule_")]
    check("agents-index-coverage", len(entries) == len(rule_files),
          f"{len(entries)}/{len(rule_files)} entries")

    # 2-3. cross-tool stubs point to AGENTS.md contract
    for name, fname in (("claude-stub", "CLAUDE.md"), ("gemini-stub", "GEMINI.md")):
        text = (root / fname).read_text(encoding="utf-8-sig")
        check(name, "AGENTS.md" in text and "CONTRACT" in text, fname)

    # 4. auto rule carries code globs
    fm = _fm(root / ".cursor" / "rules" / "rule_05_06_18_19_38_58_59.mdc")
    check("auto-rule-globs", "**/*.py" in (fm.get("globs") or []),
          str(fm.get("globs")))

    # 5. manual rules never auto-apply
    manuals = ["rule_119_marketing_technique", "rule_120_kuro_marketing",
               "rule_121_pr_fix_marketing"]
    ok = all(_fm(root / ".cursor" / "rules" / f"{m}.mdc").get("alwaysApply") is False
             for m in manuals)
    check("manual-never-auto", ok, ",".join(manuals))

    # 6. entrypoint priority dominates
    fm = _fm(root / ".agents" / "rules" / "rule_01_foundation.md")
    check("entrypoint-priority", fm.get("priority") == 10 and fm.get("trigger") == "always",
          f"priority={fm.get('priority')} trigger={fm.get('trigger')}")

    # 7. marketplace version matches VERSION
    mp = json.loads((root / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    check("marketplace-version", mp.get("version") == version,
          f"{mp.get('version')} vs {version}")

    # 8. every .agents frontmatter trigger valid
    valid = {"always", "auto", "manual"}
    bad = [p.name for p in (root / ".agents" / "rules").glob("*.md")
           if _fm(p).get("trigger") not in valid]
    check("agents-triggers-valid", not bad, f"{len(bad)} invalid" if bad else "all valid")

    # 9. every .mdc description short and present
    bad = []
    for p in (root / ".cursor" / "rules").glob("*.mdc"):
        d = _fm(p).get("description") or ""
        if not d or len(d) > 120:
            bad.append(p.name)
    check("mdc-descriptions", not bad, f"{len(bad)} bad" if bad else "all <=120")

    # 10. copilot canonical path documented
    text = (root / "copilot-instructions.md").read_text(encoding="utf-8-sig")
    check("copilot-canonical", ".github/copilot-instructions.md" in text, "canonical path")

    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Mini-benchmark for generated rule targets.")
    ap.add_argument("--root", default=str(REPO))
    args = ap.parse_args(argv)
    if yaml is None:
        print("FAIL: pyyaml required")
        return 1
    results = run_bench(Path(args.root))
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}: {name} ({detail})")
    print(f"{passed}/{len(results)} checks passed.")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
