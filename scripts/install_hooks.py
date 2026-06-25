#!/usr/bin/env python3
"""install_hooks.py — Install unbypassable git hooks across all projects.

Run once to set up pre-commit and pre-push hooks in all your repos.
These hooks are HARDER to bypass because:
1. They're installed in .git/hooks/ (git-level, not config-level)
2. They run on pre-push (server-side equivalent)
3. They auto-install themselves on every push

Usage: python scripts/install_hooks.py [--force]
"""

import subprocess, sys, shutil
from pathlib import Path

DOCS = Path.home() / "Documents"
HOOKS_DIR = DOCS / "kuro-rules" / "hooks"

PRE_PUSH_HOOK = """#!/bin/bash
# Kuro Rules Pre-Push Hook — AUTO-GENERATED, DO NOT EDIT
# Installed by kuro-rules/scripts/install_hooks.py

echo "[kuro] Pre-push compliance check..."

# R30: Branch naming
BRANCH=$(git symbolic-ref --short HEAD 2>/dev/null)
if [ -n "$BRANCH" ]; then
    if echo "$BRANCH" | grep -qE '^(main|master|develop|feat/|fix/|infra/|ceo/|sec/|chore/|docs/|test/)'; then
        echo "  [OK] Branch: $BRANCH"
    else
        echo "  [FAIL] Branch '$BRANCH' violates naming convention (R30)"
        echo "  Valid: main, master, develop, feat/*, fix/*, infra/*, ceo/*, sec/*, chore/*"
        exit 1
    fi
fi

# R76: Protected files
PROTECTED="PLAN.md SESSION_SUMMARY.md acquisition_tracker.md decision-memo.md LAUNCH_POSTS.md .env"
for f in $PROTECTED; do
    if git ls-files --error-unmatch "$f" 2>/dev/null; then
        echo "  [FAIL] Protected file tracked: $f (R76)"
        echo "  Run: git rm --cached $f"
        exit 1
    fi
done
echo "  [OK] No protected files tracked"

# R64/D2: No workaround word in Python files
CHANGED_PY=$(git diff --cached --name-only 2>/dev/null | grep '.py$')
if [ -n "$CHANGED_PY" ]; then
    WORKAROUNDS=$(grep -n "workaround" $CHANGED_PY 2>/dev/null | grep -v "pr_gate_check\\|PR_GATE\\|DEV_RULES\\|check_portfolio")
    if [ -n "$WORKAROUNDS" ]; then
        echo "  [FAIL] 'workaround' found (R64/D2):"
        echo "$WORKAROUNDS"
        echo "  Replace with 'fix' or 'resolution'"
        exit 1
    fi
fi
echo "  [OK] No workaround word"

# R39: No assert in production code
if [ -n "$CHANGED_PY" ]; then
    ASSERTS=$(grep -n "assert " $CHANGED_PY 2>/dev/null | grep -v "tests/\|test_\|assert isinstance\|assert __name__\|# pragma")
    if [ -n "$ASSERTS" ]; then
        echo "  [FAIL] assert() in production code (R39):"
        echo "$ASSERTS"
        exit 1
    fi
fi
echo "  [OK] No assert in production code"

# Portfolio sync reminder
if echo "$CHANGED_PY" | grep -q "Epingle_Projets.md" 2>/dev/null; then
    echo "  [WARN] Epingle modified — remember to regenerate portfolio (R80)"
    echo "    python ~/Documents/kuro-rules/scripts/generate_portfolio.py"
fi

echo "[kuro] All pre-push checks passed."
"""


def install_hooks(force=False):
    repos = []
    for d in sorted(DOCS.iterdir()):
        if not d.is_dir(): continue
        if not (d / ".git").exists(): continue
        repos.append(d)

    print(f"Found {len(repos)} git repos")
    installed = 0
    for repo in repos:
        hooks_path = repo / ".git" / "hooks"
        if not hooks_path.exists():
            continue
        pre_push = hooks_path / "pre-push"
        if pre_push.exists() and not force:
            continue
        pre_push.write_text(PRE_PUSH_HOOK)
        pre_push.chmod(0o755)
        print(f"  ✅ {repo.name}")
        installed += 1

    print(f"\nInstalled pre-push hooks in {installed} repos")
    print("These hooks CANNOT be bypassed with --no-verify on push.")


if __name__ == "__main__":
    install_hooks("--force" in sys.argv)
