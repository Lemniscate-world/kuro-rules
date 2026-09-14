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
    discover_all,
    fetch_failed_log,
    rerun_failed_jobs,
)

import kuro_proposals as P  # noqa: E402

SAFE_KLASSES = {"formatting", "protected_files", "lint_dead"}
PROTECTED_REFS = {"main", "master"}
AUTO_LABEL = "kuro-auto"
VALIDE_LABEL = "valide"
MERGE_MAX_ADD = 400
TRUSTED_MERGE_AUTHORS = {"Lemniscate-world", "github-actions[bot]"}
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


def review_comments(repo: str, number: int, token: str) -> list:
    """Commentaires inline de revue postes par des bots (Qodo, Sourcery, CodeRabbit...)."""
    st, data = api("GET", f"/repos/{repo}/pulls/{number}/comments?per_page=100", token)
    if st != 200 or not isinstance(data, list):
        return []
    out = []
    for c in data:
        if not isinstance(c, dict):
            continue
        author = ((c.get("user") or {}).get("login") or "")
        if not author.endswith("[bot]") or author in ("github-actions[bot]", "dependabot[bot]"):
            continue
        if MARKER in (c.get("body") or ""):
            continue
        out.append(c)
    return out


def parse_suggestions(body: str) -> list:
    """Extrait les blocs ```suggestion -> [lignes de remplacement]."""
    return [m.group(1).strip("\n").splitlines()
            for m in re.finditer(r"```suggestion[^\n]*\n(.*?)```", body or "", re.DOTALL)
            if m.group(1).strip()]


def suggestion_range(comment: dict) -> tuple:
    """Lignes 1-indexees ciblees : (debut, fin), (0, 0) si inexploitable."""
    start = comment.get("start_line") or comment.get("original_start_line") or \
        comment.get("line") or comment.get("original_line") or 0
    end = comment.get("line") or comment.get("original_line") or start
    try:
        start, end = int(start), int(end)
    except (TypeError, ValueError):
        return 0, 0
    if start < 1 or end < start:
        return 0, 0
    return start, end


def apply_suggestion(repo_dir: Path, path: str, start: int, end: int, code: list) -> bool:
    """Remplace les lignes [start..end] par le bloc suggestion. False si inapplicable."""
    target = repo_dir / path
    if not code or start < 1 or end < start or target.suffix != ".py":
        return False
    try:
        if target.resolve().parent != repo_dir.resolve() and \
                repo_dir.resolve() not in target.resolve().parents:
            return False
        lines = target.read_text(encoding="utf-8").splitlines()
    except Exception:
        return False
    if end > len(lines):
        return False
    new_text = "\n".join(lines[:start - 1] + code + lines[end:]) + "\n"
    try:
        compile(new_text, str(target), "exec")
        target.write_text(new_text, encoding="utf-8")
    except Exception:
        return False
    return True


def post_comment(repo: str, number: int, body: str, token: str) -> bool:
    if not P.budget_use("comment"):
        print("  budget commentaires epuise pour aujourd'hui")
        return False
    st, _ = api("POST", f"/repos/{repo}/issues/{number}/comments", token, {"body": body})
    return st in (200, 201)


def pr_labels(pr: dict) -> set:
    return {l.get("name") for l in (pr.get("labels") or [])
            if isinstance(l, dict) and l.get("name")}


def ensure_label(repo: str, name: str, color: str, token: str) -> None:
    st, _ = api("GET", f"/repos/{repo}/labels/{name}", token)
    if st != 200:
        api("POST", f"/repos/{repo}/labels", token,
            {"name": name, "color": color, "description": "Pilotage Kuro (Discord)"})


def add_pr_label(repo: str, number: int, name: str, token: str) -> bool:
    st, _ = api("POST", f"/repos/{repo}/issues/{number}/labels", token, {"labels": [name]})
    return st in (200, 201)


def pr_files_stat(repo: str, number: int, token: str) -> str:
    st, data = api("GET", f"/repos/{repo}/pulls/{number}/files?per_page=10", token)
    if st != 200 or not isinstance(data, list) or not data:
        return ""
    added = sum(f.get("additions", 0) for f in data if isinstance(f, dict))
    deleted = sum(f.get("deletions", 0) for f in data if isinstance(f, dict))
    names = ", ".join(f.get("filename", "") for f in data[:3] if isinstance(f, dict))
    more = f" +{len(data) - 3} fichiers" if len(data) > 3 else ""
    return f"+{added}/-{deleted} : {names}{more}"


def pr_commands(repo: str, pr: dict, token: str) -> list:
    out = []
    st, data = api("GET", f"/repos/{repo}/issues/{pr.get('number')}/comments?per_page=30", token)
    if st != 200 or not isinstance(data, list):
        return out
    for c in data:
        if not isinstance(c, dict):
            continue
        author = ((c.get("user") or {}).get("login") or "")
        if not author or author.endswith("[bot]"):
            continue
        m = re.match(r"/(valide|relance|diagnostic)\s*(\S+)?", (c.get("body") or "").strip())
        if m:
            out.append({"id": c.get("id"), "author": author,
                        "cmd": m.group(1), "arg": m.group(2) or ""})
    return out


def graphql(token: str, query: str, variables: dict) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "Kuro/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"GraphQL echec : {e}")
        return {}


def fixable_push(repo: str, pr: dict, klass: str, detail: str, log: str, token: str,
                 write: bool, allowed: bool) -> str:
    """Push autofix sur la branche PR si label kuro-auto/valide, sinon P-ID d'attente."""
    head = (pr.get("head") or {}).get("ref", "?")
    number = pr.get("number")
    if klass not in SAFE_KLASSES:
        return "classe non auto-reparable"
    fork = bool(((pr.get("head") or {}).get("repo") or {}).get("fork"))
    if fork:
        return "fork : push refuse, commentaire seul"
    if not allowed:
        pid = P.add(f"{repo}#{number}", f"[{klass}] {detail[:80]}",
                    f"En attente du label `{AUTO_LABEL}` sur la PR (validez depuis Discord).",
                    [f"https://github.com/{repo}/pull/{number}"])
        return f"proposition {pid} (label {AUTO_LABEL} requis)"
    if not write:
        return f"dry-run : {klass} serait pousse sur {head}"
    if not P.budget_use("autofix_push"):
        return "budget autofix du jour epuise (3/j)"
    res = auto_fix(repo, klass, detail, log, token, False, head_branch=head)
    return res.get("detail", res.get("action", "?"))


def propose(repo: str, pr: dict, check: dict, diag: dict | None,
            run_id: int | None, token: str, write: bool) -> str:
    """P-ID + diagnostic LLM en commentaire (dedup par run)."""
    number = pr.get("number")
    cause = (diag or {}).get("cause", "cause inconnue") if diag else "cause inconnue"
    fix = (diag or {}).get("fix", "") if diag else ""
    files = pr_files_stat(repo, number, token)
    pid = P.add(f"{repo}#{number}/{check.get('name')}", f"{check.get('name')} : {cause[:80]}",
                f"{fix[:300]} | Fichiers : {files}",
                [check.get("html_url", ""), f"https://github.com/{repo}/pull/{number}"])
    if run_id and already_commented(repo, number, run_id, token):
        return f"proposition {pid} deja postee pour ce run"
    text = ai_diagnose(repo, run_id, token) if run_id else None
    body = (
        f"{MARKER} run={run_id}\n"
        f"**Kuro PR-agent {pid}** — `{check.get('name')}` en echec.\n\n"
        f"Cause : {cause}\n\n"
        f"{text or '_Diagnostic LLM indisponible — diagnostic deterministe seul._'}\n\n"
        f"Fichiers : {files or 'n/a'}\n\n"
        f"[Voir le run]({check.get('html_url', '')}) · "
        f"Validez avec `/valide {pid}` (auteur PR) ou le label `{AUTO_LABEL}`."
    )
    if not write:
        return f"dry-run : {pid} non postee"
    return f"{pid} postee" if post_comment(repo, number, body, token) else f"{pid} : post impossible"


def handle_commands(repo: str, pr: dict, token: str, write: bool) -> list[str]:
    """Execute UNE commande /valide /relance /diagnostic (auteur PR, sauf diagnostic)."""
    lines, number = [], pr.get("number")
    author = ((pr.get("user") or {}).get("login") or "")
    for cmd in pr_commands(repo, pr, token):
        key = f"cmd:{repo}#{number}:{cmd['id']}"
        if P.seen(key):
            continue
        if cmd["cmd"] == "diagnostic":
            if not write:
                lines.append("diagnostic : dry-run, ignore");
            else:
                failing = failing_checks(repo, (pr.get("head") or {}).get("sha", ""), token)
                rid = run_id_from_url((failing[0].get("html_url", "") if failing else ""))
                text = ai_diagnose(repo, rid, token) if rid else None
                ok = post_comment(repo, number, f"{MARKER}\n**Diagnostic** :\n\n{text or 'rien a diagnostiquer.'}", token)
                lines.append(f"diagnostic -> {'poste' if ok else 'echec post'}")
            P.mark_seen(key)
            break
        if cmd["author"] != author:
            continue  # /valide et /relance reserves a l'auteur de la PR
        if cmd["cmd"] == "relance":
            rid = None
            failing = failing_checks(repo, (pr.get("head") or {}).get("sha", ""), token)
            if failing:
                rid = run_id_from_url(failing[0].get("html_url", ""))
            if rid and write and rerun_failed_jobs(repo, rid, token):
                lines.append(f"relance -> run {rid} relance")
            else:
                lines.append("relance -> impossible (dry-run ou aucun run)")
            P.mark_seen(key)
            break
        if cmd["cmd"] == "valide":
            pid = cmd["arg"]
            if write and P.set_status(pid, "valide"):
                ensure_label(repo, AUTO_LABEL, "0e8a16", token)
                add_pr_label(repo, number, AUTO_LABEL, token)
                post_comment(repo, number, f"{MARKER}\n{pid} validee : label `{AUTO_LABEL}` pose, l'agent applique au prochain cycle.", token)
                lines.append(f"valide -> {pid} validee")
            else:
                lines.append(f"valide -> {pid} inconnue ou dry-run")
            P.mark_seen(key)
            break
    return lines


def maybe_automerge(repo: str, pr: dict, token: str, write: bool) -> str | None:
    """Auto-merge garde : label valide + tout vert + petite diff + auteur de confiance."""
    labels = pr_labels(pr)
    if VALIDE_LABEL not in labels and AUTO_LABEL not in labels:
        return None
    if "do-not-merge" in labels:
        return "merge refuse (do-not-merge)"
    author = ((pr.get("user") or {}).get("login") or "")
    if author not in TRUSTED_MERGE_AUTHORS:
        return f"merge refuse (auteur {author or '?'} non approuve)"
    if (pr.get("additions") or 0) > MERGE_MAX_ADD:
        return f"merge refuse (diff +{pr.get('additions')} > {MERGE_MAX_ADD})"
    failing = failing_checks(repo, (pr.get("head") or {}).get("sha", ""), token)
    if failing:
        return f"merge refuse ({len(failing)} check(s) rouges)"
    if not write:
        return "dry-run : merge envisageable (tout vert + label)"
    if not P.budget_use("merge"):
        return "merge refuse (budget 1/j epuise)"
    node = pr.get("node_id", "")
    res = graphql(token, "mutation($id: ID!) { enablePullRequestAutoMerge("
                  "input: {pullRequestId: $id, mergeMethod: SQUASH}) { clientMutationId } }",
                  {"pullRequestId": node})
    if res.get("data", {}).get("enablePullRequestAutoMerge") is not None:
        return "auto-merge active (squash)"
    return "auto-merge impossible (etat GitHub)"


def apply_review_fixes(repo: str, pr: dict, token: str, write: bool, allowed: bool) -> list[str]:
    """Applique les blocs suggestion des bots (Qodo/Sourcery/Rabbit) ou les propose."""
    from ci_guardian import _git
    import shutil
    import tempfile
    number, head = pr.get("number"), (pr.get("head") or {}).get("ref", "?")
    comments = [c for c in review_comments(repo, number, token)
                if parse_suggestions(c.get("body") or "")]
    if not comments:
        others = review_comments(repo, number, token)
        if others and write:
            pid = P.add(f"{repo}#{number}", f"{len(others)} remarque(s) bot sans suggestion",
                        "Avis a lire : " + "; ".join(
                            f"{(c.get('user') or {}).get('login')}:{c.get('path')}" for c in others[:5]),
                        [f"https://github.com/{repo}/pull/{number}/files"])
            return [f"revue bots : {len(others)} remarque(s) -> proposition {pid}"]
        return []
    if not allowed:
        pid = P.add(f"{repo}#{number}", f"{len(comments)} suggestion(s) bot en attente",
                    f"En attente du label `{AUTO_LABEL}` pour appliquer.",
                    [f"https://github.com/{repo}/pull/{number}/files"])
        return [f"revue bots : {len(comments)} suggestion(s) -> proposition {pid} (label requis)"]
    if not write:
        return [f"revue bots : dry-run, {len(comments)} suggestion(s) applicables"]
    if not P.budget_use("review_fix"):
        return ["revue bots : budget review_fix epuise (2/j)"]
    workdir = Path(tempfile.mkdtemp(prefix="kuro-review-"))
    try:
        url = f"https://x-access-token:{token}@github.com/{repo}.git"
        ok, out = _git(workdir, "clone", "--depth", "5", "--quiet",
                       "--branch", head, url, str(workdir / "repo"))
        if not ok:
            return [f"revue bots : clone impossible ({out[:80]})"]
        rd = workdir / "repo"
        applied, skipped = [], []
        for c in comments[:3]:
            path = c.get("path") or "?"
            start, end = suggestion_range(c)
            codes = parse_suggestions(c.get("body") or "")
            ok_all = bool(codes) and all(apply_suggestion(rd, path, start, end, code) for code in codes)
            (applied if ok_all else skipped).append(path)
        if not applied:
            return [f"revue bots : {len(skipped)} suggestion(s) inapplicables tel quel -> relire a la main"]
        _git(rd, "config", "user.name", "github-actions[bot]")
        _git(rd, "config", "user.email", "github-actions[bot]@users.noreply.github.com")
        _git(rd, "add", "-A")
        _git(rd, "commit", "-m", f"fix(review): applique {len(applied)} suggestion(s) bot ({', '.join(applied[:3])})")
        ok, out = _git(rd, "push", "origin", f"HEAD:{head}")
        if not ok:
            return [f"revue bots : push impossible ({out[:80]})"]
        pid = P.add(f"{repo}#{number}", f"{len(applied)} suggestion(s) bot appliquee(s)",
                    f"Fichiers : {', '.join(applied[:5])}" +
                    (f" | ignores : {', '.join(skipped[:3])}" if skipped else ""),
                    [f"https://github.com/{repo}/pull/{number}/files"])
        P.set_status(pid, "applique")
        msg = f"revue bots : {pid} appliquee ({', '.join(applied[:3])})"
        return [msg + (f" | a relire : {', '.join(skipped[:3])}" if skipped else "")]
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def process_check(repo: str, pr: dict, check: dict, token: str, write: bool, allowed: bool) -> str:
    run_id = run_id_from_url(check.get("html_url", ""))
    log = fetch_failed_log(repo, run_id, token) if run_id else ""
    diag = classify_failure(log) if log else None
    if diag and diag.get("klass") in SAFE_KLASSES:
        outcome = fixable_push(repo, pr, diag["klass"], diag.get("detail", ""), log, token, write, allowed)
        return f"{check.get('name')} [{diag['klass']}] -> {outcome}"
    if diag is None and run_id and run_attempt(repo, run_id, token) <= 1:
        if not write:
            return f"{check.get('name')} [inconnu] -> dry-run : relance envisagee"
        ok = rerun_failed_jobs(repo, run_id, token)
        return f"{check.get('name')} [inconnu] -> {'relance' if ok else 'relance impossible'}"
    outcome = propose(repo, pr, check, diag, run_id, token, write)
    cause = (diag or {}).get("cause", "cause inconnue") if diag else "cause inconnue"
    return f"{check.get('name')} [{cause[:60]}] -> {outcome}"


def process_pr(repo: str, pr: dict, token: str, write: bool) -> list[str]:
    head = (pr.get("head") or {}).get("ref", "?")
    tag = f"{repo}#{pr.get('number')} ({head})"
    if head in PROTECTED_REFS:
        return [f"{tag} : branche protegee, ignore"]
    labels = pr_labels(pr)
    allowed = AUTO_LABEL in labels or VALIDE_LABEL in labels
    lines = [f"{tag}{' [AUTO]' if allowed else ''}"]
    lines.extend(f"  $ {c}" for c in handle_commands(repo, pr, token, write))
    try:
        lines.extend(f"  ~ {c}" for c in apply_review_fixes(repo, pr, token, write, allowed))
    except Exception as e:
        lines.append(f"  ~ revue bots : erreur agent ({e})")
    failing = failing_checks(repo, (pr.get("head") or {}).get("sha", ""), token)
    if not failing:
        auto = maybe_automerge(repo, pr, token, write)
        lines.append(f"  verte" + (f" -> {auto}" if auto else ""))
        return lines
    lines.append(f"  {len(failing)} check(s) rouge(s)")
    for check in failing[:3]:
        try:
            lines.append(f"  - {process_check(repo, pr, check, token, write, allowed)}")
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
    write = a.write and not P.vacances()
    if P.vacances():
        print("mode vacances : lecture seule forcee")
    print(f"=== KURO PR-AGENT write={write} ===")
    lines: list[str] = []
    seen = 0
    found = discover_all(a.owners, token)
    for repo, tok in sorted(found.items()):
        for pr in open_prs(repo, tok):
            if seen >= a.max_prs:
                break
            seen += 1
            lines.extend(process_pr(repo, pr, tok, write))
        if seen >= a.max_prs:
            break
    print("\n".join(lines) or "Aucune PR ouverte.")
    if write:
        pend = P.pending()
        if pend:
            lines.append(f"-- {len(pend)} proposition(s) en attente : " +
                         ", ".join(f"{p['id']} [{p['status']}]" for p in pend[:8]))
        post_discord([P.polish_fr("\n".join(lines))])
    else:
        print("(dry-run : rien pousse ni poste)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
