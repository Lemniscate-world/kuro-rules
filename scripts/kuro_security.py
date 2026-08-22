#!/usr/bin/env python3
"""kuro_security.py — durcissement sécurité automatique multi-repos (zéro dépendance).

Pour chaque repo actif des comptes suivis :
    1. Active Dependabot alerts (vulnerability_alerts)
    2. Active les auto-fixes Dependabot (automated_security_fixes -> PRs automatiques)
    3. Compte les alertes ouvertes

Sortie : console + Discord ($DISCORD_WEBHOOK_URL). Échecs par repo collectés,
jamais fatal. Nécessite un token avec droits admin sur les repos ciblés.

Usage:
    python scripts/kuro_security.py [--owners LambdaSection Lemniscate-world]
"""

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.github.com"


def api(method: str, path: str, token: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Kuro/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except Exception as exc:
        code = getattr(exc, "code", None)
        return (code or 0), {"message": str(exc)[:100]}


def discover(token: str, owner: str) -> list[str]:
    st, data = api("GET", f"/users/{owner}/repos?per_page=100", token)
    if st != 200 or not isinstance(data, list):
        return []
    return [
        f"{owner}/{r['name']}"
        for r in data
        if not r.get("archived") and not r.get("fork") and not r.get("disabled")
    ]


def harden_repo(repo: str, token: str) -> dict:
    out = {"repo": repo, "alerts_enabled": None, "autofix_enabled": None, "open_alerts": None}
    st, data = api(
        "PATCH",
        f"/repos/{repo}",
        token,
        {
            "security_and_analysis": {
                "vulnerability_alerts": {"enabled": True},
                "automated_security_fixes": {"enabled": True},
            }
        },
    )
    if st == 200:
        out["alerts_enabled"] = True
        out["autofix_enabled"] = True
    else:
        out["alerts_enabled"] = f"HTTP {st}: {data.get('message', '')[:60]}"

    st2, data2 = api("GET", f"/repos/{repo}/dependabot/alerts?state=open&per_page=100", token)
    if st2 == 200 and isinstance(data2, list):
        out["open_alerts"] = len(data2)
    elif st2 == 404:
        out["open_alerts"] = 0
    else:
        out["open_alerts"] = f"n/a (HTTP {st2})"
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Kuro Security — durcissement multi-repos")
    parser.add_argument("--owners", nargs="+", default=["LambdaSection", "Lemniscate-world"])
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GH_TOKEN absent — sécurité non exécutable")
        return 0

    repos: list[str] = []
    for owner in args.owners:
        found = discover(token, owner)
        print(f"DISCOVER {owner}: {len(found)} repos actifs")
        repos.extend(found)

    results = [harden_repo(r, token) for r in repos]

    enabled_now = sum(1 for r in results if r["alerts_enabled"] is True)
    failed = [r for r in results if isinstance(r["alerts_enabled"], str)]
    total_open, alert_repos = 0, []
    for r in results:
        if isinstance(r["open_alerts"], int):
            total_open += r["open_alerts"]
            if r["open_alerts"] > 0:
                alert_repos.append((r["repo"], r["open_alerts"]))

    lines = [
        f"**Sécurité** : {enabled_now}/{len(results)} repos protégés "
        f"(alertes vulnérabilités + auto-fixes Dependabot)",
    ]
    if failed:
        lines.append("Échecs : " + "; ".join(f"{r['repo']} ({r['alerts_enabled']})" for r in failed[:5]))
    lines.append(f"Alertes Dependabot ouvertes : {total_open}")
    lines += [f"- `{name}` : {n} alerte(s)" for name, n in sorted(alert_repos, key=lambda x: -x[1])[:8]]
    report = "\n".join(lines)
    print(report)

    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if webhook and (failed or total_open > 0 or enabled_now != len(results)):
        payload = {
            "username": "Kuro",
            "embeds": [
                {
                    "title": "[SECURITE] Rapport durcissement — "
                    + datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    "description": report[:1900],
                    "color": 16098851 if failed else 3447003,
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
