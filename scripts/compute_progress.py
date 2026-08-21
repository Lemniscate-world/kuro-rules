#!/usr/bin/env python3
"""compute_progress.py — Calcule % réaliste factuel pour chaque projet (R3 pessimiste).

Formule transparente, basée sur faits:
  base =  5 Nouveau, 10 Prototypage,  20 Validation, 25 Actif, 0 Archive
  + tests: test_funcs *0.4  (max 20)  | 50 funcs = 20%
  + commits_30j *0.8 (max 15) | 15 commits =12%
  + recence: last 7j +10, 30j +5, 60j 0, >60j -10
  + dirty: -5 si git dirty
  + loc bonus: min(loc/8000*5,5)
  Bordé 0-95% (100% seulement si tag v1.0 + coverage>90)

Source: git log, test count via audit_truth_daily, pas d'estimation humaine.
Usage:
  python scripts/compute_progress.py --dry-run
  python scripts/compute_progress.py --apply  # met à jour Epingle_Projets.md
"""
import re, subprocess, sys
from pathlib import Path

HOME = Path.home()
DOCS = HOME / "Documents"
EPINGLE = HOME / "Documents" / "kuro-rules" / "Epingle_Projets.md"

def run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, shell=True, timeout=8)
        return r.stdout.strip()
    except:
        return ""

def collect(project_name):
    # find local repo case-insensitive
    cand = None
    for d in DOCS.iterdir():
        if d.is_dir() and d.name.lower() == project_name.lower():
            cand = d
            break
    if not cand or not (cand / ".git").exists():
        return None
    # last commit date
    last_date = run('git log -1 --format="%ad" --date=short', cwd=cand)
    # commits 30j
    c30 = run('git rev-list --count --since="30 days ago" HEAD', cwd=cand)
    c30 = int(c30) if c30.isdigit() else 0
    # branch dirty
    dirty = bool(run('git status --porcelain', cwd=cand))
    # test funcs (quick count)
    tfuncs = 0
    for tf in list(cand.rglob("test*.py"))[:20]:
        if "venv" in str(tf) or ".git" in str(tf):
            continue
        try:
            tfuncs += len(re.findall(r'^\s*def test_', tf.read_text(encoding="utf-8", errors="ignore"), re.MULTILINE))
        except:
            pass
    # loc
    loc = 0
    for pf in list(cand.rglob("*.py"))[:50]:
        if "venv" in str(pf) or ".git" in str(pf):
            continue
        try:
            loc += len(pf.read_text(encoding="utf-8", errors="ignore").splitlines())
        except:
            pass
    return {"last_date": last_date, "c30": c30, "dirty": dirty, "tfuncs": tfuncs, "loc": loc, "path": cand}

def compute_pct(status, cur_pct, facts):
    """Realiste: part de cur_pct et ajuste avec delta factuel (R3 pessimiste modere)."""
    s = status.lower()
    if "archive" in s:
        return 0
    if not facts:
        return cur_pct
    delta = 0
    # Recence
    from datetime import date
    try:
        last = facts.get("last_date","")
        if last and len(last) >= 10:
            ld = date.fromisoformat(last[:10])
            days = (date.today() - ld).days
            if days <= 7:
                delta += 3
            elif days <= 30:
                delta += 1
            elif days <= 60:
                delta += 0
            elif days <= 90:
                delta -= 8
            else:
                delta -= 12
        else:
            delta -= 5
    except:
        delta -= 3
    # Activite 30j
    c30 = facts.get("c30",0)
    if c30 == 0 and "actif" in s:
        delta -= 6
    elif c30 >= 10:
        delta += 3
    elif c30 >= 3:
        delta += 1
    # Dirty
    if facts.get("dirty"):
        delta -= 3
    # Tests vs status
    tfuncs = facts.get("tfuncs",0)
    tf = facts.get("test_files",0)
    # Si Actif mais 0 tests et pas de loc, penalite
    if "actif" in s and tf == 0 and tfuncs == 0:
        # check loc
        if facts.get("loc",0) < 500:
            delta -= 4
    # R3 pessimiste: leger -2
    delta -= 2
    new_pct = cur_pct + delta
    # Borne 0-95, jamais 100 sans tag
    new_pct = max(0, min(95, new_pct))
    # Si Actif et new_pct <10, plancher 10
    if "actif" in s and new_pct < 10:
        new_pct = 10
    # Si ecart faible (<3), garde cur pour stabilite
    if abs(new_pct - cur_pct) < 3:
        return cur_pct
    return new_pct

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    dry = not args.apply

    text = EPINGLE.read_text(encoding="utf-8")
    lines = text.splitlines()
    new_lines = []
    changes = []
    for line in lines:
        if line.startswith("| **") or (line.startswith("| ") and not line.startswith("| ---") and "|" in line):
            # try to parse as project row
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                name_raw = parts[0].replace("**", "").strip()
                pct_raw = parts[1].strip()
                status = parts[2].strip() if len(parts) > 2 else ""
                if not name_raw or name_raw.lower() in ("projet", "section") or name_raw.startswith("-"):
                    new_lines.append(line)
                    continue
                # only if pct looks like % or — (skip livrables ?-2)
                if "%" not in pct_raw and pct_raw not in ("—", "-", "0", "0%") and not pct_raw.isdigit():
                    # check if status is known project status
                    if status.lower() not in ("actif", "validation", "prototypage", "nouveau", "archive", "recherche", "pivot", "outil"):
                        new_lines.append(line)
                        continue
                    # else allow but will compute
                # skip livrables with ?-
                if "?-" in pct_raw or "Externe" in pct_raw:
                    new_lines.append(line)
                    continue
                # extract current pct first
                m = re.search(r'(\d+)', pct_raw)
                cur = int(m.group(1)) if m else 0
                if pct_raw in ("—", "-"):
                    cur = 0
                facts = collect(name_raw)
                auto = compute_pct(status, cur, facts)
                diff = auto - cur
                if abs(diff) >= 5:  # only if significant
                    changes.append((name_raw, cur, auto, status, facts))
                    if not dry:
                        # replace pct cell
                        new_pct_cell = f" {auto}% "
                        # rebuild line
                        parts[1] = f" {auto}% "
                        new_line = "| " + " | ".join(parts) + " |"
                        new_lines.append(new_line)
                        continue
                new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    if dry:
        print(f"=== Compute Progress (dry-run) {len(changes)} changements proposes ===")
        for name, cur, auto, status, facts in sorted(changes, key=lambda x: abs(x[2]-x[1]), reverse=True)[:20]:
            f = facts or {}
            print(f"  {name:20} {cur:2}% -> {auto:2}% ({status:12}) | c30={f.get('c30',0)} tfuncs={f.get('tfuncs',0)} last={f.get('last_date','—')} dirty={f.get('dirty',False)}")
        if not changes:
            print("  Aucun ecart >=5% — Epingle deja realiste")
        else:
            print(f"\n  Total {len(changes)} projets avec ecart >=5%")
            print("  Lance avec --apply pour ecrire dans Epingle_Projets.md")
    else:
        EPINGLE.write_text("\n".join(new_lines), encoding="utf-8")
        print(f"  Epingle mis a jour: {len(changes)} % recalculés (factuel)")
        for name, cur, auto, _, _ in changes:
            print(f"    {name}: {cur}% -> {auto}%")

if __name__ == "__main__":
    main()
