#!/usr/bin/env python3
"""Kuro Central Rules Guard - enforcement CI de la fraicheur des regles (R11/R105).

Modes :
  local   : audite les repos du disque (projects.txt vs master) ; --apply resynchronise.
  remote  : enumere les repos GitHub (orgs + user), compare AGENTS.md au master ;
            --fix recommitte le redirector a jour sur la branche par defaut.

Sortie : rapport console + reports/rules_audit_<date>.json
"""

import argparse
import base64
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

KURO_DIR = pathlib.Path(__file__).resolve().parent.parent
MASTER_AGENTS = KURO_DIR / "AGENTS.md"
PROJECTS_FILE = KURO_DIR / "projects.txt"
REPORTS_DIR = KURO_DIR / "reports"
DOCS_DIR = pathlib.Path.home() / "Documents"
GITHUB_API = "https://api.github.com"


def normalize(text):
    return text.replace("\r\n", "\n").replace("\r", "\n")


def load_master():
    if not MASTER_AGENTS.exists():
        sys.exit("AGENTS.md master introuvable dans kuro-rules")
    return normalize(MASTER_AGENTS.read_text(encoding="utf-8-sig"))


def rule_count(text):
    return sum(1 for line in text.splitlines() if line.startswith("- **rule_"))


def local_projects():
    if not PROJECTS_FILE.exists():
        return []
    names = [
        line.strip()
        for line in PROJECTS_FILE.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return [n for n in names if (DOCS_DIR / n).is_dir()]


def github_request(url, token, method="GET", payload=None):
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return resp.status, json.loads(body) if body else {}
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


def list_remote_repos(token, orgs, include_user):
    repos = []
    for org in orgs:
        page = 1
        while True:
            status, batch = github_request(
                f"{GITHUB_API}/orgs/{org}/repos?per_page=100&page={page}", token
            )
            if status != 200:
                print(f"WARN: org {org} -> HTTP {status}")
                break
            repos.extend(r["full_name"] for r in batch)
            if len(batch) < 100:
                break
            page += 1
    if include_user:
        page = 1
        while True:
            status, batch = github_request(
                f"{GITHUB_API}/user/repos?per_page=100&page={page}&affiliation=owner",
                token,
            )
            if status != 200:
                print(f"WARN: user repos -> HTTP {status}")
                break
            repos.extend(r["full_name"] for r in batch)
            if len(batch) < 100:
                break
            page += 1
    seen = set()
    unique = []
    for repo in repos:
        if repo not in seen:
            seen.add(repo)
            unique.append(repo)
    return sorted(unique)


def fetch_agents_md(token, full_name):
    status, meta = github_request(
        f"{GITHUB_API}/repos/{full_name}/contents/AGENTS.md", token
    )
    if status == 404:
        return None, None, None
    if status != 200:
        return None, None, f"HTTP {status}"
    content = base64.b64decode(meta["content"]).decode("utf-8-sig", errors="replace")
    return normalize(content), meta.get("sha"), None


def fix_agents_md(token, full_name, master_text, file_sha, default_branch):
    payload = {
        "message": "chore(rules): sync redirector [kuro central guard]",
        "content": base64.b64encode(master_text.encode("utf-8")).decode(),
        "branch": default_branch,
    }
    if file_sha:
        payload["sha"] = file_sha
    status, _ = github_request(
        f"{GITHUB_API}/repos/{full_name}/contents/AGENTS.md",
        token,
        method="PUT",
        payload=payload,
    )
    return status


def write_report(audit):
    REPORTS_DIR.mkdir(exist_ok=True)
    date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    path = REPORTS_DIR / f"rules_audit_{date}.json"
    path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nRapport : {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["local", "remote"])
    parser.add_argument("--apply", action="store_true",
                        help="corrige automatiquement les repos en retard")
    args = parser.parse_args()

    master = load_master()
    expected_count = rule_count(master)

    results = []
    fixed = []

    if args.mode == "local":
        for name in local_projects():
            agents = DOCS_DIR / name / "AGENTS.md"
            if not agents.exists():
                results.append({"repo": name, "status": "missing_agents"})
                continue
            current = normalize(agents.read_text(encoding="utf-8-sig"))
            if current == master:
                results.append({"repo": name, "status": "ok"})
                continue
            entry = {
                "repo": name,
                "status": "stale",
                "ruleCount": rule_count(current),
                "expectedRuleCount": expected_count,
            }
            if args.apply:
                agents.write_text(master, encoding="utf-8", newline="\n")
                entry["fixed"] = True
                fixed.append(name)
            results.append(entry)
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("GH_TOKEN ou GITHUB_TOKEN requis en mode remote")
        orgs = [o.strip() for o in os.environ.get("KURO_GH_ORGS", "").split(",") if o.strip()]
        repos = list_remote_repos(token, orgs, include_user=True)
        print(f"{len(repos)} repos enumeres.")
        for full_name in repos:
            status_code, meta = github_request(f"{GITHUB_API}/repos/{full_name}", token)
            if status_code != 200:
                results.append({"repo": full_name, "status": f"meta_http_{status_code}"})
                continue
            default_branch = meta.get("default_branch", "main")
            archived = meta.get("archived", False)
            content, file_sha, error = fetch_agents_md(token, full_name)
            if error:
                results.append({"repo": full_name, "status": error})
                continue
            if content is None:
                if archived:
                    results.append({"repo": full_name, "status": "archived_no_agents"})
                    continue
                results.append({"repo": full_name, "status": "missing_agents"})
                continue
            if content == master:
                results.append({"repo": full_name, "status": "ok"})
                continue
            entry = {
                "repo": full_name,
                "status": "archived_stale" if archived else "stale",
                "ruleCount": rule_count(content),
                "expectedRuleCount": expected_count,
            }
            if args.apply and not archived:
                code = fix_agents_md(
                    token, full_name, master, file_sha, default_branch
                )
                entry["fixed"] = code in (200, 201)
                if entry["fixed"]:
                    fixed.append(full_name)
            results.append(entry)

    ok = sum(1 for r in results if r["status"] == "ok")
    stale = [r for r in results if str(r["status"]).startswith(("stale", "missing"))]
    audit = {
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
        "mode": args.mode,
        "applied": bool(args.apply),
        "masterRuleCount": expected_count,
        "totalChecked": len(results),
        "ok": ok,
        "staleOrMissing": len(stale),
        "fixed": fixed,
        "results": results,
    }

    print(f"\n=== KURO RULES GUARD ({args.mode}) ===")
    print(f"Repos OK          : {ok}/{len(results)}")
    print(f"En retard/absents : {len(stale)}")
    if fixed:
        print(f"Corriges          : {', '.join(fixed)}")
    for entry in stale[:15]:
        extra = (
            f" ({entry.get('ruleCount')}/{entry.get('expectedRuleCount')} regles)"
            if "ruleCount" in entry
            else ""
        )
        print(f"  STALE {entry['repo']}{extra}")

    write_report(audit)
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
