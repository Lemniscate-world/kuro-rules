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
import os, re, subprocess, sys
from pathlib import Path

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
EPINGLE = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules"))) / "Epingle_Projets.md"

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
    # test files (py + ts/js, quick)
    test_files = list(cand.rglob("test*.py")) + list(cand.rglob("*_test.py"))
    test_files += list(cand.rglob("test*.ts")) + list(cand.rglob("*.test.ts")) + list(cand.rglob("*.spec.ts"))
    tfiles = len([p for p in test_files if "venv" not in str(p) and "node_modules" not in str(p) and ".git" not in str(p)][:200])
    return {"last_date": last_date, "c30": c30, "dirty": dirty, "tfuncs": 0, "loc": loc, "test_files": tfiles, "path": cand}


def compute_pct(status, cur_pct, facts):
    """Cible ABSOLUE depuis les faits, puis pas borne (converge, ne derive jamais).
    score = base(statut) + min(30, c30*3) + min(20, test_files*2) + recence + dirty
    Pas: +5/j max vers le haut, -10/j max vers le bas; |ecart|<3 -> stable."""
    s = status.lower()
    if "archive" in s:
        return 0
    if not facts:
        return cur_pct
    base = 25 if "actif" in s else 20 if "validation" in s else 10 if "proto" in s else 5
    c30 = facts.get("c30", 0) or 0
    tfiles = facts.get("test_files", 0) or 0
    score = base + min(30, c30 * 3) + min(20, tfiles * 2)
    from datetime import date
    try:
        last = facts.get("last_date", "")
        days = (date.today() - date.fromisoformat(last[:10])).days if last and len(last) >= 10 else 999
    except Exception:
        days = 999
    if days <= 7: score += 10
    elif days <= 30: score += 7
    elif days <= 60: score += 3
    elif days <= 90: score -= 5
    else: score -= 15
    if facts.get("dirty"):
        score -= 3
    target = max(0, min(95, score))
    step = target - cur_pct
    if abs(step) < 3:
        return cur_pct
    step = max(-10, min(5, step))
    new = cur_pct + step
    if "actif" in s and new < 10:
        new = 10
    return new

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
