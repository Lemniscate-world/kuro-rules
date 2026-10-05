#!/usr/bin/env python3
"""landing_deploy.py — génère une landing statique S1 (stdlib, R93).

N'écrit JAMAIS sur main/master : la cible est une branche openclaw/landing-*,
PR à merger par l'humain (politique push, R105).
La capture email exige un service tiers (Tally & co) : en attendant, la
landing propose mailto + contact direct (zéro setup, zéro fuite).

Usage :
    python scripts/landing_deploy.py --product neuraldbg --repo-dir /tmp/x --magnet-url https://... --contact user@example.com
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PRODUCTS = {
    "neuraldbg": {
        "name": "NeuralDBG",
        "tagline": "Why your PyTorch run failed — in seconds, not hours.",
        "bullets": [
            "Hooks the PyTorch training loop, ranks causal hypotheses by layer and step.",
            "MIT licensed, pip install, 100% local — your data never leaves.",
            "337 clones in 14 days from developers hitting the same wall.",
        ],
        "magnet_title": "7 silent PyTorch failure patterns (checklist, 2 pages)",
        "repo": "https://github.com/LambdaSection/NeuralDBG",
        "offer_title": "Free private beta",
        "offer_text": ("Get early access + a free diagnosis of one failed run. "
                       "In exchange: 30 minutes of feedback and, if it helped, a testimonial."),
        "offer_cta": "Apply for the beta",
    },
    "lifetrack": {
        "name": "LifeTrack",
        "tagline": "Restart habit tracking in 10 minutes, guilt-free.",
        "bullets": [
            "Local-first desktop app (Windows): habits, mood, N=1 experiments.",
            "No cloud, no telemetry — your data stays home.",
            "Correlations, streaks and AI insights on your own data.",
        ],
        "magnet_title": "7-day reset template (printable, 1 page)",
        "repo": "https://github.com/Lemniscate-world/LifeTrack",
    },
}

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name} — {tagline}</title>
<meta name="description" content="{tagline}">
<style>
body{{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;line-height:1.6;color:#111}}
a{{color:#0b5fff}} .cta{{display:inline-block;margin:8px 8px 8px 0;padding:10px 18px;border:1px solid #111;text-decoration:none;color:#111}}
small{{color:#555}}
</style>
</head>
<body>
<h1>{name}</h1>
<p><strong>{tagline}</strong></p>
<ul>
{bullets}
</ul>
<h2>Free checklist</h2>
<p>{magnet_title} : <a href="{magnet_url}">download</a></p>
<h2>{offer_title}</h2>
<p>{offer_text}</p>
<p><a class="cta" href="mailto:{contact}?subject=Beta%20application%20{mail_slug}">Apply for the beta</a></p>
<h2>Talk to us</h2>
<p><a class="cta" href="{repo}">GitHub repo</a> <a class="cta" href="mailto:{contact}">Email us</a></p>
<p><small>No tracking on this page. No newsletter trap : write, we answer.</small></p>
</body>
</html>
"""


def _valid_url(url: str) -> bool:
    u = (url or "").strip()
    if u.startswith(("http://", "https://", "mailto:")):
        return True
    return u.endswith((".html", ".pdf")) and " " not in u and "://" not in u


def build(product: str, magnet_url: str, contact: str) -> str:
    """Rend le HTML. Lève ValueError si produit inconnu ou URL invalide."""
    key = (product or "").strip().lower()
    if key not in PRODUCTS:
        raise ValueError(f"produit inconnu : {product!r} (choix : {sorted(PRODUCTS)})")
    if not _valid_url(magnet_url):
        raise ValueError(f"magnet_url invalide : {magnet_url!r}")
    if "@" not in (contact or ""):
        raise ValueError("contact email requis")
    p = PRODUCTS[key]
    bullets = "\n".join(f"<li>{b}</li>" for b in p["bullets"])
    if p.get("offer_title"):
        offer_block = ("<h2>" + p["offer_title"] + "</h2>\n<p>" + p.get("offer_text", "") + "</p>\n"
                       "<p><a class=\"cta\" href=\"mailto:" + contact + "?subject=Beta%20application%20" +
                       p["name"] + "\">Apply for the beta</a></p>\n")
    else:
        offer_block = ""
    page = PAGE.replace("<h2>{offer_title}</h2>\n<p>{offer_text}</p>\n"
                        "<p><a class=\"cta\" href=\"mailto:{contact}?subject=Beta%20application%20{mail_slug}\">"
                        "Apply for the beta</a></p>\n", offer_block)
    return page.format(name=p["name"], tagline=p["tagline"], bullets=bullets,
                       magnet_title=p["magnet_title"], magnet_url=magnet_url,
                       repo=p["repo"], contact=contact)


CHECKLIST_ITEMS = {
    "neuraldbg": [
        "NaN brutal : une seule operation instable contamine tout. Check : detect_anomaly sur run reduit.",
        "LR trop eleve + activation saturee : escalier des les premieres etapes. Check : LR/10 sur 50 etapes.",
        "Gradients evanouissants : couches profondes figees. Check : normes par couche a l'etape 100.",
        "ReLU morts en masse : >50 % a zero. Check : histogramme des activations.",
        "Oubli train()/eval() : ecart fantome. Check : meme batch dans les 2 modes.",
        "Seed et non-determinisme : 2 runs, 2 destins. Check : seeds fixees + versions notees.",
        "Donnees corrompues en silence : labels decales, fuite train/test. Check : visualiser 1 batch reel.",
    ],
    "lifetrack": [
        "Jeter l'arriere : aujourd'hui = jour 1, le passe est clos.",
        "3 habitudes max : sante, tete, oeuvre. Pas une de plus.",
        "Cocher binaire : fait / pas fait. Ni pourcentages ni notes.",
        "Phrase humeur : 7 mots max le soir.",
        "Jours 2-7 : repeter sans changer les regles.",
        "1 jour rate ne casse rien. 2 jours de suite : simplifier, pas abandonner.",
        "3 semaines parfaites n'existent pas : viser la reprise, pas la perfection.",
    ],
}

CHECKLIST_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{magnet_title}</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:640px;margin:40px auto;padding:0 16px;line-height:1.6;color:#111}}
a{{color:#0b5fff}}small{{color:#555}}
</style>
</head>
<body>
<h1>{magnet_title}</h1>
<ol>
{items}
</ol>
<p><a href="landing.html">Back : {name}</a> · <a href="{repo}">GitHub repo</a></p>
<p><small>Questions ? <a href="mailto:{contact}">Email us</a>. No tracking on this page.</small></p>
</body>
</html>
"""


def build_checklist(product: str, contact: str) -> str:
    """Rend la page checklist. Lève ValueError si produit inconnu."""
    key = (product or "").strip().lower()
    if key not in PRODUCTS:
        raise ValueError(f"produit inconnu : {product!r} (choix : {sorted(PRODUCTS)})")
    if "@" not in (contact or ""):
        raise ValueError("contact email requis")
    p = PRODUCTS[key]
    items = "\n".join(f"<li>{it}</li>" for it in CHECKLIST_ITEMS[key])
    return CHECKLIST_PAGE.format(magnet_title=p["magnet_title"], items=items,
                                name=p["name"], repo=p["repo"], contact=contact)


def main() -> int:
    ap = argparse.ArgumentParser(description="Génère landing/checklist dans un repo")
    ap.add_argument("--product", required=True)
    ap.add_argument("--repo-dir", required=True)
    ap.add_argument("--magnet-url", default="checklist.html")
    ap.add_argument("--contact", required=True)
    ap.add_argument("--page", choices=["landing", "checklist", "both"], default="both")
    args = ap.parse_args()
    try:
        pages = {}
        if args.page in ("landing", "both"):
            pages["landing.html"] = build(args.product, args.magnet_url, args.contact)
        if args.page in ("checklist", "both"):
            pages["checklist.html"] = build_checklist(args.product, args.contact)
    except ValueError as exc:
        print(str(exc))
        return 2
    docs = Path(args.repo_dir) / "docs"
    docs.mkdir(parents=True, exist_ok=True)
    for fname, html in pages.items():
        dest = docs / fname
        dest.write_text(html, encoding="utf-8")
        print(f"page : {dest} ({len(html)} car)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
