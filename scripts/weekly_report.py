#!/usr/bin/env python3
"""weekly_report.py — rapport hebdo consolidé Kuro (zéro dépendance).

Agrège : santé CI (ci-status.json), progression réelle (Epingle), repos
stagnants (>14 jours sans commit parmi les repos clonés). Poste le tout sur
Discord ($DISCORD_WEBHOOK_URL) ; no-op silencieux si le webhook est absent.

Usage:
    python scripts/weekly_report.py --ci-status ci-status.json \
        --epingle Epingle_Projets.md --repos-dir ~/Documents
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

STALE_DAYS = 14


def stale_repos(repos_dir: Path) -> list[tuple[str, int]]:
    """Repos locaux dont le dernier commit date de plus de STALE_DAYS jours."""
    out = []
    if not repos_dir.exists():
        return out
    now = datetime.now(timezone.utc).timestamp()
    for candidate in sorted(repos_dir.iterdir()):
        if not candidate.is_dir() or not (candidate / ".git").exists():
            continue
        try:
            res = subprocess.run(
                'git log -1 --format="%ct"',
                cwd=str(candidate),
                capture_output=True,
                text=True,
                shell=True,
                timeout=8,
            )
            ts = float(res.stdout.strip().strip('"'))
            days = int((now - ts) / 86400)
            if days > STALE_DAYS:
                out.append((candidate.name, days))
        except Exception:
            continue
    return out


def progression(epingle: Path) -> dict:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_portfolio import parse_epingle

    sections = parse_epingle(epingle)
    projs = [p for s in sections for p in s["projects"]]
    active = sum(1 for p in projs if "actif" in p["status"].lower())
    avg = sum(p["pct"] for p in projs) // len(projs) if projs else 0
    return {"total": len(projs), "active": active, "avg": avg, "sections": len(sections)}


def ci_summary(ci_status: dict | None) -> tuple[int, int, list[str]]:
    if not ci_status:
        return 0, 0, []
    repos = [r for r in ci_status.get("repos", []) if r.get("health") != "no_ci"]
    total = sum(len(r["workflows"]) for r in repos)
    ok = sum(1 for r in repos for w in r["workflows"] if w["conclusion"] == "success")
    reds = [
        f"{r['name']} ({', '.join(w['name'] for w in r['workflows'] if w['conclusion'] == 'failure')})"
        for r in repos
        if r["health"] == "red"
    ]
    return ok, total, reds


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapport hebdo Kuro")
    parser.add_argument("--ci-status", default=None)
    parser.add_argument("--epingle", required=True)
    parser.add_argument("--repos-dir", default=None)
    args = parser.parse_args()

    ci_data = None
    if args.ci_status and Path(args.ci_status).exists():
        ci_data = json.loads(Path(args.ci_status).read_text(encoding="utf-8"))

    ok, total, reds = ci_summary(ci_data)
    prog = progression(Path(args.epingle))
    stale = stale_repos(Path(args.repos_dir)) if args.repos_dir else []

    lines = [
        "**CI**",
        f"- {ok}/{total} checks verts" + (f" · rouges : {'; '.join(reds)}" if reds else ""),
        "",
        "**Progression (faits git)**",
        f"- {prog['total']} projets · {prog['active']} actifs · moyenne {prog['avg']}% sur {prog['sections']} sections",
    ]
    if stale:
        lines += ["", f"**Stagnation >{STALE_DAYS}j**"]
        lines += [f"- {name} ({days}j)" for name, days in stale[:10]]

    report = "\n".join(lines)
    print(report)

    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("DISCORD_WEBHOOK_URL absent - rapport non poste")
        return 0
    payload = {
        "username": "Kuro",
        "embeds": [
            {
                "title": "[RAPPORT] Hebdo Kuro — " + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "description": report[:1900],
                "color": 3447003,
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
