#!/usr/bin/env python3
"""inventory_versions.py — read-only fleet version audit (R91/R105).

For every project in projects.txt present under ~/Documents, report:
  - version source (package.json / pyproject static / VERSION file / none)
  - CHANGELOG.md presence
  - release workflow presence (.github/workflows/*release*)
  - git tag count (v*)

Usage:
  python scripts/inventory_versions.py [--docs DIR] [--csv PATH]
  python scripts/inventory_versions.py --markdown FLEET_VERSIONS.md

Read-only: never writes into scanned projects. Optional --csv writes one file.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

from kuro_paths import confine_arg

REPO = Path(__file__).resolve().parent.parent


def load_project_names(projects_file: Path) -> list[str]:
    names = []
    for raw in projects_file.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def static_pyproject_version(text: str) -> str:
    m = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return m.group(1) if m else ""


def git_tag_count(repo: Path) -> str:
    try:
        # cwd= au lieu de "-C <chemin>" : la valeur ne figure plus dans argv,
        # donc aucun injection d'argument possible (S6350/S8705).
        r = subprocess.run(["git", "tag", "--list", "v*"],
                           cwd=str(repo),
                           capture_output=True, text=True, timeout=30)
    except Exception:
        return "?"
    if r.returncode != 0:
        return "?"
    tags = [t for t in r.stdout.splitlines() if t.strip()]
    return str(len(tags))


def audit_one(docs: Path, name: str) -> dict:
    # name vient de projects.txt (fichier externe) : confine a docs avant
    # toute utilisation, y compris comme argument git (S6350/S8705) et comme
    # contenu du rapport (S2083). Nom hors docs -> repli sur le basename.
    d = confine_arg(name, docs, default=Path(name).name)
    row = {"project": d.name, "present": "no", "version": "-",
           "source": "-", "changelog": "-", "release_wf": "-", "vtags": "-"}
    if not d.is_dir():
        return row
    row["present"] = "yes"
    pj = d / "package.json"
    if pj.exists():
        try:
            v = json.loads(pj.read_text(encoding="utf-8", errors="replace")).get("version", "")
            if v:
                row["version"], row["source"] = str(v), "package.json"
        except Exception:
            pass
    if row["version"] == "-":
        pp = d / "pyproject.toml"
        if pp.exists():
            v = static_pyproject_version(pp.read_text(encoding="utf-8", errors="replace"))
            if v:
                row["version"], row["source"] = v, "pyproject"
    if row["version"] == "-" and (d / "VERSION").exists():
        first = (d / "VERSION").read_text(encoding="utf-8", errors="replace").strip().splitlines()
        if first:
            row["version"], row["source"] = first[0][:16], "VERSION"
    row["changelog"] = "yes" if (d / "CHANGELOG.md").exists() else "no"
    wf = d / ".github" / "workflows"
    row["release_wf"] = "yes" if wf.is_dir() and list(wf.glob("*release*")) else "no"
    row["vtags"] = git_tag_count(d) if (d / ".git").exists() else "nogit"
    return row


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fleet version inventory (read-only).")
    ap.add_argument("--docs", default=str(Path.home() / "Documents"))
    ap.add_argument("--csv", default="")
    ap.add_argument("--markdown", default="")
    args = ap.parse_args(argv)
    # --docs pointe vers ~/Documents (hors depot) : base = home.
    docs = confine_arg(args.docs, Path.home())
    rows = [audit_one(docs, n) for n in load_project_names(REPO / "projects.txt")]
    present = [r for r in rows if r["present"] == "yes"]
    nover = [r for r in present if r["version"] == "-"]
    nochlog = [r for r in present if r["changelog"] == "no"]
    norel = [r for r in present if r["release_wf"] == "no"]
    notags = [r for r in present if r["vtags"] == "0"]
    print(f"projects={len(rows)} present={len(present)} "
          f"no-version={len(nover)} no-changelog={len(nochlog)} "
          f"no-release-wf={len(norel)} zero-vtags={len(notags)}")
    print("project | version | source | changelog | release_wf | vtags")
    for r in rows:
        if r["present"] == "no":
            print(f"{r['project']} | ABSENT")
        elif r["version"] == "-" or r["changelog"] == "no" or r["release_wf"] == "no":
            print(f"{r['project']} | {r['version']} | {r['source']} | "
                  f"{r['changelog']} | {r['release_wf']} | {r['vtags']}")
    if args.csv:
        # Sorties confinées au depot (S8707) ; usage interne = chemins du repo.
        csv_path = confine_arg(args.csv, REPO)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {args.csv}")
    if args.markdown:
        import datetime
        today = datetime.date.today().isoformat()
        lines = [
            "# FLEET_VERSIONS.md — fleet version snapshot (generated, DO NOT EDIT)",
            f"# Generated by scripts/inventory_versions.py on {today}.",
            "# Spec: VERSIONING.md. Regenerate after each sync run.",
            "",
            f"Summary: {len(rows)} tracked, {len(present)} present, "
            f"{len(nover)} no version, {len(nochlog)} no CHANGELOG, "
            f"{len(norel)} no release workflow, {len(notags)} zero `v*` tags.",
            "",
            "| project | version | source | changelog | release_wf | vtags |",
            "|---|---|---|---|---|---|",
        ]
        for r in rows:
            if r["present"] == "no":
                lines.append(f"| {r['project']} | ABSENT | - | - | - | - |")
            else:
                lines.append(f"| {r['project']} | {r['version']} | {r['source']} | "
                             f"{r['changelog']} | {r['release_wf']} | {r['vtags']} |")
        lines.append("")
        md_path = confine_arg(args.markdown, REPO)
        md_path.write_text("\n".join(lines), encoding="utf-8", newline="\n")
        print(f"wrote {args.markdown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
