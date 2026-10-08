#!/usr/bin/env python3
"""linkedin_drafts.py — drafts LinkedIn depuis faits bruts (stdlib, R93).

Format : accroche (1 ligne) + 3-5 lignes pro + hashtags.
Lien jamais dans le post (algo) : note "lien en commentaire" ajoutée.
Gates : <= 3000 car, 3-5 hashtags max, ton factuel (R110), anti-leak
minimal (pas de token/secret/chemin local).

Usage :
    python scripts/linkedin_drafts.py --text "Shipped X. 138 tests pass." --project NeuralDBG --tags ML,PyTorch
    python scripts/linkedin_drafts.py --from-file outputs/x_post_2026-09-28.md --project NeuralDBG
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_paths import confine_arg  # noqa: E402

LEAK_PATTERNS = [
    r"(?i)\b(api[_-]?key|token|secret|password)\s*=\s*\S+",
    r"(?i)[a-f0-9]{32,}",
    r"C:\\Users\\[^\s]+",
    r"/home/[^\s]+",
]


def lint(text: str) -> list[str]:
    """Retourne la liste des problèmes (vide = OK)."""
    problems = []
    if len(text) > 3000:
        problems.append(f"trop long ({len(text)} > 3000)")
    for pat in LEAK_PATTERNS:
        if re.search(pat, text):
            problems.append(f"fuite possible : {pat[:40]}")
    return problems


def build_post(project: str, hook: str, body_lines: list[str], tags: list[str]) -> str:
    """Assemble le draft LinkedIn. Pur, testable."""
    tags = [t.strip().lstrip("#") for t in tags if t.strip()][:5]
    if len(tags) < 1:
        tags = [project]
    lines = [hook.strip(), ""]
    lines += [ln.strip() for ln in body_lines if ln.strip()][:5]
    lines += ["", "(Lien en premier commentaire — l'algo pénalise les liens.)", ""]
    lines += ["#" + t.replace(" ", "") for t in tags[:5]]
    return "\n".join(lines).strip() + "\n"


def split_x_draft(text: str) -> tuple[str, list[str]]:
    """Découpe un draft X : 1re ligne = accroche, reste = corps."""
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    lines = [ln for ln in lines if not ln.startswith("#")]
    if not lines:
        return "", []
    return lines[0], lines[1:]


def main() -> int:
    ap = argparse.ArgumentParser(description="Drafts LinkedIn")
    ap.add_argument("--text", default="")
    ap.add_argument("--from-file", default="")
    ap.add_argument("--project", default="lambda-Section")
    ap.add_argument("--tags", default="")
    ap.add_argument("--apply", action="store_true", help="écrit outputs/linkedin_YYYY-MM-DD-<projet>.md")
    args = ap.parse_args()
    if args.from_file:
        text = confine_arg(args.from_file, ROOT).read_text(encoding="utf-8", errors="replace")
    elif args.text:
        text = args.text
    else:
        print("--text ou --from-file requis")
        return 2
    hook, body = split_x_draft(text)
    if not hook:
        print("vide ou que des hashtags : rien-de-publiable")
        return 1
    tags = [t for t in args.tags.split(",") if t.strip()] or [args.project]
    post = build_post(args.project, hook, body, tags)
    problems = lint(post)
    if problems:
        print("LINT-BLOCK : " + " ; ".join(problems))
        return 3
    if args.apply:
        OUT.mkdir(exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", args.project.lower()).strip("-") or "post"
        dest = OUT / f"linkedin_{date.today():%Y-%m-%d}-{slug}.md"
        dest.write_text(post, encoding="utf-8")
        print(f"draft : {dest}")
    else:
        print(post)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
