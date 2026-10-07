#!/usr/bin/env python3
"""scaffold_idea.py — Discord/Epingle -> dossier + README + git + projects.txt (R85/R87/R101/R93).

Boucle bidirectionnelle idempotente :
  Sens 1 (idée -> code) : --project Sybil --section "lambda-Section-13 — Dexter.pwn" --desc "..." --status Recherche --pct 0
    -> crée ~/Documents/<Projet>/ (README, SESSION_SUMMARY, decision-memo privé, .gitignore R101, git init)
    -> ajoute à projects.txt si absent
    -> vérifie Epingle (ajoute ligne 0% Recherche si absente, jamais écrase)
  Sens 2 (Epingle -> Discord) : --plan-discord
    -> affiche salon idée à créer (idea-<slug> pour Recherche/Prototypage, proj-<slug> pour Actif/Validation)
    -> réutilise kuro_discord.py pour le sync réel

Idempotent : relancer 2x ne crée ni doublon ni écrasement.
Zero dépendance, cross-platform (R93). Secrets jamais loggés.

Usage :
  python scripts/scaffold_idea.py --project Sybil --section "lambda-Section-13 — Dexter.pwn" --desc "Exploration des failles de réseaux de neurones." --status Recherche --pct 0
  python scripts/scaffold_idea.py --project Sybil --dry-run
  python scripts/scaffold_idea.py --plan-discord --project Sybil
"""
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
EPINGLE = KURORULES / "Epingle_Projets.md"
PROJECTS_TXT = KURORULES / "projects.txt"

GITIGNORE_BODY = """# R101 — fichiers privés jamais commités
SESSION_SUMMARY.md
decision-memo.md
LAUNCH_POSTS.md
docs/launch_plan_*.md
docs/hn_feedback_log.md
docs/community_post_template.md
docs/launch_postmortem.md
__pycache__/
 benchmarks tmp
.env
*.local.json
"""

README_TPL = """# {name}

> Section : {section}
> Statut : {pct}% {status} — {date}
> Source : idée tapée (Discord/Epingle) — scaffold auto `scripts/scaffold_idea.py`

{desc}

## État
- [ ] Mom Test (R2) — 5 interviews problème
- [ ] Desk research (R75) — evidence-matrix
- [ ] Decision-memo L0/L1 — voir `decision-memo.md` (privé, non commité)

## Boucle Discord <-> Code
- Salon idée : `#idea-{slug}` (Recherche/Prototypage) puis `#proj-{slug}` au passage Actif
- Epingle : ligne `{name}` en table `Epingle_Projets.md` (R80, anti-duplicat, UTF-8)
- Portfolio : `python scripts/generate_portfolio.py` après update Epingle

## Prochaine étape
Collecter 5 signaux problème avant tout code (R115 gate L1).
"""

SESSION_TPL = """# SESSION_SUMMARY — {name}

## Français
### Résumé Compact (R79, 150 mots max)
Scaffold initial depuis idée tapée. Problème à valider : {desc} Prochaine étape : Mom Test.

## English
### Compact Summary (R79, 150 words max)
Initial scaffold from typed idea. Problem to validate. Next: Mom Test interviews.

## Investor summary (R83, Discord-ready, 3-5 phrases)
{name} scaffold: idea registered, 0% Recherche. Next: collect 5 problem signals within 14 days. Gate: GO/ADJUST/NO-GO.
"""

DECISION_TPL = """# Decision memo (PRIVÉ — ne jamais committer, R101)

Date: {date}
Project: {name}
Status: discovery (L0)

## Current decision
- Verdict: pending Mom Test
- Section: {section}
- Idea source: Discord/Epingle typed idea

## Locked product definition
- Wedge: {desc}
- In scope: validation problème uniquement
- Out of scope: code solution avant L1

## Validation ladder
1. L0 - problem hypothesis (ce fichier)
2. L1 - desk evidence
3. L2 - expert confirmation
4. L3 - pilot-ready offer
5. L4 - willingness-to-pay proof

## Next actions
1. 5 interviews Mom Test
2. research/evidence-matrix.csv
3. GO/NO-GO L1
"""


def slug(name):
    import unicodedata
    t = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "divers"


def in_epingle(name, text):
    pat = re.compile(r"^\|\s*(\*\*)?" + re.escape(name) + r"(\*\*)?\s*\|", re.MULTILINE | re.IGNORECASE)
    return bool(pat.search(text))


def run(cmd, cwd):
    try:
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=30)
        return r.returncode, (r.stdout or "" + r.stderr or "")[:300]
    except Exception as exc:
        return 1, str(exc)[:200]


def scaffold(project, section, desc, status="Recherche", pct=0, dry=False):
    target = DOCS / project
    sl = slug(project)
    actions = []
    if target.exists():
        actions.append(f"garde dossier existant {target} (jamais écrasé)")
    elif dry:
        actions.append(f"[DRY] créer {target}/")
    else:
        target.mkdir(parents=True, exist_ok=True)
        (target / "README.md").write_text(README_TPL.format(name=project, section=section, desc=desc, status=status, pct=pct, date=date.today().isoformat(), slug=sl), encoding="utf-8")
        (target / "SESSION_SUMMARY.md").write_text(SESSION_TPL.format(name=project, desc=desc), encoding="utf-8")
        (target / "decision-memo.md").write_text(DECISION_TPL.format(name=project, section=section, desc=desc, date=date.today().isoformat()), encoding="utf-8")
        (target / ".gitignore").write_text(GITIGNORE_BODY, encoding="utf-8")
        code, _ = run(["git", "init"], target)
        actions.append(f"crée {target}/ + README + SESSION_SUMMARY + decision-memo (privé) + .gitignore R101 + git init ({code})")
        # hook pre-commit R101 minimal
        hooks = target / ".githooks" / "pre-commit"
        hooks.parent.mkdir(exist_ok=True)
        hooks.write_text("#!/bin/sh\n# R101 guard\ngit diff --cached --name-only | grep -qE '^(SESSION_SUMMARY.md|decision-memo.md)$' && echo '[R101] fichier prive bloque' && exit 1\nexit 0\n", encoding="utf-8")
    # projects.txt
    try:
        lines = PROJECTS_TXT.read_text(encoding="utf-8").splitlines()
    except Exception:
        lines = []
    names = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    if project in names:
        actions.append("projects.txt déjà présent")
    elif dry:
        actions.append("[DRY] ajouter à projects.txt")
    else:
        with PROJECTS_TXT.open("a", encoding="utf-8") as f:
            f.write(f"{project}\n")
        actions.append("ajouté à projects.txt")
    # Epingle check (jamais écrase, propose seulement)
    try:
        ep = EPINGLE.read_text(encoding="utf-8")
        if in_epingle(project, ep):
            actions.append("Epingle déjà présent (anti-duplicat OK)")
        elif dry:
            actions.append("[DRY] ajouter ligne Epingle 0% Recherche")
        else:
            actions.append(f"ABSENT Epingle -> à ajouter manuellement en table {section} : | **{project}** | {pct}% | {status} | {desc} | (R80 format)")
    except Exception as exc:
        actions.append(f"Epingle illisible: {exc}")
    # Discord sens 2
    kind = "proj" if status.lower() in ("actif", "validation") else "idea"
    actions.append(f"Discord: créer #{kind}-{sl} dans catégorie {section} + poster R83, puis `kuro_discord.py sync --apply` pour Actifs")
    return actions


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Scaffold idée -> dossier/git/Epingle/Discord (idempotent)")
    ap.add_argument("--project", required=True)
    ap.add_argument("--section", default="")
    ap.add_argument("--desc", default="Idée à valider.")
    ap.add_argument("--status", default="Recherche")
    ap.add_argument("--pct", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--plan-discord", action="store_true")
    args = ap.parse_args(argv)
    if args.plan_discord:
        sl = slug(args.project)
        kind = "proj" if args.status.lower() in ("actif", "validation") else "idea"
        print(f"Discord: #{kind}-{sl} <- {args.project} [{args.status}] ({args.section or 'section à confirmer'})")
        print("  Recherche/Prototypage -> salon idea- (visibilité sans spam webhook)")
        print("  Actif/Validation -> salon proj- + webhook Kuro + topic '%d%% %s' " % (args.pct, args.status))
        return 0
    for a in scaffold(args.project, args.section or "section à confirmer", args.desc, args.status, args.pct, args.dry_run):
        print(f"  - {a}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
