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
    # Orgs: /orgs/*, users: /users/*. Tente org d'abord, fallback user.
    for route in (f"/orgs/{owner}/repos?per_page=100", f"/users/{owner}/repos?per_page=100"):
        st, data = api("GET", route, token)
        if st == 200 and isinstance(data, list):
            return [
                f"{owner}/{r['name']}"
                for r in data
                if not r.get("archived") and not r.get("fork") and not r.get("disabled")
            ]
    return []


def api_retry(method: str, path: str, token: str, payload: dict | None = None, tries: int = 3):
    """Retry sur 502/500/503/429 (transitoires GitHub). Retourne (status, data, transient)."""
    import time
    last_st, last_data = 0, {"message": "no-attempt"}
    for i in range(tries):
        st, data = api(method, path, token, payload)
        if st in (200, 201, 204):
            return st, data, False
        # 404/401/403/422 = definitif (permissions ou non supporte), pas de retry
        if st in (401, 403, 404, 422):
            return st, data, False
        last_st, last_data = st, data
        if i < tries - 1:
            time.sleep(2 * (i + 1))
    return last_st, last_data, True


def harden_repo(repo: str, token: str) -> dict:
    out = {"repo": repo, "alerts_enabled": None, "autofix_enabled": None, "open_alerts": None}
    st, data, transient = api_retry(
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
    elif transient:
        out["alerts_enabled"] = f"TRANSIENT HTTP {st}: retry plus tard ({str(data.get('message', ''))[:50]})"
    elif st in (403, 404):
        out["alerts_enabled"] = f"PERM HTTP {st}: token sans admin ou repo sans GHAS"
    else:
        out["alerts_enabled"] = f"HTTP {st}: {data.get('message', '')[:60]}"

    out["open_alerts"] = count_open_alerts(repo, token)
    return out


def count_open_alerts(repo: str, token: str, pages: int = 10):
    """Compte TOUTES les alertes ouvertes (pagination, 100/page)."""
    total = 0
    for page in range(1, pages + 1):
        st, data, _ = api_retry(
            "GET", f"/repos/{repo}/dependabot/alerts?state=open&per_page=100&page={page}",
            token, tries=2)
        if st == 404 and page == 1:
            # Dependabot non active = inconnu, pas 0. Ne pas masquer.
            return "unknown (Dependabot off/404)"
        if st != 200 or not isinstance(data, list):
            return f"n/a (HTTP {st})" if page == 1 else total
        total += len(data)
        if len(data) < 100:
            break
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Kuro Security — durcissement multi-repos")
    parser.add_argument("--owners", nargs="+", default=["LambdaSection", "Lemniscate-world"])
    args = parser.parse_args()

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GH_TOKEN absent — sécurité non exécutable")
        return 0

    private = os.environ.get("KURO_PRIVATE_TOKEN") or None
    found: dict[str, str] = {}
    for tok in [t for t in (token, private) if t]:
        for owner in args.owners:
            for repo in discover(tok, owner):
                found.setdefault(repo, tok)
    print(f"DISCOVER {len(found)} repos actifs ({', '.join(args.owners)})"
          + (" + token prive" if private else ""))

    results = [harden_repo(r, tok) for r, tok in sorted(found.items())]

    enabled_now = sum(1 for r in results if r["alerts_enabled"] is True)
    failed = [r for r in results if isinstance(r["alerts_enabled"], str)]
    transient = [r for r in failed if str(r["alerts_enabled"]).startswith("TRANSIENT")]
    perm = [r for r in failed if str(r["alerts_enabled"]).startswith("PERM")]
    total_open, alert_repos, unknown = 0, [], []
    for r in results:
        if isinstance(r["open_alerts"], int):
            total_open += r["open_alerts"]
            if r["open_alerts"] > 0:
                alert_repos.append((r["repo"], r["open_alerts"]))
        elif isinstance(r["open_alerts"], str) and "unknown" in r["open_alerts"]:
            unknown.append(r["repo"])

    lines = [
        f"**Sécurité** : {enabled_now}/{len(results)} repos protégés "
        f"(alertes vulnérabilités + auto-fixes Dependabot)",
    ]
    if transient:
        lines.append("Transitoires (retry) : " + "; ".join(r["repo"] for r in transient[:5]))
    if perm:
        lines.append("Permissions/GHAS : " + "; ".join(r["repo"] for r in perm[:5]))
    if failed and not transient and not perm:
        lines.append("Échecs : " + "; ".join(f"{r['repo']} ({r['alerts_enabled']})" for r in failed[:5]))
    lines.append(f"Alertes Dependabot ouvertes (connues) : {total_open}")
    if unknown:
        lines.append(f"Inconnues (Dependabot off) : {len(unknown)} repos — activer avant de conclure 0 risque")
    lines += [f"- `{name}` : {n} alerte(s)" for name, n in sorted(alert_repos, key=lambda x: -x[1])[:8]]
    report = "\n".join(lines)
    print(report)
    # Statut machine pour investor_digest (fini le 15/15 en dur)
    try:
        from pathlib import Path as _P
        _status = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "protected": enabled_now,
            "total": len(results),
            "open_alerts_known": total_open,
            "unknown": unknown,
            "transient": [r["repo"] for r in transient],
            "perm": [r["repo"] for r in perm],
        }
        _P(__file__).resolve().parent.parent.joinpath("security-status.json").write_text(
            json.dumps(_status, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception:
        pass

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
