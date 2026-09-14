#!/usr/bin/env python3
"""kuro_pr_agent.py — agent PR : checks rouges -> autofix sur ou proposition LLM + Discord.

Pour chaque PR ouverte des owners suivis :
  - checks verts : rien a faire.
  - echec auto-reparable (formatting, protected_files, lint_dead) : push du fix
    sur la branche de la PR (jamais main/master, jamais de fork).
  - autre echec : diagnostic LLM poste en commentaire (1x par run) + proposition.
  - tout est resume sur Discord : l'humain relit et merge, le robot ne merge jamais.

Usage:
  python scripts/kuro_pr_agent.py --dry-run            # defaut : lecture seule
  python scripts/kuro_pr_agent.py --write --max-prs 5  # CI : ecrit reellement
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ci_guardian import (  # noqa: E402
    DEFAULT_OWNERS,
    ai_diagnose,
    api,
    auto_fix,
    classify_failure,
    discover_repos,
    fetch_failed_log,
    rerun_failed_jobs,
)

SAFE_KLASSES = {"formatting", "protected_files", "lint_dead"}
PROTECTED_REFS = {"main", "master"}
MARKER = "<!-- kuro-pr-agent -->"


def _token() -> str:
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""


def open_prs(repo: str, token: str) -> list:
    st, data = api("GET", f"/repos/{repo}/pulls?state=open&per_page=20", token)
    return data if st == 200 and isinstance(data, list) else []


def failing_checks(repo: str, sha: str, token: str) -> list:
    st, data = api("GET", f"/repos/{repo}/commits/{sha}/check-runs?per_page=50", token)
    if st != 200 or not isinstance(data, dict):
        return []
    return [c for c in data.get("check_runs", []) if c.get("conclusion") == "failure"]


def run_id_from_url(url: str) -> int | None:
    m = re.search(r"/runs/(\d+)/", url or "")
    return int(m.group(1)) if m else None


def run_attempt(repo: str, run_id: int, token: str) -> int:
    st, data = api("GET", f"/repos/{repo}/actions/runs/{run_id}", token)
    if st == 200 and isinstance(data, dict):
        try:
            return int(data.get("run_attempt", 1))
        except (TypeError, ValueError):
            pass
    return 1


def already_commented(repo: str, number: int, run_id: int | None, token: str) -> bool:
    st, data = api("GET", f"/repos/{repo}/issues/{number}/comments?per_page=30", token)
    if st != 200 or not isinstance(data, list):
        return False
    needle = f"{MARKER} run={run_id}" if run_id else MARKER
    return any(isinstance(c, dict) and needle in (c.get("body") or "") for c in data)


def post_comment(repo: str, number: int, body: str, token: str) -> bool:
    st, _ = api("POST", f"/repos/{repo}/issues/{number}/comments", token, {"body": body})
    return st in (200, 201)


def fixable_push(repo: str, klass: str, detail: str, log: str, token: str,
                 head: str, fork: bool, write: bool) -> str:
    """Push autofix sur la branche PR, ou raison du refus."""
    if klass not in SAFE_KLASSES:
        return "classe non auto-reparable"
    if fork:
        return "fork : push refuse, commentaire seul"
    if not write:
        return f"dry-run : {klass} serait pousse sur {head}"
    res = auto_fix(repo, klass, detail, log, token, False, head_branch=head)
    return res.get("detail", res.get("action", "?"))


def propose(repo: str, pr: dict, check: dict, run_id: int | None, token: str, write: bool) -> str:
    """Diagnostic LLM en commentaire (dedup par run), ou raison."""
    number = pr.get("number")
    if run_id and already_commented(repo, number, run_id, token):
        return "proposition deja postee pour ce run"
    diag = ai_diagnose(repo, run_id, token) if run_id else None
    body = (
        f"{MARKER} run={run_id}\n"
        f"**Kuro PR-agent** — `{check.get('name')}` en echec sur `{pr.get('head', {}).get('ref')}`.\n\n"
        f"{diag or '_Diagnostic LLM indisponible (cerveau down) — diagnostic deterministe a venir._'}\n\n"
        f"[Voir le run]({check.get('html_url', '')})"
    )
    if not write:
        return "dry-run : proposition non postee"
    return "proposition postee" if post_comment(repo, number, body, token) else "post commentaire impossible"


def process_check(repo: str, pr: dict, check: dict, token: str, write: bool) -> str:
    head = (pr.get("head") or {}).get("ref", "?")
    run_id = run_id_from_url(check.get("html_url", ""))
    log = fetch_failed_log(repo, run_id, token) if run_id else ""
    diag = classify_failure(log) if log else None
    if diag and diag.get("klass") in SAFE_KLASSES:
        fork = bool(((pr.get("head") or {}).get("repo") or {}).get("fork"))
        outcome = fixable_push(repo, diag["klass"], diag.get("detail", ""), log, token, head, fork, write)
        return f"{check.get('name')} [{diag['klass']}] -> {outcome}"
    if diag is None and run_id and run_attempt(repo, run_id, token) <= 1:
        if not write:
            return f"{check.get('name')} [inconnu] -> dry-run : relance envisagee"
        ok = rerun_failed_jobs(repo, run_id, token)
        return f"{check.get('name')} [inconnu] -> {'relance' if ok else 'relance impossible'}"
    outcome = propose(repo, pr, check, run_id, token, write)
    cause = (diag or {}).get("cause", "cause inconnue") if diag else "cause inconnue"
    return f"{check.get('name')} [{cause[:60]}] -> {outcome}"


def process_pr(repo: str, pr: dict, token: str, write: bool) -> list[str]:
    head = (pr.get("head") or {}).get("ref", "?")
    tag = f"{repo}#{pr.get('number')} ({head})"
    if head in PROTECTED_REFS:
        return [f"{tag} : branche protegee, ignore"]
    failing = failing_checks(repo, pr.get("head", {}).get("sha", ""), token)
    if not failing:
        return [f"{tag} : verte"]
    lines = [f"{tag} : {len(failing)} check(s) rouge(s)"]
    for check in failing[:3]:
        try:
            lines.append(f"  - {process_check(repo, pr, check, token, write)}")
        except Exception as e:
            lines.append(f"  - {check.get('name')} : erreur agent ({e})")
    return lines


def post_discord(lines: list[str]) -> None:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url or not lines:
        return
    payload = {
        "username": "Kuro",
        "embeds": [{
            "title": "[PR-AGENT] Revue PR — " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
            "description": "\n".join(lines)[:1900],
            "color": 3447003,
        }],
    }
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "User-Agent": "Kuro/1.0"})
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"Discord erreur : {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent PR Kuro")
    ap.add_argument("--owners", nargs="+", default=DEFAULT_OWNERS)
    ap.add_argument("--max-prs", type=int, default=5)
    ap.add_argument("--write", action="store_true", help="push/commentaires reels (defaut: dry-run)")
    a = ap.parse_args()
    token = _token()
    if not token:
        print("GH_TOKEN absent — lecture seule GitHub impossible")
        return 0
    write = a.write
    print(f"=== KURO PR-AGENT write={write} ===")
    lines: list[str] = []
    seen = 0
    for owner in a.owners:
        for repo in discover_repos(owner, token):
            for pr in open_prs(repo, token):
                if seen >= a.max_prs:
                    break
                seen += 1
                lines.extend(process_pr(repo, pr, token, write))
            if seen >= a.max_prs:
                break
    print("\n".join(lines) or "Aucune PR ouverte.")
    if write:
        post_discord(lines)
    else:
        print("(dry-run : rien pousse ni poste)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
