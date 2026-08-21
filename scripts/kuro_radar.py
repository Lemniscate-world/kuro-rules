#!/usr/bin/env python3
"""kuro_radar.py — veille externe hebdomadaire (zéro dépendance).

Sources publiques sans clé :
    - Hacker News (Algolia API)        : signaux tech par mots-clés
    - Reddit (top semaine)             : communautés ML / algotrading / biohacking
    - GitHub Search (repos récents)    : nouveaux projets qui montent
    - arXiv (cs.AI)                    : papiers récents

Sorties :
    - console (toujours)
    - Discord ($DISCORD_WEBHOOK_URL si présent)
    - append dans TRUTH_DAILY.md (--append-truth)

Toute source en erreur est ignorée silencieusement : le radar ne casse jamais le robot.

Usage:
    python scripts/kuro_radar.py [--append-truth path/TRUTH_DAILY.md]
"""

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

UA = "Mozilla/5.0 (compatible; KuroRadar/1.0; lambda-Section)"
MIN_HN_POINTS = 60
MIN_REDDIT_SCORE = 30
MIN_GH_STARS = 120

HN_QUERIES = ["LLM", "quantitative trading", "biohacking"]
REDDIT_SUBS = ["MachineLearning", "algotrading", "Biohackers"]
ARXIV_QUERY = 'cat:cs.AI AND submittedDate:[{start} TO {end}]'


def fetch_json(url: str, headers: dict | None = None) -> dict | list | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def week_ago_epoch() -> int:
    return int((datetime.now(timezone.utc) - timedelta(days=7)).timestamp())


def fetch_hn(query: str) -> list[dict]:
    filt = f"points>{MIN_HN_POINTS},created_at_i>{week_ago_epoch()}"
    url = (
        "https://hn.algolia.com/api/v1/search?"
        + urllib.parse.urlencode(
            {"query": query, "tags": "story", "numericFilters": filt, "hitsPerPage": 5}
        )
    )
    data = fetch_json(url)
    hits = data.get("hits", []) if isinstance(data, dict) else []
    return [
        {
            "title": h.get("title") or "",
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "score": h.get("points", 0),
        }
        for h in hits
        if h.get("title")
    ]


def fetch_reddit(sub: str) -> list[dict]:
    url = f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=5"
    data = fetch_json(url)
    posts = []
    try:
        for child in data["data"]["children"]:
            d = child.get("data", {})
            title = d.get("title", "")
            score = d.get("score", 0)
            if title and score >= MIN_REDDIT_SCORE:
                posts.append(
                    {
                        "title": title,
                        "url": "https://reddit.com" + d.get("permalink", ""),
                        "score": score,
                    }
                )
    except Exception:
        pass
    return posts


def fetch_github(token: str | None) -> list[dict]:
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    q = urllib.parse.quote(f"created:>{since} stars:>={MIN_GH_STARS}")
    url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=8"
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = fetch_json(url, headers)
    items = data.get("items", []) if isinstance(data, dict) else []
    return [
        {
            "title": f"{i.get('full_name')} ★{i.get('stargazers_count', 0)}",
            "url": i.get("html_url", ""),
            "score": i.get("stargazers_count", 0),
            "desc": (i.get("description") or "")[:110],
        }
        for i in items[:6]
    ]


def fetch_arxiv() -> list[dict]:
    start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y%m%d0000")
    end = datetime.now(timezone.utc).strftime("%Y%m%d2359")
    url = (
        "http://export.arxiv.org/api/query?search_query="
        + urllib.parse.quote(ARXIV_QUERY.format(start=start, end=end))
        + "&sortBy=submittedDate&sortOrder=descending&max_results=5"
    )
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    out = []
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            root = ET.fromstring(resp.read())
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns)[:4]:
            title = " ".join((entry.findtext("a:title", "", ns) or "").split())
            link = entry.findtext("a:id", "", ns)
            out.append({"title": title, "url": link, "score": 0})
    except Exception:
        pass
    return out


def collect(token: str | None) -> list[tuple[str, list[dict]]]:
    sections: list[tuple[str, list[dict]]] = []

    hn_items: list[dict] = []
    for q in HN_QUERIES:
        hn_items.extend(fetch_hn(q))
    hn_items.sort(key=lambda x: x["score"], reverse=True)
    sections.append(("Hacker News", hn_items[:5]))

    reddit_items: list[dict] = []
    for sub in REDDIT_SUBS:
        reddit_items.extend(fetch_reddit(sub))
    reddit_items.sort(key=lambda x: x["score"], reverse=True)
    sections.append(("Reddit", reddit_items[:5]))

    sections.append(("GitHub — nouveaux repos qui montent", fetch_github(token)))
    sections.append(("arXiv cs.AI", fetch_arxiv()))

    return [(name, items) for name, items in sections if items]


def render_section(name: str, items: list[dict]) -> str:
    lines = [f"**{name}**"]
    for it in items:
        extra = f" — _{it['desc']}_" if it.get("desc") else ""
        score = f" ({it['score']})" if it.get("score") else ""
        lines.append(f"- [{it['title']}]({it['url']}){score}{extra}")
    return "\n".join(lines)


STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "how",
    "why", "what", "when", "new", "using", "use", "build", "built", "building",
    "les", "des", "une", "pour", "avec", "dans", "sur", "est", "are", "can",
    "our", "out", "about", "more", "than", "then", "them", "they", "have",
    "been", "will", "would", "could", "should", "its", "his", "her", "not",
    "but", "all", "any", "you", "your", "get", "got", "one", "two", "app",
}

SECTION_LEXICON = {
    "1": {"llm", "model", "neural", "training", "inference", "agent", "agents",
          "rag", "debug", "dataset", "transformer", "embedding", "prompt",
          "network", "learning", "machine"},
    "2": {"trading", "quant", "backtest", "market", "strategy", "markov",
          "portfolio", "alpha", "stock", "crypto"},
    "3": {"bio", "health", "sleep", "longevity", "nutrition", "wearable",
          "hrv", "fitness", "supplement"},
    "9": {"devops", "pipeline", "deploy", "monitoring", "docker", "mlops",
          "automation", "observability", "infrastructure"},
}

STRONG = {
    "llm", "agent", "agents", "model", "models", "training", "inference",
    "prompt", "embedding", "benchmark", "claude", "gpt", "openai", "anthropic",
    "quant", "trading", "backtest", "market", "portfolio", "crypto",
    "health", "longevity", "sleep", "nutrition", "wearable",
    "devops", "mlops", "monitoring", "deploy", "pipeline", "automation",
}

FRENCH_MAP = {
    "apprentissage": "learning", "reseau": "network", "reseaux": "network",
    "entrainement": "training", "modele": "model", "modeles": "model",
    "marche": "market", "sante": "health", "sommeil": "sleep",
    "surveillance": "monitoring", "deploiement": "deploy",
    "automatisation": "automation", "donnees": "dataset",
}


def _tok(text: str) -> set[str]:
    import re

    raw = set(re.findall(r"[a-z]{3,}", text.lower()))
    mapped = {FRENCH_MAP.get(t, t) for t in raw}
    return mapped - STOPWORDS


def _section_num(name: str) -> str:
    import re

    m = re.search(r"section-(\d+)", name.lower())
    return m.group(1) if m else ""


def build_recommendations(
    sections: list[tuple[str, list[dict]]], epingle: Path | None
) -> list[str]:
    """Croise les signaux avec les projets (Epingle) : quoi intégrer / améliorer."""
    if not epingle or not epingle.exists():
        return []
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from generate_portfolio import parse_epingle

        secs = parse_epingle(epingle)
    except Exception as exc:
        print(f"Advisor: parse Epingle impossible ({exc})")
        return []

    projects = []
    for sec in secs:
        num = _section_num(sec["name"])
        lex = SECTION_LEXICON.get(num, set())
        for p in sec["projects"]:
            status = p["status"].lower()
            if status.startswith("archive"):
                continue
            own = _tok(f"{p['name']} {p['desc']}")
            projects.append({"name": p["name"], "status": status,
                             "own": own, "tokens": own | lex,
                             "section": num, "pct": p["pct"]})

    recs: list[tuple[int, str]] = []
    idea_sections: dict[str, list[str]] = {}
    seen_projects: set[str] = set()
    for name, items in sections:
        for it in items:
            sig = _tok(f"{it['title']} {it.get('desc', '')}")
            strong_hits = sig & STRONG
            if not sig:
                continue
            best: list[tuple[int, dict, set[str]]] = []
            matched_any = False
            for prj in projects:
                if prj["name"] in seen_projects:
                    continue
                overlap_own = sig & prj["own"]
                overlap_lex = sig & (prj["tokens"] - prj["own"])
                if len(overlap_own) >= 2 or (overlap_own and overlap_lex):
                    matched_any = True
                    score = len(overlap_own) * 3 + len(overlap_lex)
                    best.append((score, prj, overlap_own | overlap_lex))
                elif overlap_lex and strong_hits:
                    matched_any = True
                    best.append((1, prj, overlap_lex))
            best.sort(key=lambda x: x[0], reverse=True)
            for score, prj, overlap in best[:1]:
                seen_projects.add(prj["name"])
                words = ", ".join(sorted(overlap)[:4])
                if score >= 3:
                    verb = "intégrer dans" if prj["pct"] >= 20 else "relancer avec"
                    recs.append((score, f"**{verb} `{prj['name']}`** ← [{it['title']}]({it['url']}) (mots : {words})"))
                else:
                    recs.append((1, f"**À surveiller pour `{prj['name']}`** ← [{it['title']}]({it['url']}) ({words})"))
            if not matched_any and len(strong_hits) >= 2:
                for num, lex in SECTION_LEXICON.items():
                    hits = strong_hits & lex
                    if len(hits) >= 2:
                        idea_sections.setdefault(num, []).append(
                            f"[{it['title']}]({it['url']})"
                        )
                        break

    seen = set()
    out = []
    for _, line in sorted(recs, key=lambda x: x[0], reverse=True)[:8]:
        key = line.split("<-")[0]
        if key not in seen:
            seen.add(key)
            out.append("- " + line)
    for num, ideas in idea_sections.items():
        sample = ideas[0]
        out.append(f"**Idée de nouveau repo pour la section S-{num}** : {sample}")
    return out


def post_discord(webhook: str, blocks: list[tuple[str, str]], max_chars: int) -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ok = 0
    for title, body in blocks:
        while body:
            chunk, body = body[:max_chars], body[max_chars:]
            payload = {
                "username": "Kuro",
                "embeds": [
                    {
                        "title": f"{title} — {stamp}" if len(blocks) > 1 else f"{title} — {stamp}",
                        "description": chunk,
                        "color": 3066993,
                    }
                ],
            }
            try:
                req = urllib.request.Request(
                    webhook,
                    data=json.dumps(payload).encode(),
                    method="POST",
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Kuro/1.0 (lambda-Section bot)",
                    },
                )
                with urllib.request.urlopen(req, timeout=15) as resp:
                    ok += 1
                    if resp.status != 204:
                        print(f"Discord: HTTP {resp.status}")
            except Exception as exc:
                print(f"Discord erreur: {exc}")
                break
    print(f"Discord: {ok} message(s) envoye(s)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Kuro Radar — veille hebdo")
    parser.add_argument("--append-truth", default=None, help="TRUTH_DAILY.md à enrichir")
    parser.add_argument("--epingle", default=None, help="Epingle_Projets.md pour l'advisor")
    parser.add_argument("--max-chars", type=int, default=1900)
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN")

    sections = collect(token)
    blocks: list[tuple[str, str]] = [
        ("[RADAR] " + name, render_section(name, items)) for name, items in sections
    ]

    recs = build_recommendations(sections, Path(args.epingle) if args.epingle else None)
    if recs:
        blocks.append(("[RADAR] Recommandations pour nos projets", "\n".join(recs)))

    full_report = "\n\n".join(body for _, body in blocks)
    print(full_report)

    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook:
        post_discord(webhook, blocks, args.max_chars)
    else:
        print("DISCORD_WEBHOOK_URL absent - signaux non postes")

    if args.append_truth and os.path.exists(args.append_truth):
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(args.append_truth, "a", encoding="utf-8") as fh:
            fh.write(f"\n## Signaux Radar + recommandations (semaine du {stamp})\n\n{full_report}\n")
        print(f"TRUTH_DAILY enriched: {args.append_truth}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
