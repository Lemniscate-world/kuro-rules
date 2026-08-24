#!/usr/bin/env python3
"""ci_guardian.py — CI Guardian: surveillance + auto-fix des workflows GitHub Actions.

Découvre automatiquement tous les repos des comptes spécifiés (hors forks/archivés),
surveille le dernier run de chaque workflow (branche par défaut), tente une remédiation
automatique sur les échecs et publie:
    - un statut JSON (ci-status.json) consommé par le portfolio Lemniscate-world
    - un bloc auto-généré dans le README du profil personnel (marqueurs CI-GUARDIAN)

Remédiation automatique:
    - échec au 1er essai (run_attempt == 1)  -> relance des jobs échoués (rerun-failed-jobs)
    - échec persistant (run_attempt >= 2)    -> auto-diagnostic du log par signatures
      (secret manquant, sous-module fantôme, asserts production, findings bandit,
      dette lint/formatage, dépendances) + issue de suivi avec cause et correctif
    - KURO_AUTO_FIX=1 : réparation automatique poussée sur la branche par défaut
      pour les classes sûres uniquement (format black/isort épinglés au repo,
      fichiers protégés R76). Le reste = diagnostic seul.

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
import re
import subprocess
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
# Runs plus vieux que ça = fantômes (workflow supprimé ou logs expirés) -> ignorés
RUN_MAX_AGE_DAYS = int(os.environ.get("KURO_RUN_MAX_AGE_DAYS", "45"))


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


def run_age_days(run: dict) -> int:
    stamp = run.get("created_at") or ""
    try:
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).days
    except Exception:
        return 0


def latest_workflow_runs(repo: str, token: str | None) -> list[dict]:
    """Dernier run par workflow, branche par défaut, fantômes anciens exclus."""
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
        if run_age_days(run) > RUN_MAX_AGE_DAYS:
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


def failed_steps_summary(repo: str, run_id: int, token: str | None) -> str | None:
    """Liste compacte des jobs/steps en échec d'un run."""
    status, data = api("GET", f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=20", token)
    if status != 200 or not isinstance(data, dict):
        return None
    lines = []
    for job in data.get("jobs", [])[:10]:
        if job.get("conclusion") != "failure":
            continue
        steps = [
            s.get("name")
            for s in job.get("steps", [])
            if s.get("conclusion") == "failure"
        ]
        lines.append(f"- job `{job.get('name')}` échoué aux étapes : {', '.join(steps) or 'n/a'}")
    return "\n".join(lines[:8]) or None


def ai_diagnose(repo: str, run_id: int, token: str | None) -> str | None:
    """Diagnostic LLM du probable root cause. None si aucun moteur dispo."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from kuro_llm import ask
    except Exception:
        return None
    summary = failed_steps_summary(repo, run_id, token)
    if not summary:
        return None
    prompt = (
        f"Le workflow GitHub Actions du repo {repo} (run {run_id}) échoue.\n"
        f"Jobs et étapes en échec :\n{summary}\n\n"
        "En 3-5 puces max : cause probable la plus vraisemblable et correctif à "
        "tenter en premier. Réponds en français, concis, sans préambule."
    )
    return ask(
        prompt,
        system="Tu es ingénieur CI/CD senior du studio lambda-Section. Pragmatique, pas de speculations farfelues.",
    )


# ---------- auto-diagnostic par signatures (cas réels éprouvés) ----------

FAILURE_SIGNATURES: list[tuple[str, str, str, str]] = [
    # (regex sur les logs, cause, commande(s) de réparation, classe auto-fix)
    (
        r"sonar\.token|SONAR_TOKEN|api\.sonarcloud\.io",
        "Secret SONAR_TOKEN absent ou invalide (analyse SonarCloud en 403)",
        "Ajouter le secret SONAR_TOKEN dans les settings du repo, ou passer le job "
        "Sonar en continue-on-error: true",
        "",
    ),
    (
        r"No url found for submodule path '([^']+)'",
        "Sous-module fantôme : gitlink présent sans entrée .gitmodules (casse le checkout)",
        "git rm --cached <chemin> puis gitignore, commit, push",
        "",
    ),
    (
        r"Protected file tracked: (\S+)",
        "Fichier protégé (R76) suivi par git",
        "git rm --cached <fichier> + .gitignore, commit, push",
        "protected_files",
    ),
    (
        r"(?:would reformat|reformatted) .*\.py|black\.{10,}",
        "Dette de formatage (black/isort)",
        "pre-commit run black,isort --all-files (ou black . && isort .), commit, push",
        "formatting",
    ),
    (
        r"flake8\.{10,}|F401|F841|E501.*line too long",
        "Dette de lint flake8 (imports/variables morts, lignes longues)",
        "Corriger les imports/variables morts listés, ou per-file-ignores documenté "
        "dans .flake8 pour la dette legacy",
        "",
    ),
    (
        r"error:.*\[.*\]$|mypy\.{10,}",
        "Erreurs de typage mypy",
        "Corriger les annotations pointées (Optional explicites, annotations dict, "
        "renommages de variables en collision)",
        "",
    ),
    (
        r"assert .+ in (injected|production)|grep -rn \"assert \"",
        "assert en code de production (règle R-compliance)",
        "Remplacer par if not ...: raise ValueError/ SystemExit (hors tests)",
        "",
    ),
    (
        r"\[B\d{3}[ :\]]|bandit.*exit code 1",
        "Findings bandit sévérité medium+",
        "Corriger le code ou ajouter # nosec BXXX avec justification sur la ligne",
        "",
    ),
    (
        r"No module named|ResolutionImpossible|pip.*exit code 1",
        "Dépendance manquante ou incompatible",
        "Vérifier requirements*.txt / l'épinglage, tester l'install en local",
        "",
    ),
]


def classify_failure(log_text: str) -> dict | None:
    """Reconnaît une cause connue dans un extrait de log. None si inconnue."""
    if not log_text:
        return None
    for pattern, cause, fix, klass in FAILURE_SIGNATURES:
        match = re.search(pattern, log_text, re.MULTILINE | re.IGNORECASE)
        if match:
            detail = match.group(1) if match.groups() else ""
            return {
                "cause": cause,
                "fix": fix,
                "auto_fixable": bool(klass),
                "klass": klass or None,
                "detail": detail,
            }
    return None


def fetch_failed_log(repo: str, run_id: int, token: str | None, max_chars: int = 20000) -> str:
    """Concatène la queue des logs des jobs en échec d'un run (texte brut)."""
    status, data = api("GET", f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=20", token)
    if status != 200 or not isinstance(data, dict):
        return ""
    snippets: list[str] = []
    for job in data.get("jobs", [])[:3]:
        if job.get("conclusion") != "failure":
            continue
        try:
            req = urllib.request.Request(
                f"{API_BASE}/repos/{repo}/actions/jobs/{job.get('id')}/logs"
            )
            if token:
                req.add_header("Authorization", f"Bearer {token}")
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            lines = [
                line
                for line in text.splitlines()
                if ("##[error]" in line or "Failed" in line or "error" in line.lower())
            ]
            snippets.append("\n".join(lines[-60:]) or text[-3000:])
        except Exception:
            continue
    return "\n".join(snippets)[-max_chars:]


# ---------- auto-réparation des classes sûres ----------


def _git(repo_dir: Path, *args: str) -> tuple[bool, str]:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    ok = completed.returncode == 0
    return ok, (completed.stdout + completed.stderr).strip()


def auto_fix(repo: str, klass: str, detail: str, log_text: str, token: str, dry_run: bool) -> dict:
    """Applique une réparation sûre et pousse sur la branche par défaut.

    Classes supportées : formatting (black/isort épinglés au repo),
    protected_files (détache du tracking). Toute autre classe = no-op.
    """
    result = {"klass": klass, "action": "autofix_skipped", "detail": ""}
    if klass not in ("formatting", "protected_files"):
        result["detail"] = f"classe {klass} non auto-réparable"
        return result
    if dry_run:
        result["action"] = "autofix_would_run"
        result["detail"] = f"dry-run: {klass} sur {repo}"
        return result

    import shutil
    import tempfile

    workdir = Path(tempfile.mkdtemp(prefix="kuro-autofix-"))
    try:
        url = f"https://x-access-token:{token}@github.com/{repo}.git"
        ok, out = _git(workdir, "clone", "--depth", "5", "--quiet", url, str(workdir / "repo"))
        if not ok:
            result["detail"] = f"clone impossible: {out[:200]}"
            return result
        repo_dir = workdir / "repo"

        if klass == "formatting":
            # Épingler sur les versions du repo pour éviter les cycles de formatage
            pins: dict[str, str] = {}
            config = repo_dir / ".pre-commit-config.yaml"
            if config.exists():
                text = config.read_text(encoding="utf-8", errors="replace")
                for tool, key in (("black", "psf/black"), ("isort", "pycqa/isort")):
                    m = re.search(rf"repo: https://github\.com/{re.escape(key)}\s*\n\s*rev: '?\"?([^'\"\n]+)", text)
                    if m:
                        pins[tool] = m.group(1).strip()
            if "black" not in pins:
                result["detail"] = "pas de révision black épinglée (.pre-commit-config.yaml) - auto-fix refusé"
                return result
            pip_ok = subprocess.run(
                ["pip", "install", "-q", f"black=={pins['black']}"]
                + ([f"isort=={pins['isort']}"] if "isort" in pins else []),
                capture_output=True,
                text=True,
                timeout=300,
            )
            if pip_ok.returncode != 0:
                result["detail"] = f"pip install black=={pins['black']} impossible"
                return result
            subprocess.run(
                ["python", "-m", "black", "--quiet", "."],
                cwd=repo_dir,
                capture_output=True,
                timeout=600,
                check=False,
            )
            if "isort" in pins:
                subprocess.run(
                    ["python", "-m", "isort", "--quiet", "."],
                    cwd=repo_dir,
                    capture_output=True,
                    timeout=300,
                    check=False,
                )
        elif klass == "protected_files":
            tracked = re.findall(r"Protected file tracked: (\S+)", log_text)
            if not tracked:
                result["detail"] = "aucun fichier protégé identifiable dans le log"
                return result
            for f in tracked[:5]:
                _git(repo_dir, "rm", "--cached", "--", f)

        status = _git(repo_dir, "status", "--porcelain")[1].strip()
        if not status:
            result["action"] = "autofix_noop"
            result["detail"] = "aucun changement produit (déjà propre)"
            return result

        _git(repo_dir, "config", "user.name", "github-actions[bot]")
        _git(repo_dir, "config", "user.email", "github-actions[bot]@users.noreply.github.com")
        _git(repo_dir, "add", "-A")
        message = {
            "formatting": "style(ci-guardian): auto-format black/isort (versions épinglées du repo)",
            "protected_files": "fix(R76): retire les fichiers protégés du tracking git",
        }.get(klass, "fix(ci-guardian): auto-réparation")
        _git(repo_dir, "commit", "-m", message)
        branch_ok, branch_out = _git(repo_dir, "rev-parse", "--abbrev-ref", "HEAD")
        branch = branch_out.strip() if branch_ok else "main"
        push_ok, push_out = _git(repo_dir, "push", "origin", f"HEAD:{branch}")
        if push_ok:
            result["action"] = "autofix_pushed"
            result["detail"] = f"poussé sur {branch}: {message}"
        else:
            result["action"] = "autofix_push_failed"
            result["detail"] = push_out[:200]
        return result
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


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
        f"- Détecté: {datetime.now(timezone.utc).isoformat()}\n"
    )

    # Auto-diagnostic par signatures puis auto-réparation des classes sûres
    log_text = fetch_failed_log(repo, run_id, token)
    diag = classify_failure(log_text)
    if diag:
        body += (
            f"\n### Diagnostic automatique\n"
            f"**Cause identifiée** : {diag['cause']}\n\n"
            f"**Correctif** : {diag['fix']}\n"
        )
        if diag.get("detail"):
            body += f"\nDétail : `{diag['detail']}`\n"
        auto_fix_enabled = os.environ.get("KURO_AUTO_FIX", "0") == "1"
        if diag["auto_fixable"] and token and not dry_run and auto_fix_enabled:
            fix_result = auto_fix(repo, diag["klass"], diag.get("detail", ""), log_text, token, dry_run)
            body += f"\n**Auto-réparation** : {fix_result['action']} — {fix_result['detail']}\n"
            action.update(
                action=fix_result["action"],
                detail=f"{diag['cause'][:80]} | {fix_result['detail'][:120]}",
            )
        elif diag["auto_fixable"]:
            body += (
                "\n_Auto-réparation disponible pour cette classe "
                "(activez KURO_AUTO_FIX=1)._\n"
            )
    else:
        analysis = ai_diagnose(repo, run_id, token)
        if analysis:
            body += f"\n### Analyse IA (indicative)\n{analysis}\n"

    body += "\n_Issue maintenue à jour automatiquement par le robot Kuro._"
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
    parser.add_argument("--readme", default=None, help="README du profil à mettre à jour (bloc CI)")
    parser.add_argument("--actions-log", default=None, help="journal versionné des actions")
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
    if not args.dry_run:
        write_actions_log(Path(args.actions_log) if args.actions_log else None, report)
    notify_discord(report)
    return 0


ACTION_ICONS = {
    "rerun_triggered": "relance",
    "issue_opened": "issue créée",
    "issue_updated": "issue mise à jour",
    "issue_would_open": "issue (dry-run)",
    "rerun_would_trigger": "relance (dry-run)",
}


def render_actions_md(report: dict) -> str:
    """Journal lisible : 1 ligne par action + ligne de synthèse du scan."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    lines = [f"- {ts} | scan {report['overall']} | "
             f"{sum(len(r['workflows']) for r in report['repos'])} checks, "
             f"{sum(1 for r in report['repos'] if r['health'] == 'red')} repo(s) rouge(s)"]
    for act in report["actions"]:
        if act["action"] == "none":
            continue
        icon = ACTION_ICONS.get(act["action"], act["action"])
        lines.append(f"  - {ts} | {act['action']} ({icon}) | {act['repo']} / {act['workflow']} | {act['detail']}")
    return "\n".join(lines)


def write_actions_log(path: Path | None, report: dict) -> None:
    """Append au journal versionné + résumé GitHub Step Summary."""
    entry = render_actions_md(report)
    print(entry)
    if path:
        header = "" if path.exists() else (
            "# Journal des actions Kuro\n\n"
            "Chaque scan ajoute une ligne de synthèse ; chaque auto-action est détaillée.\n\n"
        )
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(header + entry + "\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        try:
            with open(summary, "a", encoding="utf-8") as fh:
                fh.write("### 🤖 Actions Kuro Sentinel\n\n```\n" + entry + "\n```\n")
        except Exception:
            pass


def notify_discord(report: dict) -> None:
    """Alerte Discord si des checks sont rouges ou si des actions ont été tentées."""
    if report["overall"] != "red" and not report["actions"]:
        return
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        print("Discord: DISCORD_WEBHOOK_URL absent - alerte ignoree")
        return
    failing = [r for r in report["repos"] if r["health"] == "red"]
    lines = [f"**{len(failing)} repo(s) en échec CI**"]
    for r in failing:
        names = ", ".join(w["name"] for w in r["workflows"] if w["conclusion"] == "failure")
        lines.append(f"- `{r['name']}` : {names}")
    for act in report["actions"]:
        if act["action"] in ("rerun_triggered", "issue_opened", "issue_updated"):
            lines.append(f"Action : {act['action']} sur `{act['repo']}` / {act['workflow']}")
    payload = {
        "username": "Kuro",
        "embeds": [
            {
                "title": "[ALERTE] Intégration continue",
                "description": "\n".join(lines)[:1900],
                "color": 15158332,
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


if __name__ == "__main__":
    sys.exit(main())
