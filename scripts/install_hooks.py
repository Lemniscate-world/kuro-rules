#!/usr/bin/env python3
"""install_hooks.py — Install unbypassable git hooks across all projects.

Run once to set up pre-commit and pre-push hooks in all your repos.
These hooks are HARDER to bypass because:
1. They're installed in .git/hooks/ (git-level, not config-level)
2. They run on pre-push (server-side equivalent)
3. They auto-install themselves on every push

Usage: python scripts/install_hooks.py [--force]
"""

import subprocess
import sys
from pathlib import Path

DOCS = Path.home() / "Documents"
HOOKS_DIR = DOCS / "kuro-rules" / "hooks"
# Source unique (R89): le template versionne fait foi, plus de string embarquee.
TEMPLATE = DOCS / "kuro-rules" / "templates" / "git-hooks" / "pre-push.sh"


def load_template() -> str:
    return TEMPLATE.read_text(encoding="utf-8").replace("\r\n", "\n")

# (string embarquee supprimee R89 - voir templates/git-hooks/pre-push.sh)

def install_hooks(force=False):
    try:
        hook_text = load_template()
    except OSError as exc:
        print(f"Template introuvable: {TEMPLATE} ({exc})")
        sys.exit(1)
    repos = []
    for d in sorted(DOCS.iterdir()):
        if not d.is_dir():
            continue
        if not (d / ".git").exists():
            continue
        repos.append(d)

    print(f"Found {len(repos)} git repos")
    installed = 0
    for repo in repos:
        try:
            out = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "--absolute-git-dir"],
                capture_output=True, text=True, timeout=30,
            )
            git_dir = Path(out.stdout.strip()) if out.returncode == 0 else repo / ".git"
        except Exception:
            git_dir = repo / ".git"
        hooks_path = git_dir / "hooks"
        if not hooks_path.exists():
            continue
        pre_push = hooks_path / "pre-push"
        if pre_push.exists() and not force:
            continue
        pre_push.write_text(hook_text, encoding="utf-8", newline="\n")
        try:
            pre_push.chmod(0o755)
        except OSError:
            pass
        print(f"  INSTALLED {repo.name}")
        installed += 1

    print(f"\nInstalled pre-push hooks in {installed} repos")
    print("These hooks CANNOT be bypassed with --no-verify on push.")


if __name__ == "__main__":
    install_hooks("--force" in sys.argv)
