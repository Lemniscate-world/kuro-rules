#!/usr/bin/env python3
"""install_hooks.py — Install unbypassable git hooks across all projects.

Deploys kuro-rules/templates/git-hooks/* into .git/hooks/ of every repo
under ~/Documents (pre-push: tests/branch, commit-msg: conventional
commits for release-please). Git-level hooks run even with --no-verify.

Modes:
  (default)  install only where the hook is missing
  --upgrade  also replace hooks previously deployed by kuro (marker
             "Source de verite: kuro-rules/templates"), never touch
             foreign custom hooks
  --force    replace everything (use with care)

Usage: python scripts/install_hooks.py [--upgrade] [--force]
"""
import subprocess
import sys
from pathlib import Path

DOCS = Path.home() / "Documents"
TEMPLATES = DOCS / "kuro-rules" / "templates" / "git-hooks"
HOOKS = ("pre-push", "commit-msg")
MARKER = "Source de verite: kuro-rules/templates"


def load_template(name: str) -> str:
    ext = ".sh"
    return (TEMPLATES / f"{name}{ext}").read_text(encoding="utf-8").replace("\r\n", "\n")


def is_kuro_hook(path: Path) -> bool:
    try:
        return MARKER in path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False


def install_hooks(upgrade=False, force=False):
    try:
        texts = {name: load_template(name) for name in HOOKS}
    except OSError as exc:
        print(f"Template introuvable dans {TEMPLATES} ({exc})")
        sys.exit(1)
    repos = []
    for d in sorted(DOCS.iterdir()):
        if not d.is_dir():
            continue
        if not (d / ".git").exists():
            continue
        repos.append(d)

    print(f"Found {len(repos)} git repos")
    installed = {name: 0 for name in HOOKS}
    skipped_foreign = 0
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
        for name in HOOKS:
            target = hooks_path / name
            if target.exists() and not (force or (upgrade and is_kuro_hook(target))):
                if not is_kuro_hook(target):
                    skipped_foreign += 1
                continue
            target.write_text(texts[name], encoding="utf-8", newline="\n")
            try:
                target.chmod(0o755)
            except OSError:
                pass
            installed[name] += 1

    for name in HOOKS:
        print(f"Installed/updated {name}: {installed[name]} repos")
    print(f"Foreign custom hooks left untouched: {skipped_foreign}")
    print("Git-level hooks run on push/commit even with --no-verify.")


if __name__ == "__main__":
    install_hooks("--upgrade" in sys.argv, "--force" in sys.argv)
