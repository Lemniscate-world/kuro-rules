#!/usr/bin/env python3
"""auto_place.py — Routeur auto : sait où tout mettre, dans les deux sens (R80/R85/R87/R101/R105/R93).

Placements (idempotent, jamais destructif) :
  LABO      : recherche pure (Hypatia Recherche 0-5%, formalisation/preuve/théorie, sans produit)
              -> Horcruxe Labs/recherches/NNN-slug/ + RESEARCH_MAP + Epingle Hypatia (thématique, anti-duplicat)
  PROD      : produit/hacking appliqué Actif/Validation, ou Recherche Dexter.pwn forcée (ex: Sybil)
              -> ~/Documents/<Projet>/ + projects.txt + Epingle section thématique
  EPINGLE_ONLY : idée 0% Prototypage/Recherche non pure, sans code attendu (ex: Bad Bunny, Mori, Charles)
              -> Epingle seule, aucun dossier (évite 15 repos vides)
  EXTERNE   : Demeter/Demeter-Financial-Labs, Constant_Yield, DevDemeterDAO, XP_Farming, Nwt
              -> Epingle Externes uniquement, jamais de dossier local OWNED
  ARCHIVE   : status Archive -> aucune action (ne jamais ressusciter)
  ALIAS     : kuro -> KuroGuardian, etc. -> mappe, ne duplique jamais

Sens 1 (idée -> place) :
  python scripts/auto_place.py --project Sybil --section "lambda-Section-13 — Dexter.pwn" --desc "..." --status Recherche --pct 0 [--force] [--dry-run]
  python scripts/auto_place.py --from-epingle [--force] [--dry-run]   # route tous les Epingle sans dossier
  python scripts/auto_place.py --from-discord-export exports/ [--dry-run]  # route salons/messages Discord (réutilise mapping sync_discord_to_epingle)

Sens 2 (place -> Discord) :
  python scripts/auto_place.py --plan-discord [--project Sybil]
  Recherche/Prototypage -> #idea-<slug> (visibilité sans spam webhook)
  Actif/Validation      -> #proj-<slug> + webhook Kuro (via kuro_discord.py sync --apply)
  Recherches labo 002/003 -> PAS de salon par recherche (restent dans hub #proj-horcruxe-labs, R105 monorepo)

Zero dépendance, cross-platform (R93). Secrets jamais loggés. R101 : decision-memo/SESSION_SUMMARY jamais commités.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
EPINGLE = KURORULES / "Epingle_Projets.md"
PROJECTS_TXT = KURORULES / "projects.txt"
LABO = DOCS / "Horcruxe Labs"
RECHERCHES = LABO / "recherches"
RESEARCH_MAP = LABO / "RESEARCH_MAP.md"

ALIAS = {
    "kuro": "KuroGuardian",
    "datalint": "DataLint",
}

# Epingle EN -> dossier labo FR (ne pas recréer 004-doublon)
LABO_SLUG_ALIAS = {
    "logical-calculus": "calcul-logique",
    "math-theorization-of-linguistics": "linguistique-mathematique",
    "math-theorization-of-linguistic": "linguistique-mathematique",
}

# Actif sans code attendu -> reste Epingle seule (pas de repo vide)
EPINGLE_ONLY_MARKERS = ("mindmapping", "phase de mindmapping", "périmètre à définir")

EXTERNE_MARKERS = ("demeter", "constant_yield", "devdemeterdao", "xp_farming", "nwt", "demeter-financial-labs")

PURE_KEYWORDS = (
    "calcul infinit", "formalisation", "formalization", "preuve", "theorem",
    "minkowski", "non-hermitien", "non hermitien", "shannon", "probabilit",
    "logique et le calcul de newton", "mathématisation", "mathematisation",
    "théorie de shannon", "espaces de probabilit", "système de calcul",
)

PRODUCT_BLOCKLIST_FOR_LABO = (
    "trading", "saas", "landing", "ide", "tracker", "app mobile", "callisthénie",
    "musique", "beatmaking", "fintech", "assurance", "blockchain", "tranche",
)

LABO_SECTIONS = ("hypatia", "laboratoire", "horcruxe")


def slug(name):
    t = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "divers"


def classify(project, section, desc, status, pct):
    """Logique pure et testable. Retourne (placement, raison)."""
    name = (project or "").strip()
    low_name = name.lower()
    low_sec = (section or "").lower()
    low_desc = (desc or "").lower()
    low_status = (status or "").lower()

    if not name:
        return ("REJECT", "nom vide")
    # Alias dossier existant (jamais de doublon) : kuro/ == KuroGuardian
    if low_name in ALIAS:
        return ("ALIAS", f"dossier existant {ALIAS[low_name]} (ex: kuro/ == KuroGuardian) : mapper sans créer")
    if low_name == "kuroguardian":
        return ("ALIAS", "dossier existant kuro/ == KuroGuardian : mapper sans créer (pas de 2e repo)")
    if low_status == "archive":
        return ("ARCHIVE", "status Archive : ne jamais ressusciter")
    # Externe : jamais de dossier local OWNED
    blob = f"{low_name} {low_sec} {low_desc}"
    if any(m in blob for m in EXTERNE_MARKERS) or "externes (demeter" in low_sec or "tiers" in low_sec:
        return ("EXTERNE", "écosystème Demeter/Tiers : Epingle Externes uniquement (R87/R105)")
    # Actif sans code (mindmapping, périmètre à définir) -> Epingle seule
    if low_status in ("actif", "validation") and any(m in low_desc for m in EPINGLE_ONLY_MARKERS) and (pct or 0) <= 6:
        return ("EPINGLE_ONLY", "Actif mindmapping/scaffold vide : Epingle seule, dossier à la demande")
    # Labo : recherche pure Hypatia/Laboratoire, sans produit, pct petit
    is_labo_section = any(s in low_sec for s in LABO_SECTIONS)
    has_pure = any(k in low_desc for k in PURE_KEYWORDS)
    has_product = any(k in low_desc for k in PRODUCT_BLOCKLIST_FOR_LABO)
    if low_status in ("recherche",) and (is_labo_section or has_pure) and not has_product and (pct or 0) <= 5:
        return ("LABO", "recherche pure publiable, isolée du code prod (Epingle Laboratoire, R105 hub)")
    # Prod : Actif/Validation toujours ; Dexter.pwn hacking appliqué même en Recherche (avec force ou par défaut Sybil-like)
    if low_status in ("actif", "validation"):
        return ("PROD", f"statut {status} : produit vivant -> repo standalone")
    if "dexter" in low_sec or "pwn" in low_sec or "ctf" in low_desc or "zero day" in low_desc or "failles de r" in low_desc:
        return ("PROD", "hacking appliqué Dexter.pwn : repo standalone, pas labo maths")
    # Reste : idées 0% sans code attendu
    if low_status in ("recherche", "prototypage", "outil", "pivot", "en pause") and (pct or 0) <= 5:
        return ("EPINGLE_ONLY", "idée 0-5% sans code attendu : Epingle seule, aucun dossier (anti-pollution ~/Documents)")
    return ("PROD", "défaut raisonné : produit standalone (forcer EPINGLE_ONLY avec --epingle-only si idée)")


def next_labo_num():
    nums = []
    if RECHERCHES.is_dir():
        for d in RECHERCHES.iterdir():
            m = re.match(r"(\d{3})-", d.name)
            if m:
                nums.append(int(m.group(1)))
    return max(nums or [1]) + 1


def find_labo_by_slug(sl):
    if not RECHERCHES.is_dir():
        return None
    # Alias FR/EN : logical-calculus == 002-calcul-logique
    sl = LABO_SLUG_ALIAS.get(sl, sl)
    for d in RECHERCHES.iterdir():
        if d.is_dir() and (d.name.endswith(sl) or sl in d.name):
            return d
    return None


def ensure_labo(project, desc, dry=False):
    sl = slug(project)
    existing = find_labo_by_slug(sl)
    if existing:
        return [f"labo déjà placé {existing} (idempotent)"]
    num = next_labo_num()
    target = RECHERCHES / f"{num:03d}-{sl}"
    if dry:
        return [f"[DRY] labo+ {target} (T1 R81, outline seule)"]
    subdirs = ["notes", "code", "tests", "hypotheses", "benchmarks/runs",
               f"papers/draft-{num:03d}-{sl}", "references"]
    for s in subdirs:
        (target / s).mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    (target / "README.md").write_text(
        f"# {num:03d} — {project}\n\nQuestion : {desc}\n\n"
        f"## État ({today}, import Epingle, routeur auto_place)\n\n"
        f"- Recherche pure -> labo, pas de repo prod (R105 hub).\n"
        f"- Prochaine étape : T1 terminology scan R81 (15 min), landmarks, frontier 2022-2026.\n"
        f"- Papier seulement si angle nouveau (R81/R108).\n",
        encoding="utf-8")
    (target / "ROADMAP.md").write_text(
        "# ROADMAP\n\n- [ ] T1 terminology scan\n- [ ] T2 landmarks (2-3)\n"
        "- [ ] T3 frontier 2022-2026 (3-5)\n- [ ] T4 synthèse GO/PIVOT/ARCHIVE\n"
        "- [ ] T5+ expérience/axiomatique seulement si GO\n",
        encoding="utf-8")
    (target / "notes" / "00-vision.md").write_text(
        f"# 00-vision — {project}\n\nPourquoi ce labo : recherche publiable isolée du code prod. "
        f"Si T4 sans hypothèse falsifiable, on archive avec la leçon.\n",
        encoding="utf-8")
    (target / "code" / "README.md").write_text(
        "# Provenance\n\nAucune. Part de zéro. Ne copier depuis ailleurs qu'avec référence fichier:ligne.\n",
        encoding="utf-8")
    return [f"labo créé {target} + README/ROADMAP/notes/code (outline seule, pas de bench avant T4)"]


def ensure_prod(project, section, desc, status, pct, dry=False):
    sys.path.insert(0, str((KURORULES / "scripts").resolve()))
    try:
        import scaffold_idea as sc
        if dry:
            acts = sc.scaffold(project, section or "section à confirmer", desc, status, pct, dry=True)
        else:
            acts = sc.scaffold(project, section or "section à confirmer", desc, status, pct, dry=False)
        return [f"PROD: {a}" for a in acts]
    except Exception as exc:
        return [f"PROD erreur scaffold: {exc}"]


def adopted_channel(project):
    try:
        m = json.loads((KURORULES / "kuro_discord_map.local.json").read_text(encoding="utf-8"))
        return (m.get("channels", {}) or {}).get(project)
    except Exception:
        return None


def plan_discord(project, status, section, pct=0):
    sl = slug(project)
    # Recherches labo : restent dans le hub, jamais de salon par recherche
    if RECHERCHES.is_dir() and find_labo_by_slug(sl):
        return f"Discord: PAS de salon #{sl} (recherche labo -> hub #proj-horcruxe-labs, R105). Poster digest hub si T4=GO."
    # Adoption : ta structure gagne (#sybil, #hermes...) — jamais de doublon idea-
    hit = adopted_channel(project)
    if hit:
        return (f"Discord: {hit} <- {project} [{status}] (adopté, map locale) | "
                f"sync topic/parent via kuro_discord.py (Recherche : topic seul, pas de webhook spam)")
    kind = "proj" if (status or "").lower() in ("actif", "validation") else "idea"
    return (f"Discord: #{kind}-{sl} <- {project} [{status}] ({section or 'section à confirmer'}) | "
            f"Recherche/Proto -> idea- (sans webhook) ; Actif/Validation -> proj- + webhook via kuro_discord.py sync --apply")


def load_epingle_projects():
    sys.path.insert(0, str((KURORULES / "scripts").resolve()))
    import gen_x_posts as gx
    return gx.load_projects(str(EPINGLE))


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Routeur auto placement (labo/prod/epingle/externe/archive/alias)")
    ap.add_argument("--project", default="")
    ap.add_argument("--section", default="")
    ap.add_argument("--desc", default="Idée à valider.")
    ap.add_argument("--status", default="Recherche")
    ap.add_argument("--pct", type=int, default=0)
    ap.add_argument("--force", action="store_true", help="Force PROD même pour idée 0%% (ex: Sybil déjà forcée)")
    ap.add_argument("--epingle-only", action="store_true", help="Force EPINGLE_ONLY même si classé PROD")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--from-epingle", action="store_true", help="Route tous les Epingle sans dossier local")
    ap.add_argument("--from-discord-export", default="", help="Dossier/fichier export Discord (réutilise mapping sync_discord_to_epingle)")
    ap.add_argument("--plan-discord", action="store_true")
    args = ap.parse_args(argv)

    if args.plan_discord and args.project:
        print(plan_discord(args.project, args.status, args.section, args.pct))
        return 0
    if args.plan_discord:
        try:
            projs = load_epingle_projects()
        except Exception as exc:
            print(f"[ERR] Epingle illisible: {exc}")
            return 2
        for p in projs:
            print(plan_discord(p["name"], p.get("status", ""), p.get("section", ""), p.get("pct", 0)))
        return 0

    targets = []
    if args.from_epingle:
        try:
            projs = load_epingle_projects()
        except Exception as exc:
            print(f"[ERR] Epingle illisible: {exc}")
            return 2
        local_dirs = {d.name.lower() for d in DOCS.iterdir() if d.is_dir()}
        for p in projs:
            # Déjà placé (dossier prod ou labo) -> skip sauf dry-run informatif
            sl = slug(p["name"])
            if p["name"].lower() in local_dirs or find_labo_by_slug(sl):
                continue
            targets.append((p["name"], p.get("section", ""), p.get("desc", ""), p.get("status", ""), p.get("pct", 0)))
        print(f"Epingle sans place: {len(targets)} candidat(s)")
    elif args.from_discord_export:
        sys.path.insert(0, str((KURORULES / "scripts").resolve()))
        try:
            from pathlib import Path as _P  # noqa: N814 - alias local temporaire

            import sync_discord_to_epingle as sde
            msgs = sde.load_exports(_P(args.from_discord_export).expanduser())
            print(f"Discord: {len(msgs)} salon(s) avec messages")
            for proj, snippets in msgs.items():
                targets.append((proj, "à inférer du salon", (snippets[-1][:200] if snippets else ""), "Recherche", 0))
        except Exception as exc:
            print(f"[ERR] export Discord illisible: {exc}")
            return 2
    elif args.project:
        targets.append((args.project, args.section, args.desc, args.status, args.pct))
    else:
        ap.print_help()
        return 2

    for (proj, sec, desc, status, pct) in targets:
        placement, reason = classify(proj, sec, desc, status, pct)
        if args.force and placement == "EPINGLE_ONLY":
            placement, reason = "PROD", "forcé par --force (ex: Sybil, idée hacking à lancer)"
        if args.epingle_only and placement == "PROD":
            placement, reason = "EPINGLE_ONLY", "forcé par --epingle-only"
        print(f"\n[{proj}] -> {placement} ({reason})")
        print(f"  {plan_discord(proj, status, sec, pct)}")
        if placement == "LABO":
            for a in ensure_labo(proj, desc, dry=args.dry_run):
                print(f"  - {a}")
        elif placement == "PROD":
            for a in ensure_prod(proj, sec, desc, status, pct, dry=args.dry_run):
                print(f"  - {a}")
        elif placement in ("EPINGLE_ONLY", "EXTERNE", "ARCHIVE", "ALIAS", "REJECT"):
            print(f"  - aucune création dossier (placement {placement}) ; vérifier Epingle seule")
    return 0


if __name__ == "__main__":
    sys.exit(main())
