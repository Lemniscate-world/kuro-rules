#!/usr/bin/env python3
"""ci_guardian.py — CI Guardian: surveillance + auto-fix des workflows GitHub Actions.

Découvre automatiquement tous les repos des comptes spécifiés (hors forks/archivés),
surveille le dernier run de chaque workflow (branche par défaut), tente une remédiation
automatique sur les échecs et publie:
    - un statut JSON (ci-status.json) consommé par le portfolio Lemniscate-world
    - un bloc auto-généré dans le README du profil personnel (marqueurs CI-GUARDIAN)

Remédiation automatique:
    - échec au 1er essai (run_attempt == 1)  -> relance des jobs échoués (rerun-failed-jobs)
    - échec persistant (run_attempt >= 2)    -> ouvre/met à jour une issue de suivi (label: ci-guardian)

Usage:
    python scripts/ci_guardian.py [--owners LambdaSection Lemniscate-world]
                                  [--repos owner/repo ...] [--output ci-status.json]
                                  [--readme path/README.md] [--token TOKEN] [--dry-run]

Résolution du token: --token > $CI_GUARDIAN_TOKEN > $GH_TOKEN > $GITHUB_TOKEN.
Sans token: lecture seule (repos publics), aucun rerun ni issue.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://api.github.com"
GUARDIAN_LABEL = "ci-guardian"
DEFAULT_OWNERS = ["LambdaSection", "Lemniscate-world"]
START_MARK = "<!-- CI-GUARDIAN:START"
END_MARK = "<!-- CI-GUARDIAN:END -->"


def api(method: str, path: str, token: str | None = None, payload: dict | None = None) -> tuple[int, dict | list | None]:
    url = path if path.startswith("http") else f"{API_BASE}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("User-Agent", "kuro-ci-guardian")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode()
            return resp.status, json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        try:
            return exc.code, json.loads(body) if body else None
        except json.JSONDecodeError:
            return exc.code, {"message": body}


def resolve_token(cli_token: str | None) -> str | None:
    if cli_token:
        return cli_token
    for env_name in ("CI_GUARDIAN_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        value = os.environ.get(env_name)
        if value:
            return value
    return None


def discover_repos(owner: str, token: str | None) -> list[str]:
    """Tous les repos actifs du compte (forks/archivés/désactivés exclus)."""
    status, data = api("GET", f"/users/{owner}/repos?per_page=100&sort=pushed", token)
    if status != 200 or not isinstance(data, list):
        status, data = api("GET", f"/orgs/{owner}/repos?per_page=100&sort=pushed", token)
    if status != 200 or not isinstance(data, list):
        print(f"  WARN: impossible de lister les repos de {owner} (HTTP {status})")
        return []
    return sorted(
        f"{owner}/{r['name']}"
        for r in data
        if not r.get("archived") and not r.get("fork") and not r.get("disabled")
    )


def default_branch(repo: str, token: str | None) -> str | None:
    status, data = api("GET", f"/repos/{repo}", token)
    if status != 200 or not isinstance(data, dict):
        return None
    return data.get("default_branch")


def latest_workflow_runs(repo: str, token: str | None) -> list[dict]:
    """Dernier run par workflow, branche par défaut uniquement."""
    branch = default_branch(repo, token)
    if not branch:
        return []
    status, data = api("GET", f"/repos/{repo}/actions/runs?per_page=100", token)
    if status != 200 or not isinstance(data, dict):
        return []
    latest: dict[str, dict] = {}
    for run in data.get("workflow_runs", []):
        if run.get("head_branch") != branch:
            continue
        name = run.get("name") or "unknown"
        current = latest.get(name)
        if current is None or run.get("run_number", 0) > current.get("run_number", 0):
            latest[name] = run
    return sorted(latest.values(), key=lambda r: r.get("created_at") or "", reverse=True)


def rerun_failed_jobs(repo: str, run_id: int, token: str | None) -> bool:
    status, _ = api("POST", f"/repos/{repo}/actions/runs/{run_id}/rerun-failed-jobs", token)
    return status in (201, 202)


def open_issue(repo: str, title: str, body: str, token: str | None) -> int | None:
    status, data = api(
        "POST",
        f"/repos/{repo}/issues",
        token,
        {"title": title, "body": body, "labels": [GUARDIAN_LABEL]},
    )
    if status == 201 and isinstance(data, dict):
        return data.get("number")
    return None


def comment_issue(repo: str, issue_number: int, body: str, token: str | None) -> bool:
    status, _ = api(
        "POST",
        f"/repos/{repo}/issues/{issue_number}/comments",
        token,
        {"body": body},
    )
    return status == 201


def find_open_issue(repo: str, workflow: str, token: str | None) -> int | None:
    status, data = api(
        "GET",
        f"/repos/{repo}/issues?labels={GUARDIAN_LABEL}&state=open&per_page=50",
        token,
    )
    if status != 200 or not isinstance(data, list):
        return None
    prefixes = (f"[Kuro Sentinel] {workflow}", f"[CI Guardian] {workflow}")
    for issue in data:
        title = issue.get("title", "")
        if any(title.startswith(p) for p in prefixes) and "pull_request" not in issue:
            return issue.get("number")
    return None


def remediate(repo: str, run: dict, token: str | None, dry_run: bool) -> dict:
    name = run.get("name") or "unknown"
    attempt = run.get("run_attempt", 1)
    run_id = run.get("id")
    run_url = run.get("html_url", "")
    action = {"repo": repo, "workflow": name, "action": "none", "detail": ""}

    if attempt <= 1:
        if dry_run:
            action.update(action="rerun_would_trigger", detail=f"dry-run: rerun run {run_id}")
            return action
        if not token:
            action.update(action="skipped_no_token", detail="token requis pour relancer")
            return action
        ok = rerun_failed_jobs(repo, run_id, token)
        if ok:
            action.update(
                action="rerun_triggered",
                detail=f"relance jobs échoués (run {run_id}, tentative {attempt})",
            )
            return action
        action.update(
            action="rerun_failed",
            detail=f"relance impossible (run {run_id}) — escalade en issue de suivi",
        )

    title = f"[Kuro Sentinel] {name} en échec persistant"
    body = (
        f"Le workflow **{name}** du repo `{repo}` échoue de façon persistante.\n\n"
        f"- Run: {run_url}\n"
        f"- Tentatives: {attempt}\n"
        f"- Détecté: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"_Issue maintenue à jour automatiquement par le CI Guardian._"
    )
    if dry_run:
        action.update(action="issue_would_open", detail=f"dry-run: issue '{title}'")
        return action
    if not token:
        action.update(action="skipped_no_token", detail="token requis pour ouvrir une issue")
        return action
    existing = find_open_issue(repo, name, token)
    if existing:
        ok = comment_issue(repo, existing, f"Nouvel échec confirmé ({attempt} tentatives): {run_url}", token)
        action.update(
            action="issue_updated" if ok else "comment_failed",
            detail=f"issue #{existing} mise à jour",
        )
    else:
        number = open_issue(repo, title, body, token)
        action.update(
            action="issue_opened" if number else "issue_failed",
            detail=f"issue #{number}" if number else "création issue impossible",
        )
    return action


def guard(repos: list[str], token: str | None, dry_run: bool) -> dict:
    report_repos = []
    no_ci = []
    actions = []
    for repo in repos:
        runs = latest_workflow_runs(repo, token)
        if not runs:
            no_ci.append(repo)
            continue
        workflows = []
        health = "green"
        for run in runs:
            conclusion = run.get("conclusion")
            workflows.append(
                {
                    "name": run.get("name") or "unknown",
                    "status": run.get("status"),
                    "conclusion": conclusion,
                    "attempt": run.get("run_attempt", 1),
                    "url": run.get("html_url", ""),
                    "updated_at": run.get("updated_at") or run.get("created_at"),
                }
            )
            if conclusion == "failure":
                health = "red"
                actions.append(remediate(repo, run, token, dry_run))
        report_repos.append({"name": repo, "health": health, "workflows": workflows})
    overall = "red" if any(r["health"] == "red" for r in report_repos) else "green"
    report_repos.sort(key=lambda r: (r["health"] != "red", r["name"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "overall": overall,
        "repos": report_repos,
        "no_ci": no_ci,
        "actions": actions,
    }


def readme_block(report: dict) -> str:
    total_wf = sum(len(r["workflows"]) for r in report["repos"])
    ok_wf = sum(1 for r in report["repos"] for w in r["workflows"] if w["conclusion"] == "success")
    lines = [
        f"{START_MARK} auto-généré par kuro-rules/ci_guardian.py — ne pas éditer",
        "",
        "## Intégration continue — état des repos",
        "",
        f"Scan du {report['generated_at']} · **{ok_wf}/{total_wf} checks verts** · "
        f"{len(report['no_ci'])} repo(s) sans CI · "
        f"[Dashboard](https://lemniscate-world.github.io/Lemniscate-world/)",
        "",
        "| Repo | CI | Détail |",
        "|------|----|--------|",
    ]
    for r in report["repos"]:
        repo_dot = "🟢" if r["health"] == "green" else "🔴"
        failing = [w["name"] for w in r["workflows"] if w["conclusion"] == "failure"]
        detail = ", ".join(failing) if failing else f"{len(r['workflows'])} workflow(s) OK"
        url = f"https://github.com/{r['name']}/actions"
        lines.append(f"| [{r['name']}]({url}) | {repo_dot} | {detail} |")
    lines += ["", END_MARK]
    return "\n".join(lines)


def inject_readme(path: Path, report: dict) -> bool:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    block = readme_block(report)
    if START_MARK in text and END_MARK in text:
        head = text.split(START_MARK, 1)[0]
        tail = text.split(END_MARK, 1)[1]
        new_text = head + block + tail
    else:
        new_text = text.rstrip() + "\n\n" + block + "\n"
    if new_text == text:
        return False
    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="CI Guardian — surveillance + auto-fix GitHub Actions")
    parser.add_argument("--owners", nargs="+", default=DEFAULT_OWNERS, help="comptes dont tous les repos sont surveillés")
    parser.add_argument("--repos", nargs="+", default=None, help="liste explicite de repos (désactive la découverte)")
    parser.add_argument("--output", default=None, help="chemin du ci-status.json à écrire")
    parser.add_argument("--readme", default=None, help="README du profil à mettre à jour (bloc CI Guardian)")
    parser.add_argument("--token", default=None, help="token GitHub (sinon variables d'env)")
    parser.add_argument("--dry-run", action="store_true", help="aucune écriture externe, statut seulement")
    args = parser.parse_args()

    token = resolve_token(args.token)
    repos = args.repos if args.repos else []
    if not repos:
        for owner in args.owners:
            found = discover_repos(owner, token)
            print(f"DISCOVER {owner}: {len(found)} repos actifs")
            repos.extend(found)

    report = guard(repos, token, args.dry_run)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    if args.readme and not args.dry_run:
        if inject_readme(Path(args.readme), report):
            print(f"README updated: {args.readme}")
        else:
            print("README unchanged")

    monitored = len(report["repos"])
    failing = sum(1 for r in report["repos"] if r["health"] == "red")
    print(f"CI GUARDIAN: overall={report['overall']} repos_with_ci={monitored} repos_failing={failing} repos_no_ci={len(report['no_ci'])}")
    for r in report["repos"]:
        state = "RED" if r["health"] == "red" else "GREEN"
        print(f"  [{state}] {r['name']}: {len(r['workflows'])} workflows")
        for wf in r["workflows"]:
            if wf["conclusion"] == "failure":
                print(f"         FAIL: {wf['name']}")
    for act in report["actions"]:
        print(f"  ACTION: {act['repo']} / {act['workflow']} -> {act['action']} ({act['detail']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
