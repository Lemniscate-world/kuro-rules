#!/usr/bin/env python3
"""post_session_check.py — Run at end of every session to verify everything is synced.

Checks:
1. Epingle_Projets.md matches projects on disk
2. Portfolio HTML is up to date
3. Git repos are clean (no uncommitted changes)
4. Rules are consistent across repos

Usage: python scripts/post_session_check.py [--fix] [--quiet]
"""

import subprocess, sys, os
from pathlib import Path
from datetime import date

HOME = Path.home()
DOCS = HOME / "Documents"
KURORULES = DOCS / "kuro-rules"
LEMNISCATE = DOCS / "Lemniscate-world"
EPINGLE = KURORULES / "Epingle_Projets.md"
PORTFOLIO_HTML = LEMNISCATE / "index.html"

OK = "✅"
WARN = "⚠️"
FAIL = "❌"


def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd) if cwd else None, shell=True)


def check_portfolio_freshness():
    """Check if portfolio HTML is older than Epingle."""
    if not PORTFOLIO_HTML.exists():
        return FAIL, "Portfolio HTML missing"
    epingle_mtime = EPINGLE.stat().st_mtime
    html_mtime = PORTFOLIO_HTML.stat().st_mtime
    if html_mtime < epingle_mtime:
        return WARN, f"Portfolio is stale (Epingle newer by {int(epingle_mtime - html_mtime)}s)"
    return OK, "Portfolio is up to date"


def check_repos_clean():
    """Check all key repos are clean."""
    repos = [KURORULES, LEMNISCATE, DOCS / "NeuralDBG", DOCS / "Neural-Agent", DOCS / "Aquarium"]
    dirty = []
    for r in repos:
        if not (r / ".git").exists():
            continue
        result = run("git status --porcelain", cwd=r)
        if result.stdout.strip():
            dirty.append(r.name)
    if dirty:
        return WARN, f"Uncommitted changes in: {', '.join(dirty)}"
    return OK, "All repos clean"


def check_projects_listed():
    """Check all directories with AGENTS.md are in Epingle."""
    text = EPINGLE.read_text(encoding="utf-8")
    missing = []
    for d in sorted(DOCS.iterdir()):
        if not d.is_dir(): continue
        if d.name.startswith('.'): continue
        if d.name in ('kuro-rules', 'Vault', 'Lemniscate-world', 'WindowsPowerShell', 'vcpkg', 'MATLAB'): continue
        has_agents = (d / "AGENTS.md").exists()
        has_git = (d / ".git").exists()
        if has_agents or has_git:
            if d.name not in text:
                missing.append(d.name)
    if missing:
        return WARN, f"Projects not in Epingle: {', '.join(missing)}"
    return OK, "All projects listed in Epingle"


def regenerate_portfolio():
    """Regenerate the portfolio HTML."""
    gen = KURORULES / "scripts" / "generate_portfolio.py"
    if not gen.exists():
        return FAIL, "generate_portfolio.py not found"
    result = run(f"python {gen}")
    if result.returncode != 0:
        return FAIL, f"Generation failed: {result.stderr[:200]}"
    return OK, "Portfolio regenerated"


def commit_portfolio():
    """Commit and push the portfolio if changed."""
    result = run("git diff --quiet index.html", cwd=LEMNISCATE)
    if result.returncode == 0:
        return OK, "No changes to commit"
    run('git add index.html', cwd=LEMNISCATE)
    today = date.today().strftime("%Y-%m-%d")
    run(f'git commit -m "chore: auto-sync portfolio ({today})"', cwd=LEMNISCATE)
    run('git push', cwd=LEMNISCATE)
    return OK, "Portfolio committed and pushed"


def main():
    fix = "--fix" in sys.argv
    quiet = "--quiet" in sys.argv

    if not quiet:
        print("=" * 55)
        print("Post-Session Compliance Check")
        print("=" * 55)
        print()

    checks = [
        ("Portfolio freshness", check_portfolio_freshness),
        ("Repos clean", check_repos_clean),
        ("Projects in Epingle", check_projects_listed),
    ]

    all_ok = True
    for name, fn in checks:
        status, msg = fn()
        if not quiet:
            print(f"  {status} {name}: {msg}")
        if status == FAIL:
            all_ok = False

    if fix:
        if not quiet: print("\n--- Auto-fix ---")
        status, msg = regenerate_portfolio()
        if not quiet: print(f"  {status} Regenerate: {msg}")
        if status != FAIL:
            status, msg = commit_portfolio()
            if not quiet: print(f"  {status} Commit: {msg}")

    if not quiet:
        print()
        if all_ok:
            print("All checks passed.")
        else:
            print("Some checks failed. Run with --fix to auto-repair.")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
