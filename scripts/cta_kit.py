#!/usr/bin/env python3
"""cta_kit.py — briques capture leads (stdlib uniquement, R93).

- utm() : construit des URLs trackees (source/medium/campaign), jamais devinees.
- CTA : appels a l'action par canal, compatibles R96 (question d'abord,
  jamais de lien froid) et R94-v2 (lien X en reply, pas dans le post).
- MAGNETS : registre des lead magnets (slug -> promesse + format).
- Stockage leads : leads.local.json (gitignore, 100% local comme R111).

Usage :
    python scripts/cta_kit.py --list-magnets
    python scripts/cta_kit.py --utm https://github.com/org/repo --source reddit --campaign checklist
    python scripts/cta_kit.py --cta discord --url https://example.com/magnet
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
LEADS_FILE = ROOT / "leads.local.json"

MAGNETS = {
    "neuraldbg-7-patterns": {
        "title": "7 silent PyTorch failure patterns (checklist)",
        "promise": "La checklist qui aurait sauve vos 3 derniers trainings.",
        "format": "PDF 2 pages + repo exemple",
        "audience": "ML engineers, PyTorch",
    },
    "lifetrack-7day-reset": {
        "title": "7-day reset template",
        "promise": "Reprendre un tracking d'habitudes en 10 min, sans culpabilite.",
        "format": "Template imprimable 1 page",
        "audience": "self-trackers satures",
    },
}

CTA = {
    "x_reply": "Code et details ici : {url}",
    "linkedin_comment": "Lien en premier commentaire (l'algo penalise les liens) : {url}",
    "reddit": "J'ai mis la checklist complete ici si utile : {url} — curieux de vos retours surtout.",
    "discord": "Checklist complete ici pour ceux que ca interesse : {url} — des retours ?",
}


def utm(url: str, source: str, medium: str = "social", campaign: str = "launch",
        content: str = "") -> str:
    """Ajoute utm_source/medium/campaign(+content). Lève ValueError si URL invalide."""
    parts = urlparse((url or "").strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError(f"URL invalide : {url!r}")
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["utm_source"] = source.strip()
    query["utm_medium"] = medium.strip()
    query["utm_campaign"] = campaign.strip()
    if content.strip():
        query["utm_content"] = content.strip()
    return urlunparse(parts._replace(query=urlencode(query)))


def cta(channel: str, url: str) -> str:
    """Rend la phrase CTA du canal avec l'URL deja trackee injectee."""
    key = (channel or "").strip().lower()
    if key not in CTA:
        raise ValueError(f"Canal inconnu : {channel!r} (choix : {sorted(CTA)})")
    tracked = url  # l'appelant tracke via utm() avant
    return CTA[key].format(url=tracked)


def main() -> int:
    ap = argparse.ArgumentParser(description="Kit capture leads")
    ap.add_argument("--list-magnets", action="store_true")
    ap.add_argument("--utm", default="", help="URL a tracker")
    ap.add_argument("--source", default="x")
    ap.add_argument("--medium", default="social")
    ap.add_argument("--campaign", default="launch")
    ap.add_argument("--content", default="")
    ap.add_argument("--cta", default="", help="canal : x_reply|linkedin_comment|reddit|discord")
    ap.add_argument("--url", default="")
    args = ap.parse_args()
    if args.list_magnets:
        for slug, m in MAGNETS.items():
            print(f"{slug} : {m['title']} [{m['format']}] — {m['audience']}")
        return 0
    if args.utm:
        try:
            print(utm(args.utm, args.source, args.medium, args.campaign, args.content))
        except ValueError as exc:
            print(str(exc))
            return 2
        return 0
    if args.cta:
        if not args.url:
            print("--url requis avec --cta")
            return 2
        try:
            print(cta(args.cta, args.url))
        except ValueError as exc:
            print(str(exc))
            return 2
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
