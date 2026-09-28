#!/usr/bin/env python3
"""check_epingle_completeness.py — Epingle ne perd plus aucun projet (R85/R116).

Compare projects.txt + repos git locaux vs Epingle_Projets.md :
  ERROR : projet suivi (projects.txt) + remote OWNED verifie + absent d'Epingle
          -> regression classe "Forma" (25 commits invisibles). A corriger.
  WARN  : fork (-fork), org non-owned, sans remote non confirme, org inconnue
          -> decision humaine requise (R87), jamais bloquant.
  INFO  : ligne Epingle sans repo local (concept, ex: Aladin) — normal.

Parser unique via gen_x_posts.load_projects (inclut Laboratoire).
Registre ownership via gen_x_posts.classify_ownership (1 seul registre).

Zero dependance, cross-platform (R93). CI-safe : --warn-only -> exit 0.

Usage :
  python scripts/check_epingle_completeness.py [--strict] [--warn-only]
"""
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
EPINGLE = KURORULES / "Epingle_Projets.md"
PROJECTS_TXT = KURORULES / "projects.txt"

SKIP_DIRS = {"kuro-rules", "Lemniscate-world", "Vault", "WindowsPowerShell",
             "vcpkg", "MATLAB", ".git", "__pycache__"}

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from gen_x_posts import is_tracked
except Exception:
    def is_tracked(name, epingle_names):  # repli sans alias
        return (name or "").lower() in epingle_names


def read_projects_txt(path):
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except Exception:
        return []
    return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]


def check(projects, epingle_names, local_ownership):
    """Logique pure et testable. Retourne (errors, warns, infos)."""
    errors, warns, infos = [], [], []
    for name in projects:
        if is_tracked(name, epingle_names):
            continue
        own = local_ownership.get(name.lower(), "NO-LOCAL-REPO")
        if own == "NO-LOCAL-REPO":
            infos.append((name, "suivi-sans-clone-local"))
        elif "fork" in name.lower():
            warns.append((name, "fork — decider suivi Outil/exclusion (%s)" % own))
        elif own == "OWNED":
            errors.append((name, "OWNED verifie mais absent d'Epingle — ajouter (R85)"))
        else:
            warns.append((name, "ownership %s — confirmer avant ajout (R87)" % own))
    return errors, warns, infos


def check_org_registry(local_orgs, owned_markers, external_markers):
    """Orgs rencontrees non classees -> WARN (regression classe Quant-Search)."""
    warns = []
    for org, count in sorted(local_orgs.items(), key=lambda kv: -kv[1]):
        low = org.lower()
        known = any(m.lower().rstrip("/").endswith("/" + low) or low in m.lower()
                    for m in list(owned_markers) + list(external_markers))
        if not known:
            warns.append((org, "%d repo(s) — classer OWNED/EXTERNAL ou exclure" % count))
    return warns


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Epingle completeness gate (R85/R116)")
    ap.add_argument("--warn-only", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--docs", default=str(DOCS))
    ap.add_argument("--epingle", default=str(EPINGLE))
    ap.add_argument("--projects", default=str(PROJECTS_TXT))
    args = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import gen_x_posts as gx
    except Exception as exc:
        print("[ERR] import gen_x_posts impossible: %s" % exc)
        return 2

    try:
        projs = gx.load_projects(args.epingle)
    except RuntimeError as exc:
        print("[ERR] %s" % exc)
        return 2
    epingle_names = set(p["name"].lower() for p in projs)
    projects = read_projects_txt(args.projects)

    base = Path(args.docs)
    local_ownership, local_orgs = {}, {}
    if base.is_dir():
        for d in base.iterdir():
            if not d.is_dir() or d.name in SKIP_DIRS or not (d / ".git").is_dir():
                continue
            remotes = gx.run("git remote -v", cwd=d)
            own = gx.classify_ownership(remotes) if remotes else "UNKNOWN"
            local_ownership[d.name.lower()] = own
            if remotes:
                first = remotes.splitlines()[0]
                if "github.com/" in first:
                    org = first.split("github.com/")[1].split("/")[0]
                    local_orgs[org] = local_orgs.get(org, 0) + 1

    errors, warns, infos = check(projects, epingle_names, local_ownership)
    org_warns = check_org_registry(local_orgs, gx.OWNED_MARKERS, gx.EXTERNAL_MARKERS)

    print("=== epingle completeness ===")
    print("  Epingle: %d | projects.txt: %d | repos locaux: %d"
          % (len(epingle_names), len(projects), len(local_ownership)))
    for name, reason in errors:
        print("  [ERROR] %-24s %s" % (name, reason))
    for name, reason in warns + org_warns:
        print("  [WARN]  %-24s %s" % (name, reason))
    if args.strict:
        for name, reason in infos:
            print("  [INFO]  %-24s %s" % (name, reason))
    print("  -> %d ERROR, %d WARN" % (len(errors), len(warns) + len(org_warns)))
    if errors and not args.warn_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
