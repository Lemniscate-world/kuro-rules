#!/usr/bin/env python3
"""discovery_poll.py -- poll GitHub traffic 14j (R113) + snapshot + digest Discord.

Fenetre glissante 14j : la donnee non sondee est perdue, d'ou poll quotidien
via KuroDaily (scripts/kuro_automate.py). Zero dependance, Windows + Linux.

Usage:
    python scripts/discovery_poll.py [--discord] [--output reports/discovery_snapshot.json] [--history reports/discovery_history.csv]

Stocke : views, clones, referrers par repo + followers (user + org LambdaSection) + stars/forks.
Historique : CSV versionne pour la courbe (le JSON est ecrase a chaque run).
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_paths import confine_arg  # noqa: E402

DEFAULT_OUTPUT = ROOT / "reports" / "discovery_snapshot.json"
DEFAULT_HISTORY = ROOT / "reports" / "discovery_history.csv"
HISTORY_HEADER = "timestamp,repo,views,views_uniques,clones,clones_uniques,stars,forks\n"

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
    # NOTE: pas de --jq via gh_api (un seul arg path) -> un seul appel meta.
    full = gh_api(f"repos/{repo}") or {}
    meta = {
        "stars": full.get("stargazers_count"),
        "forks": full.get("forks_count"),
    }
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
    # Org LambdaSection (7/10 repos suivis) : public_repos + followers via /orgs.
    org = gh_api("orgs/LambdaSection") or {}
    return {
        "followers": u.get("followers"),
        "public_repos": u.get("public_repos"),
        "blog": u.get("blog"),
        "orgs": {
            "LambdaSection": {
                "public_repos": org.get("public_repos"),
                "followers": org.get("followers"),
                "blog": org.get("blog"),
            }
        },
    }


def load_previous(path):
    try:
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def append_history(history_path, snapshot):
    """Ajoute une ligne par repo au CSV versionne (courbe R113).

    Le snapshot JSON est ecrase a chaque run (fenetre 14j perdue),
    le CSV garde l'historique : timestamp,repo,views,views_uniques,
    clones,clones_uniques,stars,forks.
    """
    try:
        p = Path(history_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists() or p.stat().st_size == 0:
            p.write_text(HISTORY_HEADER, encoding="utf-8")
        ts = snapshot.get("generated_at", "")
        rows = []
        for repo in REPOS:
            d = snapshot.get("repos", {}).get(repo, {})
            if not d:
                continue
            rows.append(
                f"{ts},{repo},{d.get('views', 0)},{d.get('views_uniques', 0)},"
                f"{d.get('clones', 0)},{d.get('clones_uniques', 0)},"
                f"{d.get('stars', '')},{d.get('forks', '')}\n"
            )
        if rows:
            with p.open("a", encoding="utf-8", newline="") as f:
                f.writelines(rows)
        return str(p)
    except Exception as exc:
        print(f"history erreur: {exc}")
        return ""


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
            f"{x['referrer']}({x['count']})" for x in cur.get("referrers", [])[:5]
        ) or "-"
        lines.append(
            f"- {short}: {cur.get('views', 0)}v({cur.get('views_uniques', 0)}u)"
            f"/{cur.get('clones', 0)}c({cur.get('clones_uniques', 0)}u)"
            f"{flag} | refs: {refs}"
        )
    pf = (previous or {}).get("followers", {})
    cf = snapshot.get("followers", {})
    if cf:
        df = (cf.get("followers") or 0) - (pf.get("followers") or 0) if pf else 0
        org = (cf.get("orgs") or {}).get("LambdaSection", {})
        lines.append(
            f"- followers: {cf.get('followers')} ({df:+d})"
            f" [LambdaSection: {org.get('followers')}f/{org.get('public_repos')}r]"
            f" | blog: '{cf.get('blog') or ''}'"
        )
    # Spike alert: fenetre glissante 14j avec clones totaux >= 300.
    # Ratio clones >> vues et clones_uniques eleves = bots/CI probables, a qualifier.
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
    ap.add_argument("--history", default=str(DEFAULT_HISTORY))
    a = ap.parse_args()

    out = confine_arg(a.output, ROOT, default="reports/discovery_snapshot.json")
    hist = confine_arg(a.history, ROOT, default="reports/discovery_history.csv")
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
    hpath = append_history(hist, snapshot)
    if hpath:
        print(f"history: {hpath}")

    title, digest = render_digest(snapshot, previous)
    print(f"--- {title} ---\n{digest}")
    if a.discord:
        post_discord(title, digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
