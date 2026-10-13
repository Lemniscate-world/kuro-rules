#!/usr/bin/env python3
"""inventory_versions.py — read-only fleet version audit (R91/R105).

For every project in projects.txt present under ~/Documents, report:
  - version source (package.json / pyproject static / VERSION file / none)
  - CHANGELOG.md presence
  - release workflow presence (.github/workflows/*release*)
  - git tag count (v*)

Usage:
  python scripts/inventory_versions.py [--docs DIR] [--csv PATH]

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
        r = subprocess.run(["git", "-C", str(repo), "tag", "--list", "v*"],
                           capture_output=True, text=True, timeout=30)
    except Exception:
        return "?"
    if r.returncode != 0:
        return "?"
    tags = [t for t in r.stdout.splitlines() if t.strip()]
    return str(len(tags))


def audit_one(docs: Path, name: str) -> dict:
    d = docs / name
    row = {"project": name, "present": "no", "version": "-",
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
    args = ap.parse_args(argv)
    docs = Path(args.docs)
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
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
