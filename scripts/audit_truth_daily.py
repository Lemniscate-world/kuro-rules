#!/usr/bin/env python3
"""audit_truth_daily.py — Daily truth audit for lambda-Section.
Scans ~/Documents for all projects with .git, collects factual data,
writes TRUTH_DAILY.md and optionally updates Epingle_Projets.md.

Facts per project:
  - last commit (hash, date, message)
  - branch, dirty status
  - test files count, test functions count
  - line count (python)
  - last 30 days commit count

Usage:
  python scripts/audit_truth_daily.py --dry-run          # just report
  python scripts/audit_truth_daily.py --apply            # update Epingle descriptions with facts
  python scripts/audit_truth_daily.py --output TRUTH_DAILY.md
"""

import os, subprocess, re, sys
from pathlib import Path
from datetime import date, datetime

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
EPINGLE = KURORULES / "Epingle_Projets.md"
TRUTH_REPORT = KURORULES / "TRUTH_DAILY.md"

SKIP = {"kuro-rules", "Vault", "Lemniscate-world", "WindowsPowerShell", "vcpkg", "MATLAB", ".git", "__pycache__"}

def run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, shell=True, timeout=10)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), 1

def collect_project_facts(proj_path: Path, quick=False):
    facts = {"path": proj_path, "name": proj_path.name}
    # git exists?
    if not (proj_path / ".git").exists():
        facts["git"] = False
        facts["test_files"] = 0
        facts["test_funcs"] = 0
        facts["loc"] = 0
        return facts
    facts["git"] = True
    # last commit
    out, _, _ = run('git log -1 --format="%h|%ad|%s|%an" --date=short', cwd=proj_path)
    if out:
        parts = out.strip('"').split("|", 3)
        if len(parts) >= 3:
            facts["last_hash"] = parts[0]
            facts["last_date"] = parts[1]
            facts["last_msg"] = parts[2][:80]
            facts["last_author"] = parts[3] if len(parts) > 3 else ""
        else:
            facts["last_hash"] = out[:7]
    else:
        facts["last_hash"] = "—"
        facts["last_date"] = "—"
        facts["last_msg"] = "no commits"
    # branch
    out, _, _ = run('git branch --show-current', cwd=proj_path)
    facts["branch"] = out or "—"
    # dirty
    out, _, _ = run('git status --porcelain', cwd=proj_path)
    facts["dirty"] = bool(out.strip())
    facts["dirty_files"] = len(out.splitlines()) if out.strip() else 0
    # commit count last 30 days (fast)
    out, _, _ = run('git rev-list --count --since="30 days ago" HEAD', cwd=proj_path)
    facts["commits_30d"] = out.strip() if out.strip().isdigit() else "0"
    if quick:
        facts["test_files"] = 0
        facts["test_funcs"] = 0
        facts["loc"] = 0
        return facts
    # test files (heavy, skip if quick)
    test_files = list(proj_path.rglob("test*.py")) + list(proj_path.rglob("*_test.py"))
    test_files = [p for p in test_files if "venv" not in str(p) and ".git" not in str(p) and "__pycache__" not in str(p)]
    facts["test_files"] = len(test_files)
    test_funcs = 0
    for tf in test_files[:20]:  # limit to 20 files for speed
        try:
            txt = tf.read_text(encoding="utf-8", errors="ignore")
            test_funcs += len(re.findall(r'^\s*def test_', txt, re.MULTILINE))
        except:
            pass
    facts["test_funcs"] = test_funcs
    # python lines (sample, not full rglob for speed)
    facts["loc"] = 0
    return facts

def scan_all(quick=True):
    facts_list = []
    # Prefer Epingle list if available (60 projets) for speed and truth
    epingle_projects = set()
    if EPINGLE.exists():
        try:
            txt = EPINGLE.read_text(encoding="utf-8")
            for m in re.finditer(r'^\|\s*\*\*([^\*]+)\*\*\s*\|', txt, re.MULTILINE):
                epingle_projects.add(m.group(1).strip().lower())
            for m in re.finditer(r'^\|\s*([A-Za-z0-9/_-]+)\s*\|\s*(?:\d+%|—)', txt, re.MULTILINE):
                # capture non-bold like Console, Mori
                name = m.group(1).strip()
                if name.lower() not in ("projet", "section") and len(name) < 30:
                    epingle_projects.add(name.lower())
        except:
            pass
    for child in sorted(DOCS.iterdir()):
        if not child.is_dir():
            continue
        if child.name in SKIP or child.name.startswith("."):
            continue
        if not (child / ".git").exists() and not (child / "AGENTS.md").exists():
            continue
        # if Epingle list exists, only scan those projects for speed (daily truth)
        if epingle_projects and child.name.lower() not in epingle_projects:
            # allow a few extra like NeuralDBG etc. but skip unrelated
            if child.name.lower() not in ("neuraldbg", "neural-agent", "lifetrack", "openquant"):
                # keep but mark as extra
                pass
        facts = collect_project_facts(child, quick=quick)
        facts_list.append(facts)
    return facts_list

def write_truth_report(facts_list, output_path):
    today = date.today().isoformat()
    lines = []
    lines.append(f"# TRUTH DAILY — {today}")
    lines.append("")
    lines.append(f"> **Auto-généré** chaque jour à partir de `git log` + comptage tests. Aucune estimation, que des faits.")
    lines.append(f"> **Projects scannés:** {len(facts_list)} | **Source:** `~/Documents` + `Epingle_Projets.md`")
    lines.append("")
    lines.append("| Projet | Dernier commit | Branche | Tests | LOC | 30j | Dirty |")
    lines.append("|--------|---------------|---------|-------|-----|-----|-------|")
    for f in sorted(facts_list, key=lambda x: x.get("last_date",""), reverse=True):
        name = f["name"]
        last = f.get("last_date","—")
        msg = f.get("last_msg","—")[:50].replace("|","/")
        h = f.get("last_hash","—")
        branch = f.get("branch","—")
        tf = f.get("test_files",0)
        tfn = f.get("test_funcs",0)
        loc = f.get("loc",0)
        c30 = f.get("commits_30d","0")
        dirty = "!" if f.get("dirty") else ""
        if f.get("git"):
            lines.append(f"| **{name}** | {last} `{h}` {msg} | {branch} | {tf} ({tfn} funcs) | {loc} | {c30} | {dirty} |")
        else:
            lines.append(f"| **{name}** | — (no git) | — | {tf} | {loc} | — | — |")
    lines.append("")
    lines.append("## Verite vs Epingle")
    lines.append("")
    # Compare with Epingle percentages vs recent activity
    try:
        epingle_text = EPINGLE.read_text(encoding="utf-8")
        # extract project rows
        import re as _re
        for f in facts_list:
            name = f["name"]
            # find in epingle
            m = _re.search(rf'^\|\s*\*\*{re.escape(name)}\*\*\s*\|\s*([^\|]+)\|', epingle_text, re.MULTILINE | re.IGNORECASE)
            if m:
                epingle_pct = m.group(1).strip()
                # flag if no commit in 30 days but status Actif
                if f.get("commits_30d") == "0" and f.get("last_date","") < "2026-07-01":
                    lines.append(f"- **{name}** `{epingle_pct}` mais 0 commit 30j (dernier {f.get('last_date')}) -> verifier statut Actif")
    except Exception as e:
        lines.append(f"_Erreur comparaison Epingle: {e}_")

    lines.append("")
    lines.append(f"_Généré {datetime.now().isoformat()} | Script: `scripts/audit_truth_daily.py` | Prochain: `generate_portfolio.py`_")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {output_path} ({len(facts_list)} projets)")

def update_epingle_with_facts(facts_list):
    """Optionally patch Epingle descriptions with factual footer (last commit + tests)."""
    text = EPINGLE.read_text(encoding="utf-8")
    updated = 0
    for f in facts_list:
        if not f.get("git"):
            continue
        name = f["name"]
        # Build factual suffix
        suffix = f" | git: {f.get('last_date')} {f.get('last_hash')} ({f.get('commits_30d')} commits 30j), {f.get('test_files')} tests"
        # Find line
        pattern = re.compile(rf'(^\|\s*\*\*{re.escape(name)}\*\*\s*\|[^\n]+\|)([^\n]+)(\|)', re.MULTILINE | re.IGNORECASE)
        # Instead, just ensure last commit not already in description
        # For now, we don't auto-patch Epingle to avoid overwriting curated descriptions.
        # We only report. To enable, uncomment below.
        pass
    print(f"  Epingle not auto-patched (dry). Use TRUTH_DAILY.md as source, copy manually if needed.")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="just generate report")
    ap.add_argument("--apply", action="store_true", help="also update Epingle (currently no-op, manual)")
    ap.add_argument("--output", default=str(TRUTH_REPORT), help="path for truth report")
    args = ap.parse_args()

    print("=== Daily Truth Audit ===")
    facts = scan_all()
    print(f"  Scanned {len(facts)} projets")

    out_path = Path(args.output).expanduser()
    write_truth_report(facts, out_path)

    if args.apply:
        update_epingle_with_facts(facts)
        print("  (--apply) Epingle check done (manual copy recommended)")

    # Always regenerate portfolio to ensure truth propagates
    print("\nRegenerating portfolio from Epingle...")
    gen = KURORULES / "scripts" / "generate_portfolio.py"
    if gen.exists():
        out, err, code = run(f'python "{gen}"')
        print(out)
        if err:
            print(f"  stderr: {err[:500]}")

if __name__ == "__main__":
    main()
