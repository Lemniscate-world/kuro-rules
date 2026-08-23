#!/usr/bin/env python3
"""kuro_metrics.py — KPIs d'exécution Kuro : lead time, vélocité, échecs CI, pivots.

Sources 100% locales :
  - git log des repos détectés sous ~/Documents (+ projects.txt)
  - ci-status.json (copie committée par le robot Kuro)
  - ~/.kuro/kuro.db (dernière activité par projet)

Métriques :
  - lead_time_days   : jours entre le 1er commit (idée) et le N-ième commit (MVP)
  - velocity_per_week: commits / semaine sur la fenêtre glissante (30 j)
  - ci_failure_rate  : part des workflows en échec dans le dernier relevé CI
  - pivot_candidates : projets inactifs > 60 j (candidats au pivot ou à l'archivage)

Usage:
    python scripts/kuro_metrics.py [--json] [--window-days 30] [--min-commits 5]
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT_DIR.parent
PROJECTS_FILE = ROOT_DIR / "projects.txt"
EXCLUDE_FILE = ROOT_DIR / "exclude.txt"
KURO_DB_FILE = Path.home() / ".kuro" / "kuro.db"
CI_STATUS_CANDIDATES = (
    ROOT_DIR / "ci-status.json",
    Path.home() / "Documents" / "Lemniscate-world" / "ci-status.json",
)
PIVOT_INACTIVITY_DAYS = 60
CACHE_TTL_SECONDS = 300
_PAYLOAD_CACHE: dict[tuple[int, int], tuple[datetime, dict[str, Any]]] = {}


@dataclass
class GitResult:
    ok: bool
    output: str = ""


def run_git(path: Path, *args: str) -> GitResult:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=path,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return GitResult(False, "git not available")
    if completed.returncode != 0:
        return GitResult(False, completed.stderr.strip() or completed.stdout.strip())
    return GitResult(True, completed.stdout.strip())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_list_file(path: Path) -> list[str]:
    if not path.exists():
        return []
    entries: list[str] = []
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            entries.append(line)
    return entries


def detect_git_repositories() -> list[Path]:
    excluded = set(parse_list_file(EXCLUDE_FILE))
    excluded.add(ROOT_DIR.name)
    repos: list[Path] = []
    for child in DOCS_DIR.iterdir():
        if child.is_dir() and child.name not in excluded and (child / ".git").exists():
            repos.append(child)
    return sorted(repos, key=lambda item: item.name.lower())


def iso_date(value: str) -> str | None:
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def repo_lead_time(repo: Path, min_commits: int) -> tuple[int | None, int | None]:
    """(lead_time_days, total_commits). Lead = 1er commit -> commit n°min_commits."""
    dates_raw = run_git(repo, "log", "--reverse", "--format=%cI")
    if not dates_raw.ok or not dates_raw.output.strip():
        return None, None
    dates = [d for d in (iso_date(line) for line in dates_raw.output.splitlines()) if d]
    if not dates:
        return None, None
    first = dates[0]
    if len(dates) < min_commits:
        return None, len(dates)
    milestone = dates[min_commits - 1]
    return max(0, (milestone - first).days), len(dates)


def commits_in_window(repo: Path, window_days: int) -> int:
    result = run_git(repo, "rev-list", "--count", f"--since={window_days} days ago", "HEAD")
    if not result.ok or not result.output.strip().isdigit():
        return 0
    return int(result.output.strip())


def last_commit_at(repo: Path) -> str | None:
    result = run_git(repo, "log", "-1", "--format=%cI")
    return result.output.splitlines()[0].strip() if result.ok and result.output else None


def load_ci_status() -> dict[str, Any] | None:
    for candidate in CI_STATUS_CANDIDATES:
        try:
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return None


def ci_failure_by_repo(ci_status: dict[str, Any] | None) -> dict[str, dict[str, float]]:
    table: dict[str, dict[str, float]] = {}
    if not isinstance(ci_status, dict):
        return table
    for repo in ci_status.get("repos", []):
        name = str(repo.get("name") or "")
        workflows = repo.get("workflows", []) or []
        if not name or not workflows:
            continue
        failures = sum(1 for w in workflows if w.get("conclusion") == "failure")
        table[name.split("/")[-1]] = {
            "total": len(workflows),
            "failures": failures,
            "failure_rate": round(failures / len(workflows), 3),
        }
    return table


def pivot_candidates(window_days: int) -> list[dict[str, Any]]:
    if not KURO_DB_FILE.exists():
        return []
    cutoff = (datetime.now() - timedelta(days=window_days)).strftime("%Y-%m-%d %H:%M:%S")
    out: list[dict[str, Any]] = []
    try:
        conn = sqlite3.connect(f"file:{KURO_DB_FILE}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT name, status, last_activity FROM projects
               WHERE last_activity IS NOT NULL AND last_activity < ?
               ORDER BY last_activity ASC""",
            (cutoff,),
        ).fetchall()
        now = datetime.now()
        for row in rows:
            try:
                last = datetime.strptime(str(row["last_activity"])[:19], "%Y-%m-%d %H:%M:%S")
                days_inactive = (now - last).days
            except ValueError:
                days_inactive = None
            out.append(
                {
                    "name": row["name"],
                    "status": row["status"],
                    "last_activity": row["last_activity"],
                    "days_inactive": days_inactive,
                }
            )
        conn.close()
    except sqlite3.Error:
        return []
    return out


def build_payload(window_days: int = 30, min_commits: int = 5) -> dict[str, Any]:
    key = (window_days, min_commits)
    now = datetime.now().astimezone()
    cached = _PAYLOAD_CACHE.get(key)
    if cached and (now - cached[0]).total_seconds() < CACHE_TTL_SECONDS:
        return cached[1]

    ci_status = load_ci_status()
    ci_table = ci_failure_by_repo(ci_status)
    tracked_names = set(parse_list_file(PROJECTS_FILE))
    repos = detect_git_repositories()
    by_name = {repo.name: repo for repo in repos}
    for name in tracked_names:
        path = DOCS_DIR / name
        if name not in by_name and (path / ".git").exists():
            by_name[name] = path

    projects: list[dict[str, Any]] = []
    for name, repo in sorted(by_name.items()):
        lead, total_commits = repo_lead_time(repo, min_commits)
        commits_window = commits_in_window(repo, window_days)
        ci = ci_table.get(name, {})
        projects.append(
            {
                "name": name,
                "tracked": name in tracked_names,
                "lead_time_days": lead,
                "total_commits": total_commits,
                "commits_window": commits_window,
                "velocity_per_week": round(commits_window * 7 / window_days, 2),
                "ci_failure_rate": ci.get("failure_rate"),
                "ci_checks_total": ci.get("total", 0),
                "ci_failures": ci.get("failures", 0),
                "last_commit_at": last_commit_at(repo),
            }
        )

    leads = [p["lead_time_days"] for p in projects if p["lead_time_days"] is not None]
    velocities = [p["velocity_per_week"] for p in projects]
    total_checks = sum(p["ci_checks_total"] for p in projects)
    total_failures = sum(p["ci_failures"] for p in projects)

    payload = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "window_days": window_days,
        "min_commits_for_mvp": min_commits,
        "project_count": len(projects),
        "averages": {
            "lead_time_days": round(sum(leads) / len(leads), 1) if leads else None,
            "velocity_per_week": round(sum(velocities) / len(velocities), 2) if velocities else 0.0,
            "ci_failure_rate": round(total_failures / total_checks, 3) if total_checks else None,
        },
        "pivot_candidates": pivot_candidates(PIVOT_INACTIVITY_DAYS),
        "projects": projects,
    }
    _PAYLOAD_CACHE[key] = (datetime.now().astimezone(), payload)
    return payload


def render(payload: dict[str, Any]) -> str:
    avg = payload["averages"]
    lines = [
        f"Métriques d'exécution Kuro ({payload['project_count']} projets,"
        f" fenêtre {payload['window_days']} j)",
        f"  Lead time moyen : {avg['lead_time_days']} j"
        + ("" if avg["lead_time_days"] is not None else " (aucun projet au stade MVP)"),
        f"  Vélocité moyenne: {avg['velocity_per_week']} commits/semaine",
        f"  Échec CI global : {avg['ci_failure_rate']}",
        "",
        "  Par projet:",
    ]
    for p in payload["projects"]:
        lead = f"{p['lead_time_days']} j" if p["lead_time_days"] is not None else "—"
        lines.append(
            f"    {p['name']:<28} lead {lead:>8}  {p['commits_window']:>4} commits/{payload['window_days']}j"
            f"  ({p['velocity_per_week']}/sem)  CI {p['ci_failures']}/{p['ci_checks_total']} en échec"
        )
    if payload["pivot_candidates"]:
        lines.append("", )
        lines.append("  Pivots possibles (inactifs > 60 j):")
        for c in payload["pivot_candidates"]:
            lines.append(f"    {c['name']:<28} {c['days_inactive']} j d'inactivité ({c['status']})")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="KPIs d'exécution Kuro")
    parser.add_argument("--window-days", type=int, default=30)
    parser.add_argument("--min-commits", type=int, default=5)
    parser.add_argument("--json", action="store_true", help="sortie JSON brute")
    args = parser.parse_args()
    payload = build_payload(window_days=args.window_days, min_commits=args.min_commits)
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else render(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
