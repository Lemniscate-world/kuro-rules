#!/usr/bin/env python3
"""kuro_autosync — toute mise à jour locale part seule sur le serveur.

Surveille le dépôt et, à chaque passage (tâche planifiée toutes les 20 min
+ appel manuel), commite + pousse la branche courante vers origin si :
  - des fichiers suivis ont changé dans le périmètre code/config/doc ;
  - aucun fichier protégé R76 (.env, clés, credentials) n'est en jeu ;
  - aucun secret apparent R101 n'est dans le diff ;
  - les gardes qualité passent (ruff + slice pytest TUI), sauf --no-gate.

Fichiers du bot quotidien (TRUTH_DAILY.md, tasks_anydo.json, outputs/, …)
restent au workflow kuro.yml : l'autosync les ignore toujours.
Jamais de push sur main/master sans --allow-main. Échec fermé : on journalise
dans logs/autosync.log et on ne pousse rien de cassé.

Usage :
    python scripts/kuro_autosync.py [--dry-run] [--no-gate] [--allow-main]
Côté serveur (pull auto, cron Linux) :
    */15 * * * * cd ~/kuro-rules && git pull --ff-only -q
"""

from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Périmètre autosync : code, tests, tooling, CI, docs techniques.
ALLOW_DIRS = ("src/", "tests/", "scripts/", ".github/", "docs/", "rules/", "prompts/", "templates/",
              "dashboard/")
ALLOW_FILES = ("pyproject.toml", ".pre-commit-config.yaml", ".sonarcloud.properties",
               "AGENTS.md", "README.md")
# Écrits par le bot kuro.yml : jamais touchés ici (conflits garantis sinon).
BOT_OWNED = (
    "TRUTH_DAILY.md", "tasks_anydo.json", "ci-status.json", "skills.json",
    "KURO_ACTIONS_LOG.md", "outputs/", "security-status.json", "coverage.local.json",
)
# R76 : fichiers protégés, refus bloquant même s'ils sont déjà suivis.
PROTECTED_RE = re.compile(
    r"((^|/)(PLAN|SESSION_SUMMARY|acquisition_tracker|decision-memo|LAUNCH_POSTS|decision)\.md$"
    r"|(^|/)\.env$|credentials\.json$|service_account.*\.json$|\.pem$|\.key$|\.p12$)"
)
# R101 : scan best-effort des secrets dans le diff stagé.
SECRET_RE = re.compile(r"(api_key|apikey|secret|password)\s*=\s*['\"]\w{8,}", re.IGNORECASE)


def _git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def current_branch() -> str:
    out = _git("rev-parse", "--abbrev-ref", "HEAD")
    return out.stdout.strip()


def changed_files() -> list[str]:
    """Suivis modifiés + nouveaux non ignorés. Set dédupliqué."""
    out = _git("status", "--porcelain")
    files: list[str] = []
    for line in out.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip().strip('"')
        if " -> " in path:  # renommé : prend la destination
            path = path.split(" -> ", 1)[1].strip()
        if path:
            files.append(path)
    others = _git("ls-files", "--others", "--exclude-standard")
    files.extend(f for f in others.stdout.splitlines() if f.strip())
    return sorted(set(files))


def classify(paths: list[str]) -> tuple[list[str], list[str]]:
    """Sépare (à synchroniser, ignorés). Pur, testable."""
    ok, skipped = [], []
    for p in paths:
        posix = p.replace(os.sep, "/")
        if posix in BOT_OWNED or any(posix == b or posix.startswith(b) for b in BOT_OWNED if b.endswith("/")):
            skipped.append(p)
            continue
        if posix.startswith(ALLOW_DIRS) or posix in ALLOW_FILES:
            ok.append(p)
        else:
            skipped.append(p)
    return ok, skipped


def refusal_reasons(branch: str, staged: list[str], diff_text: str, allow_main: bool) -> list[str]:
    """Motifs de refus bloquants. Pur, testable."""
    reasons = []
    if branch in ("main", "master") and not allow_main:
        reasons.append(f"branche protégée {branch} (--allow-main requis)")
    bad = [p for p in staged if PROTECTED_RE.search(p.replace(os.sep, "/"))]
    if bad:
        reasons.append(f"fichiers protégés R76 : {bad}")
    if SECRET_RE.search(diff_text):
        reasons.append("secret apparent R101 dans le diff")
    conflict = _git("ls-files", "--unmerged")
    if conflict.stdout.strip():
        reasons.append("conflits de fusion non résolus")
    return reasons


def run_gates(py_files: list[str]) -> tuple[bool, str]:
    """ruff + slice pytest TUI. True si OK."""
    if py_files:
        ruff = subprocess.run(
            [sys.executable, "-m", "ruff", "check", *py_files],
            cwd=REPO, capture_output=True, text=True, timeout=180,
        )
        if ruff.returncode != 0:
            return False, f"ruff KO:\n{ruff.stdout[-2000:]}"
    tests = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_kuro_tui_parts.py", "-q",
         "--cov=kuro_dashboard.tui", "--cov-fail-under=90"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    if tests.returncode != 0:
        tail = (tests.stdout + tests.stderr)[-2000:]
        return False, f"pytest KO:\n{tail}"
    return True, "gardes OK"


def build_message(branch: str, files: list[str]) -> str:
    sample = ", ".join(files[:5]) + ("…" if len(files) > 5 else "")
    stamp = _dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")
    return f"chore(sync): {len(files)} fichiers ({branch}) {stamp} [{sample}]"


def log_line(text: str) -> None:
    try:
        logdir = REPO / "logs"
        logdir.mkdir(exist_ok=True)
        with (logdir / "autosync.log").open("a", encoding="utf-8") as fh:
            stamp = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
            fh.write(f"{stamp} {text}\n")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Autosync local -> origin avec gardes.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-gate", action="store_true")
    parser.add_argument("--allow-main", action="store_true")
    args = parser.parse_args(argv)

    branch = current_branch()
    if not branch or branch == "HEAD":
        print("autosync: HEAD détachée, abandon")
        return 2
    ok, skipped = classify(changed_files())
    if skipped:
        print(f"autosync: ignorés ({len(skipped)}) : {skipped[:4]}")
    if not ok:
        print("autosync: rien à synchroniser")
        return 0
    staged_diff = _git("diff", "--", *ok, timeout=120).stdout or ""
    staged_diff += _git("diff", "--cached", "--", *ok, timeout=120).stdout or ""
    reasons = refusal_reasons(branch, ok, staged_diff, args.allow_main)
    if reasons:
        msg = "autosync: REFUS : " + " ; ".join(reasons)
        print(msg)
        log_line(msg)
        return 3
    if not args.no_gate:
        passed, detail = run_gates([f for f in ok if f.endswith(".py")])
        if not passed:
            msg = f"autosync: GARDES KO : {detail[:500]}"
            print(msg)
            log_line(msg)
            return 4
    message = build_message(branch, ok)
    if args.dry_run:
        print(f"autosync: DRY-RUN committerait+pousserait : {message}")
        return 0
    add = _git("add", "--", *ok, timeout=120)
    if add.returncode != 0:
        print(f"autosync: git add KO : {add.stderr[-500:]}")
        return 5
    commit = _git("commit", "-m", message, timeout=120)
    if commit.returncode != 0:
        print(f"autosync: git commit KO : {(commit.stdout + commit.stderr)[-500:]}")
        return 6
    push = _git("push", "origin", branch, timeout=180)
    if push.returncode != 0:
        rebase = _git("pull", "--rebase", "origin", branch, timeout=180)
        if rebase.returncode == 0:
            push = _git("push", "origin", branch, timeout=180)
    if push.returncode != 0:
        msg = f"autosync: git push KO sur {branch}"
        print(msg)
        log_line(msg)
        return 7
    msg = f"autosync: OK {message}"
    print(msg)
    log_line(msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
