#!/usr/bin/env python3
"""upstream_watch.py -- veille hebdo repos tiers (R119/R121), lecture seule.

Scanne les issues/PRs ouvertes des repos surveilles (defaut: Agent-Reach,
repo EXTERNE - jamais de `gh repo edit` dessus), qualifie les cibles
(0-2 reponses, activite < 180j) et produit une file de drafts locale :
`docs/tracking/upstream_queue.md`.

GATE NON NEGOCIABLE (R120) : ce script ne poste RIEN sur GitHub.
L'humain relit chaque draft et dit "poste" ; le suivi R99 va dans
l'acquisition tracker sous 5 min apres envoi.

Usage:
    python scripts/upstream_watch.py --dry-run
    python scripts/upstream_watch.py --apply [--discord]
    python scripts/upstream_watch.py --apply --repo Owner/Repo --limit 20
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_QUEUE = ROOT / "docs" / "tracking" / "upstream_queue.md"

WATCH_REPOS = [
    "Panniantong/Agent-Reach",
]

ISSUE_FIELDS = "number,title,commentsCount,updatedAt,url,isPullRequest,labels"
PR_FIELDS = "number,title,commentsCount,updatedAt,url"


def gh_search(kind, repo, limit):
    """Retourne la liste brute `gh search` (kind = issues|prs), [] si echec."""
    fields = ISSUE_FIELDS if kind == "issues" else PR_FIELDS
    cmd = ["gh", "search", kind, "--repo", repo, "--state", "open",
           "--sort", "updated", "--order", "desc",
           "--limit", str(limit), "--json", fields]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60,
                           encoding="utf-8", errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    if r.returncode != 0:
        return []
    try:
        data = json.loads(r.stdout or "[]")
    except ValueError:
        return []
    return data if isinstance(data, list) else []


def gh_issue_body(repo, number, limit=800):
    """Extrait tronque du body d'une issue (contexte draft), '' si echec."""
    try:
        r = subprocess.run(
            ["gh", "issue", "view", str(number), "--repo", repo, "--json", "body"],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""
    if r.returncode != 0:
        return ""
    try:
        body = (json.loads(r.stdout) or {}).get("body") or ""
    except ValueError:
        return ""
    body = " ".join(body.split())
    return body[:limit] + ("..." if len(body) > limit else "")


def qualify(items, max_comments=2, max_age_days=180, now=None):
    """Filtre pur R119 : 0..max reponses, activite recente. Exclut les PRs du flux issues."""
    now = now or datetime.now(timezone.utc)
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get("kind") == "issue" and it.get("isPullRequest"):
            continue
        try:
            comments = int(it.get("commentsCount", 99))
        except (TypeError, ValueError):
            continue
        if comments > max_comments:
            continue
        try:
            updated = datetime.fromisoformat(str(it.get("updatedAt", "")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now - updated).days > max_age_days:
            continue
        out.append(it)
    out.sort(key=lambda x: str(x.get("updatedAt", "")), reverse=True)
    return out


def draft_skeleton(item, body_excerpt):
    """Squelette de draft aide-d'abord. L'aide technique reste a valider humainement."""
    url = item.get("url", "")
    title = item.get("title", "")
    lines = [
        f"## Draft -> {url}",
        "",
        f"> Cible : #{item.get('number')} ({item.get('kind')}) - {title}",
        f"> Reponses : {item.get('commentsCount')} - maj : {item.get('updatedAt', '')[:10]}",
        "",
        "### Contexte issue (extrait auto, ne pas copier tel quel)",
        "",
        body_excerpt or "(extrait indisponible - lire le thread avant de rediger)",
        "",
        "### Aide (A REDIGER humainement : etapes concretes + commandes + sortie reelle)",
        "",
        "- [ ] Repro locale faite (commandes exactes + sortie collee, pas de paraphrase)",
        "- [ ] Aide d'abord, zero promo froide ; mention produit ensuite = 1 phrase max ou rien",
        "",
        "### Gate avant envoi (R120, non negociable)",
        "",
        "- [ ] Texte relu et valide par l'humain (jamais de draft brut moteur)",
        "- [ ] Apres envoi : suivi 24h + entree acquisition tracker sous 5 min (R99)",
    ]
    return "\n".join(lines)


def render_queue(candidates, generated_at, repos):
    head = [
        "# Upstream Queue — file de drafts R119/R121 (validation humaine requise)",
        "",
        f"Genere le {generated_at} — scope : {', '.join(repos)}",
        "NE JAMAIS POSTER SANS RELECTURE HUMAINE (R120 gate 2).",
        "",
        "## Candidats qualifies (0-2 reponses, < 180j)",
        "",
        "| # | Type | Titre | Rep. | Maj | Lien |",
        "|---|---|---|---|---|---|",
    ]
    for c in candidates:
        head.append(
            f"| {c.get('number')} | {c.get('kind')} | "
            f"{str(c.get('title', ''))[:60]} | {c.get('commentsCount')} | "
            f"{str(c.get('updatedAt', ''))[:10]} | {c.get('url')} |")
    if not candidates:
        head.append("| - | - | (aucun candidat cette semaine) | - | - | - |")
    head += ["", "---", ""]
    if candidates:
        head.append(draft_skeleton(candidates[0],
                                   candidates[0].get("body_excerpt", "")))
        head += ["", "---", ""]
    head += [
        "Rappel : 1-2 threads/semaine/projet max (R119), 1 PR ou review/thread max,",
        "pas de DM, pas de brigading, 1 ping poli max si ignore 7j (R107/R121).",
    ]
    return "\n".join(head) + "\n"


def post_discord(title, description):
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("DISCORD_WEBHOOK_URL absent - digest non poste")
        return
    payload = {
        "username": "Kuro",
        "embeds": [{"title": f"[INFO] {title}", "description": description[:1900],
                    "color": 3447003}],
    }
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json",
                     "User-Agent": "Kuro/1.0 (upstream watch)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Discord: HTTP {resp.status}")
    except Exception as exc:
        print(f"Discord erreur: {exc}")


def main():
    ap = argparse.ArgumentParser(description="Veille upstream R119/R121 (lecture seule)")
    ap.add_argument("--apply", action="store_true", help="ecrit la file de drafts")
    ap.add_argument("--dry-run", action="store_true", help="affiche sans ecrire")
    ap.add_argument("--discord", action="store_true", help="poste le digest sur Discord")
    ap.add_argument("--repo", action="append", default=[], help="repo Owner/Name (repetable)")
    ap.add_argument("--limit", type=int, default=15, help="items par flux et par repo")
    ap.add_argument("--queue", default=str(DEFAULT_QUEUE), help="fichier file de drafts")
    ap.add_argument("--max-comments", type=int, default=2)
    ap.add_argument("--max-age", type=int, default=180, help="jours d'inactivite max")
    a = ap.parse_args()

    repos = a.repo or WATCH_REPOS
    items = []
    for repo in repos:
        for row in gh_search("issues", repo, a.limit):
            row["kind"] = "issue"
            row["repo"] = repo
            items.append(row)
        for row in gh_search("prs", repo, a.limit):
            row["kind"] = "pr"
            row["repo"] = repo
            items.append(row)
    if not items:
        print("veille: gh indisponible ou aucun item (non fatal)")
        return 1

    candidates = qualify(items, a.max_comments, a.max_age)
    if candidates:
        top = candidates[0]
        if top["kind"] == "issue":
            top["body_excerpt"] = gh_issue_body(top["repo"], top["number"])
        else:
            top["body_excerpt"] = ""
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    queue_md = render_queue(candidates, generated_at, repos)

    if a.apply and not a.dry_run:
        out = Path(a.queue)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(queue_md, encoding="utf-8")
        print(f"file : {out} ({len(candidates)} candidats)")
    else:
        print("=== Upstream watch dry-run ===")
        print(queue_md[:2000])

    for c in candidates[:5]:
        print(f"- #{c['number']} [{c['kind']}] {c['commentsCount']} rep. "
              f"{str(c['updatedAt'])[:10]} : {str(c['title'])[:70]}")

    if a.discord:
        top3 = "\n".join(
            f"- #{c['number']} [{c['kind']}] {str(c['title'])[:60]} ({c['url']})"
            for c in candidates[:3]) or "(aucun candidat)"
        post_discord(f"Upstream watch ({len(candidates)} candidats)",
                     f"File : docs/tracking/upstream_queue.md\n{top3}\n"
                     f"Rappel : validation humaine avant tout post (R120).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
