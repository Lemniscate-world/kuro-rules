#!/usr/bin/env python3
"""discovery_poll.py -- poll GitHub traffic 14j (R113) + snapshot + digest Discord.

Fenetre glissante 14j : la donnee non sondee est perdue, d'ou poll quotidien
via KuroDaily (scripts/kuro_automate.py). Zero dependance, Windows + Linux.

Usage:
    python scripts/discovery_poll.py [--discord] [--output reports/discovery_snapshot.json]

Stocke : views, clones, referrers par repo + followers + stars NeuralDBG.
Digest --discord : delta vs snapshot precedent + referrers (correlation R99).
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
DEFAULT_OUTPUT = ROOT / "reports" / "discovery_snapshot.json"

REPOS = [
    "LambdaSection/NeuralDBG",
    "Lemniscate-world/kuro-rules",
    "LambdaSection/TokenWise",
    "LambdaSection/Astral",
    "LambdaSection/Datalint",
    "LambdaSection/NeuralPaper",
    "LambdaSection/Sugar",
    "LambdaSection/Odin",
    "Lemniscate-world/LifeTrack",
    "Lemniscate-world/Lemniscate-world",
]


def gh_api(path):
    """GET via gh CLI (reutilise l'auth keyring). Retourne dict ou None."""
    try:
        r = subprocess.run(
            ["gh", "api", path],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        if r.returncode != 0:
            return None
        return json.loads(r.stdout) if r.stdout.strip() else None
    except Exception:
        return None


def poll_repo(repo):
    views = gh_api(f"repos/{repo}/traffic/views") or {}
    clones = gh_api(f"repos/{repo}/traffic/clones") or {}
    referrers = gh_api(f"repos/{repo}/traffic/popular/referrers") or []
    meta = gh_api(f"repos/{repo} --jq '{{\"stars\": .stargazers_count, \"forks\": .forks_count}}'")
    # gh api with --jq returns raw value; fallback via second call
    if not isinstance(meta, dict):
        full = gh_api(f"repos/{repo}")
        meta = {
            "stars": (full or {}).get("stargazers_count"),
            "forks": (full or {}).get("forks_count"),
        } if full else {}
    return {
        "views": views.get("count", 0),
        "views_uniques": views.get("uniques", 0),
        "clones": clones.get("count", 0),
        "clones_uniques": clones.get("uniques", 0),
        "referrers": [
            {"referrer": x.get("referrer"), "count": x.get("count"), "uniques": x.get("uniques")}
            for x in (referrers if isinstance(referrers, list) else [])
        ][:10],
        "stars": meta.get("stars"),
        "forks": meta.get("forks"),
    }


def poll_followers():
    u = gh_api("users/Lemniscate-world") or {}
    return {"followers": u.get("followers"), "public_repos": u.get("public_repos"), "blog": u.get("blog")}


def load_previous(path):
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def render_digest(snapshot, previous):
    lines = []
    prev_repos = (previous or {}).get("repos", {})
    for repo in REPOS:
        cur = snapshot["repos"].get(repo, {})
        prev = prev_repos.get(repo, {})
        if not cur:
            continue
        dv = cur.get("views", 0) - prev.get("views", 0) if prev else 0
        dc = cur.get("clones", 0) - prev.get("clones", 0) if prev else 0
        short = repo.split("/", 1)[1]
        flag = ""
        if dv != 0 or dc != 0:
            flag = f" ({dv:+d}v/{dc:+d}c)"
        refs = ", ".join(
            f"{x['referrer']}({x['count']})" for x in cur.get("referrers", [])[:3]
        ) or "-"
        lines.append(f"- {short}: {cur.get('views',0)}v/{cur.get('clones',0)}c{flag} | refs: {refs}")
    pf = (previous or {}).get("followers", {})
    cf = snapshot.get("followers", {})
    if pf and cf:
        df = (cf.get("followers") or 0) - (pf.get("followers") or 0)
        lines.append(f"- followers: {cf.get('followers')} ({df:+d}) | blog: '{cf.get('blog') or ''}'")
    # Spike alert: clones du jour > 50
    spikes = [r for r, d in snapshot["repos"].items() if d.get("clones", 0) >= 300]
    head = "Discovery 14j (R113)"
    if spikes:
        head += f" - {len(spikes)} repo(s) >=300 clones (bots/CI probables a qualifier)"
    return head, "\n".join(lines)


def post_discord(title, description):
    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("DISCORD_WEBHOOK_URL absent - digest non poste")
        return
    payload = {
        "username": "Kuro",
        "embeds": [{"title": f"[INFO] {title}", "description": description[:1900], "color": 3447003}],
    }
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "Kuro/1.0 (lambda-Section bot)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"Discord: HTTP {resp.status}")
    except Exception as exc:
        print(f"Discord erreur: {exc}")


def main():
    ap = argparse.ArgumentParser(description="Poll traffic GitHub R113")
    ap.add_argument("--discord", action="store_true", help="poste le digest sur Discord")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT))
    a = ap.parse_args()

    out = Path(a.output)
    previous = load_previous(out)
    snapshot = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "repos": {},
        "followers": {},
    }
    for repo in REPOS:
        snapshot["repos"][repo] = poll_repo(repo)
        d = snapshot["repos"][repo]
        print(f"{repo}: {d['views']}v/{d['clones']}c stars={d.get('stars')} refs={len(d['referrers'])}")
    snapshot["followers"] = poll_followers()
    print(f"followers: {snapshot['followers']}")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"snapshot: {out}")

    title, digest = render_digest(snapshot, previous)
    print(f"--- {title} ---\n{digest}")
    if a.discord:
        post_discord(title, digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
