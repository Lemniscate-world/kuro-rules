#!/usr/bin/env python3
"""veille_outils.py — veille hebdo outils IA (zéro dépendance).

Sources auto : HackerNews (API Algolia, sans clé) + GitHub search (sans auth,
quota 10 req/min). Agent.reviews : pas d'API publique connue -> URLs manuelles
via --url (répétable) intégrées en section dédiée.

Sortie : fiche RESEARCH_MEMORY/veille-outils-<YYYY-MM-DD>.md
(naming : <project>-<topic>-<date>, cf RESEARCH_MEMORY/README.md).

Usage:
    python scripts/veille_outils.py --out RESEARCH_MEMORY
    python scripts/veille_outils.py --out RESEARCH_MEMORY --url https://agent.reviews/... --limit 5
"""

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from kuro_paths import confine_arg

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
HN_API = "https://hn.algolia.com/api/v1/search"
GH_API = "https://api.github.com/search/repositories"


def get_json(url: str, timeout: int = 15) -> dict | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "kuro-veille/1.0", "Accept": "application/vnd.github.v3+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return json.loads(res.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"[warn] fetch {url[:80]}... -> {e}", file=sys.stderr)
        return None


def hn_hits(query: str, limit: int) -> list[dict]:
    params = urllib.parse.urlencode(
        {"query": query, "tags": "story", "hitsPerPage": limit}
    )
    data = get_json(f"{HN_API}?{params}")
    if not data:
        return []
    out = []
    for h in data.get("hits", [])[:limit]:
        out.append(
            {
                "title": h.get("title") or "(sans titre)",
                "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
                "points": h.get("points") or 0,
                "comments": h.get("num_comments") or 0,
            }
        )
    return out


def gh_repos(query: str, limit: int) -> list[dict]:
    params = urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": limit}
    )
    data = get_json(f"{GH_API}?{params}")
    if not data:
        return []
    out = []
    for r in data.get("items", [])[:limit]:
        out.append(
            {
                "name": r.get("full_name"),
                "url": r.get("html_url"),
                "stars": r.get("stargazers_count"),
                "desc": (r.get("description") or "").strip()[:180],
            }
        )
    return out


def verdict_hn(rank: int) -> str:
    if rank < 2:
        return "A tester"
    if rank < 5:
        return "Veille"
    return "Bruit"


def verdict_gh(rank: int) -> str:
    if rank < 2:
        return "A tester"
    if rank < 5:
        return "Veille"
    return "Bruit"


def main() -> int:
    ap = argparse.ArgumentParser(description="Veille hebdo outils IA -> fiche RESEARCH_MEMORY")
    ap.add_argument("--out", default="RESEARCH_MEMORY")
    ap.add_argument("--query", default="AI agent tool")
    ap.add_argument("--gh-query", default="AI agent stars:>500")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--url", action="append", default=[], help="URL manuelle (ex: Agent.reviews), répétable")
    args = ap.parse_args()

    # --out vient de la CLI (S8707) : confinement au depot (defaut RESEARCH_MEMORY).
    out_dir = confine_arg(args.out, ROOT, default="RESEARCH_MEMORY")
    out_dir.mkdir(parents=True, exist_ok=True)

    hn = hn_hits(args.query, args.limit)
    gh = gh_repos(args.gh_query, args.limit)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    path = out_dir / f"veille-outils-{today}.md"

    lines = [
        f"# Veille outils IA — {today}",
        "",
        f"Requête HN : `{args.query}` — Requête GitHub : `{args.gh_query}`",
        "",
        "## 1. HackerNews",
        "",
        "| Outil / titre | Points | Comments | Verdict | Lien |",
        "| :--- | ---: | ---: | :--- | :--- |",
    ]
    if hn:
        for i, h in enumerate(hn):
            v = verdict_hn(i)
            lines.append(f"| {h['title'][:90]} | {h['points']} | {h['comments']} | {v} | [lien]({h['url']}) |")
    else:
        lines.append("| (fetch HN échoué — offline ou quota) | — | — | — | — |")
    lines += [
        "",
        "## 2. GitHub (stars — chiffres API bruts, à recouper)",
        "",
        "| Repo | Stars | Verdict | Description |",
        "| :--- | ---: | :--- | :--- |",
    ]
    if gh:
        for i, r in enumerate(gh):
            v = verdict_gh(i)
            lines.append(f"| [{r['name']}]({r['url']}) | {r['stars']} | {v} | {r['desc']} |")
    else:
        lines.append("| (fetch GitHub échoué — offline ou quota 10 req/min) | — | — | — |")
    lines += ["", "## 3. Agent.reviews / URLs manuelles", ""]
    if args.url:
        # --url vient de la CLI : on n'accepte que des URLs http(s) pour eviter
        # tout scheme dangereux (javascript:, file:) et couper le taint S8707.
        for u in args.url:
            if urllib.parse.urlparse(u).scheme not in ("http", "https"):
                print(f"[WARN] URL ignoree (scheme non http/https) : {u}",
                      file=sys.stderr)
                continue
            lines.append(f"- [ ] {u} — Verdict : à lire, source IA-à-IA à recouper par test hermétique.")
    else:
        lines.append("(aucune URL manuelle — passe `--url https://...` pour tracer une review Agent.reviews)")
    lines += [
        "",
        "## 4. Décision",
        "",
        "- [ ] Top 3 « A tester » reproduits en sandbox avant d'intégrer au backlog.",
        "- Règle : une review IA ne vaut jamais un test hermétique local.",
        "",
    ]
    # out_dir est deja confine ; on reconfine le chemin final (sink S8707).
    confine_arg(path, ROOT).write_text("\n".join(lines), encoding="utf-8")
    n_test = sum(1 for i in range(len(hn)) if verdict_hn(i) == "A tester") + sum(
        1 for i in range(len(gh)) if verdict_gh(i) == "A tester"
    )
    print(f"OK {path} (HN={len(hn)} GH={len(gh)} a_tester~{n_test})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
