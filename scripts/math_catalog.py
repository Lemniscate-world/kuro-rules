#!/usr/bin/env python3
"""math_catalog.py — sandbox d'exploration openai/math (zéro dépendance).

openai/math N'EST PAS une lib de calcul : c'est 719 manuscrits + preuves Lean
produits par un modèle OpenAI (release 06/10/2026, Apache-2.0). Pas de clone
complet (PDFs lourds) : on exploite CONTENTS.md (manuscript map) via HTTP.

Usage:
    python scripts/math_catalog.py --list
    python scripts/math_catalog.py --find optimization
    python scripts/math_catalog.py --get 102 --fiche RESEARCH_MEMORY
"""

import argparse
import os
import re
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from kuro_paths import confine_arg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
# Racines legitimes du cache : le depot ou le temp systeme (defaut de --cache).
_CACHE_ROOTS = [ROOT, Path(tempfile.gettempdir()).resolve()]

CONTENTS_URL = "https://raw.githubusercontent.com/openai/math/main/CONTENTS.md"
FAMILY_RE = re.compile(r"\*\*(\d{3})\.\s*(.*?)\*\*", re.DOTALL)
LINK_RE = re.compile(r"\[.*?\]\((preprints/.*?)\)")


def fetch_contents(cache: Path) -> str:
    # --cache vient de la CLI (S8707) : confinement depot + temp (defaut).
    cache = confine_arg(cache, _CACHE_ROOTS)
    if cache.exists() and cache.stat().st_size > 100_000:
        return cache.read_text(encoding="utf-8", errors="replace")
    req = urllib.request.Request(CONTENTS_URL, headers={"User-Agent": "kuro-sandbox/1.0"})
    with urllib.request.urlopen(req, timeout=60) as res:
        text = res.read().decode("utf-8", errors="replace")
    cache.write_text(text, encoding="utf-8")
    return text


def families(text: str) -> list[tuple[str, str, str]]:
    """-> [(num, title, block)] ; block = texte jusqu'à la famille suivante."""
    matches = list(FAMILY_RE.finditer(text))
    out = []
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        num = m.group(1)
        title = re.sub(r"\s+", " ", m.group(2)).strip()[:150]
        out.append((num, title, text[m.start() : end]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Explore openai/math sans clone complet")
    ap.add_argument("--list", action="store_true", help="liste les 372 familles")
    ap.add_argument("--find", metavar="MOT", help="recherche insensible à la casse")
    ap.add_argument("--get", metavar="NNN", help="affiche le bloc complet d'une famille")
    ap.add_argument("--fiche", metavar="DIR", help="écrit une fiche RESEARCH_MEMORY/<slug>-<date>.md")
    ap.add_argument("--cache", default=os.path.join(tempfile.gettempdir(), "openai-math-CONTENTS.md"))
    args = ap.parse_args()

    if not (args.list or args.find or args.get):
        ap.print_help()
        return 1

    text = fetch_contents(Path(args.cache))
    fams = families(text)
    print(f"# {len(fams)} familles indexées (CONTENTS.md, {len(text)//1024} Ko)", file=sys.stderr)

    selected: list[tuple[str, str, str]] = []
    if args.list:
        for num, title, _ in fams:
            print(f"{num} — {title}")
        return 0
    if args.find:
        kw = args.find.lower()
        for fam in fams:
            if kw in (fam[1] + fam[2]).lower():
                selected.append(fam)
        for num, title, block in selected:
            links = LINK_RE.findall(block)
            print(f"\n## {num} — {title}")
            print(f"   preprints: {len(links)}")
            for link in links[:4]:
                print(f"   - https://github.com/openai/math/blob/main/{link}")
        print(f"\n{len(selected)} famille(s) pour '{args.find}'", file=sys.stderr)
    if args.get:
        selected = [f for f in fams if f[0] == args.get]
        if not selected:
            print(f"Famille {args.get} introuvable.", file=sys.stderr)
            return 2
        num, title, block = selected[0]
        plain = re.sub(r"<[^>]+>", "", block)
        plain = re.sub(r"[ \t]+", " ", plain)
        print(f"# {num} — {title}\n")
        print(plain[:4000])

    if args.fiche and selected:
        # --fiche vient de la CLI (S8707) : confinement au depot (RESEARCH_MEMORY).
        out_dir = confine_arg(args.fiche, ROOT, default="RESEARCH_MEMORY")
        out_dir.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", (args.find or args.get or "math").lower()).strip("-")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        path = out_dir / f"math-{slug}-{today}.md"
        lines = [f"# openai/math — {slug} ({today})", "",
                 "Source : https://github.com/openai/math (manuscrits + Lean, Apache-2.0).",
                 "Statut verif : ~42% formalisé, le reste peut contenir des erreurs (cf README upstream).", ""]
        for num, title, block in selected:
            links = LINK_RE.findall(block)
            lines += [f"## Famille {num} — {title}", ""]
            for link in links:
                lines.append(f"- https://github.com/openai/math/blob/main/{link}")
            lines.append("")
        lines += ["## Verdict sandbox",
                  "- [ ] Manuscrit pertinent pour nos besoins (opti/quanti) ? Lire 1 preprint ciblé.",
                  "- [ ] Si preuve Lean dispo : vérifier via Comparator (toolchain Lean 4.32, hors scope PC actuel).",
                  "- Rappel : ceci n'est pas une lib de calcul — proto numérique = SymPy/NumPy, pas ce repo.", ""]
        # slug vient de --find/--get (CLI) : confinement final du chemin d'ecriture.
        confine_arg(path, ROOT).write_text("\n".join(lines), encoding="utf-8")
        print(f"Fiche {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
