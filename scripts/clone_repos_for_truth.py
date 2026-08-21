#!/usr/bin/env python3
"""clone_repos_for_truth.py — Clone les repos publics dans ~/Documents pour la vérité sur CI.

Sur GitHub Actions, ~/Documents est vide: audit_truth_daily / compute_progress /
truth_enrich / generate_blog dépendent de repos locaux. Ce script clone en shallow
les repos listés dans Epingle depuis LambdaSection et Lemniscate-world.

Usage (CI): python clone_repos_for_truth.py --token "$TOKEN"
Ignorer silencieusement les repos privés/inexistants.
"""
import re, subprocess, sys
from pathlib import Path

HOME = Path.home()
DOCS = HOME / "Documents"
EPINGLE = Path(__file__).resolve().parent.parent / "Epingle_Projets.md"

ORGS = ["LambdaSection", "Lemniscate-world"]

def epingle_names():
    text = EPINGLE.read_text(encoding="utf-8")
    names = set()
    for m in re.finditer(r'^\|\s*\*\*([^\*]+)\*\*\s*\|', text, re.MULTILINE):
        n = m.group(1).strip()
        if n and not n.startswith("-") and "?-" not in n:
            names.add(n)
    return sorted(names)

def main():
    token = ""
    if "--token" in sys.argv:
        token = sys.argv[sys.argv.index("--token") + 1]
    DOCS.mkdir(parents=True, exist_ok=True)
    ok, fail = 0, 0
    for name in epingle_names():
        dest = DOCS / name
        if (dest / ".git").exists():
            ok += 1
            continue
        cloned = False
        for org in ORGS:
            url = f"https://x-access-token:{token}@github.com/{org}/{name}.git" if token else f"https://github.com/{org}/{name}.git"
            r = subprocess.run(
                ["git", "clone", "--depth", "50", "--quiet", url, str(dest)],
                capture_output=True, text=True, timeout=120,
            )
            if r.returncode == 0:
                cloned = True
                break
        if cloned:
            ok += 1
            print(f"  + {name}")
        else:
            fail += 1
    print(f"Clones OK: {ok} | indisponibles (prive/404): {fail}")

if __name__ == "__main__":
    main()
