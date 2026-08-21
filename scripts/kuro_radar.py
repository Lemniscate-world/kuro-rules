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


def render(sections: list[tuple[str, list[dict]]]) -> str:
    lines = []
    for name, items in sections:
        lines.append(f"**{name}**")
        for it in items:
            extra = f" — _{it['desc']}_" if it.get("desc") else ""
            score = f" ({it['score']})" if it.get("score") else ""
            lines.append(f"- [{it['title']}]({it['url']}){score}{extra}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Kuro Radar — veille hebdo")
    parser.add_argument("--append-truth", default=None, help="TRUTH_DAILY.md à enrichir")
    parser.add_argument("--max-chars", type=int, default=1900)
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN")
    report = render(collect(token))
    print(report)

    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook:
        payload = {
            "username": "Kuro",
            "embeds": [
                {
                    "title": "[RADAR] Signaux du net — semaine du "
                    + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "description": report[: args.max_chars],
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
                print(f"Discord: HTTP {resp.status}")
        except Exception as exc:
            print(f"Discord erreur: {exc}")
    else:
        print("DISCORD_WEBHOOK_URL absent - signaux non postes")

    if args.append_truth and os.path.exists(args.append_truth):
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with open(args.append_truth, "a", encoding="utf-8") as fh:
            fh.write(f"\n## Signaux Radar (semaine du {stamp})\n\n{report}\n")
        print(f"TRUTH_DAILY enriched: {args.append_truth}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
