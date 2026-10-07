from __future__ import annotations

import json
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def _rules_dir() -> Path:
    """Racine kuro-rules : env KURO_RULES_DIR sinon layout standard ~/Documents."""
    env = os.environ.get("KURO_RULES_DIR")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "kuro-rules"


def _docs_dir() -> Path:
    """Racine des projets : env KURO_DOCS_DIR sinon parent de kuro-rules."""
    env = os.environ.get("KURO_DOCS_DIR")
    if env:
        return Path(env)
    return _rules_dir().parent


ROOT_DIR = _rules_dir()
DASHBOARD_DIR = ROOT_DIR / "dashboard"
DOCS_DIR = _docs_dir()
KNOWLEDGE_DIR = ROOT_DIR / "KNOWLEDGE_BASE"
PROJECTS_FILE = ROOT_DIR / "projects.txt"
EXCLUDE_FILE = ROOT_DIR / "exclude.txt"
AGENTS_FILE = ROOT_DIR / "AGENTS.md"
SYNC_LOG_FILE = ROOT_DIR / "SYNC_LOG.md"
KURO_DB_FILE = Path.home() / ".kuro" / "kuro.db"
OUTPUT_FILE = DASHBOARD_DIR / "dashboard-data.json"

RULE_PATTERN = re.compile(r"^## RULE\s+(\d+):\s*(.+)$")

GIT_TIMEOUT_SECONDS = 25
PAYLOAD_CACHE_TTL_SECONDS = 60
_PAYLOAD_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None}


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
            timeout=GIT_TIMEOUT_SECONDS,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except FileNotFoundError:
        return GitResult(False, "git not available")
    except (NotADirectoryError, OSError) as exc:
        return GitResult(False, f"git cwd invalide: {exc}".strip()[:120])
    except subprocess.TimeoutExpired:
        return GitResult(False, "git timeout")

    if completed.returncode != 0:
        return GitResult(False, completed.stderr.strip() or completed.stdout.strip())

    return GitResult(True, completed.stdout.strip())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iso_from_timestamp(timestamp: float) -> str:
    try:
        return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")
    except (OSError, OverflowError, ValueError):
        return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_list_file(path: Path) -> list[str]:
    if not path.exists():
        return []

    entries: list[str] = []
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line)
    return entries


def detect_git_repositories() -> list[Path]:
    repos: list[Path] = []
    if not DOCS_DIR.is_dir():
        return repos
    excluded = set(parse_list_file(EXCLUDE_FILE))
    excluded.add(ROOT_DIR.name)

    for child in DOCS_DIR.iterdir():
        if not child.is_dir():
            continue
        if child.name in excluded:
            continue
        if (child / ".git").exists():
            repos.append(child)

    return sorted(repos, key=lambda item: item.name.lower())


def normalize_name(value: str) -> str:
    return value.strip().lower()


def parse_remote(remote_url: str) -> dict[str, Any]:
    if not remote_url:
        return {"organization": "local-only", "repository": "", "host": ""}

    if remote_url.startswith("git@"):
        match = re.match(r"git@([^:]+):([^/]+)/(.+?)(?:\.git)?$", remote_url)
        if match:
            host, organization, repository = match.groups()
            return {
                "organization": organization,
                "repository": repository,
                "host": host,
            }
    else:
        parsed = urlparse(remote_url)
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            return {
                "organization": parts[0],
                "repository": parts[1].removesuffix(".git"),
                "host": parsed.netloc,
            }

    return {"organization": "local-only", "repository": "", "host": ""}


def first_heading_or_line(path: Path) -> str:
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#"):
            return line.lstrip("# ").strip()
        return line
    return path.stem.replace("_", " ").replace("-", " ").title()


def first_summary_line(path: Path) -> str:
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        return line
    return "No summary yet."


def detect_kind(path: Path) -> str:
    lower = path.as_posix().lower()
    if "post_mortem" in lower or "postmortem" in lower:
        return "post-mortem"
    if "mom_tests" in lower:
        return "mom-test"
    return "note"


def collect_knowledge_entries() -> list[dict[str, Any]]:
    if not KNOWLEDGE_DIR.exists():
        return []

    entries: list[dict[str, Any]] = []
    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        relative = path.relative_to(ROOT_DIR)
        entries.append(
            {
                "title": first_heading_or_line(path),
                "summary": first_summary_line(path),
                "path": str(relative).replace("\\", "/"),
                "kind": detect_kind(path),
                "category": str(relative.parent).replace("\\", "/"),
                "updatedAt": iso_from_timestamp(path.stat().st_mtime),
            }
        )
    return entries


def collect_rule_highlights() -> list[dict[str, Any]]:
    if not AGENTS_FILE.exists():
        return []

    lines = read_text(AGENTS_FILE).splitlines()
    rules: list[dict[str, Any]] = []
    interesting = (
        "failure",
        "knowledge",
        "linear",
        "dashboard",
        "memory",
        "gui",
        "sync",
        "cross-branch",
        "progress",
    )

    for index, line in enumerate(lines):
        match = RULE_PATTERN.match(line.strip())
        if not match:
            continue

        number, title = match.groups()
        lowered = title.lower()
        if not any(token in lowered for token in interesting):
            continue

        summary = ""
        for candidate in lines[index + 1 : index + 8]:
            candidate = candidate.strip()
            if not candidate or candidate.startswith("#"):
                continue
            summary = candidate
            break

        rules.append(
            {
                "number": int(number),
                "title": title.strip(),
                "summary": summary or "No summary extracted.",
                "lineNumber": index + 1,
            }
        )

    return rules


def parse_sync_log() -> dict[str, Any]:
    if not SYNC_LOG_FILE.exists():
        return {"lastRun": None, "repoCount": 0, "fileCount": 0, "entries": []}

    lines = read_text(SYNC_LOG_FILE).splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("## ")), None)
    if header_index is None:
        return {"lastRun": None, "repoCount": 0, "fileCount": 0, "entries": []}

    last_run = lines[header_index].replace("## ", "", 1).strip()
    entries: list[dict[str, Any]] = []
    file_count = 0

    for line in lines[header_index + 1 :]:
        if line.startswith("## "):
            break
        if not line.startswith("- "):
            continue
        payload = line[2:]
        if " : " in payload:
            project, files = payload.split(" : ", 1)
            file_names = [item.strip() for item in files.split(",") if item.strip()]
        else:
            project = payload
            file_names = []
        file_count += len(file_names)
        entries.append({"project": project.strip(), "files": file_names})

    return {
        "lastRun": last_run,
        "repoCount": len(entries),
        "fileCount": file_count,
        "entries": entries,
    }


def collect_project_snapshot(project_name: str, path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {
            "name": project_name,
            "path": str((DOCS_DIR / project_name).resolve()),
            "exists": False,
            "tracked": True,
            "status": "missing",
            "organization": "missing",
            "repository": "",
            "host": "",
            "branch": "",
            "dirtyCount": 0,
            "dirtyFiles": [],
            "lastCommitAt": None,
            "lastCommitMessage": "",
            "hasAgents": False,
            "hasReadme": False,
            "hasSessionSummary": False,
            "workflowCount": 0,
            "remoteUrl": "",
            "ahead": 0,
            "behind": 0,
        }

    remote_url = run_git(path, "config", "--get", "remote.origin.url").output
    remote = parse_remote(remote_url)
    branch = run_git(path, "branch", "--show-current").output
    status_lines = run_git(path, "status", "--porcelain").output.splitlines()
    dirty_files = [line[3:] if len(line) > 3 else line for line in status_lines]
    commit_log = run_git(path, "log", "-1", "--format=%cI%n%s").output.splitlines()
    last_commit_at = commit_log[0] if len(commit_log) >= 1 else None
    last_commit_message = commit_log[1] if len(commit_log) >= 2 else ""

    upstream_name = run_git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    ahead = 0
    behind = 0
    if upstream_name.ok and upstream_name.output:
        left_right = run_git(path, "rev-list", "--left-right", "--count", f"HEAD...{upstream_name.output}")
        if left_right.ok and left_right.output:
            behind_text, ahead_text = left_right.output.split()
            behind = int(behind_text)
            ahead = int(ahead_text)

    has_agents = (path / "AGENTS.md").exists()
    has_readme = any((path / candidate).exists() for candidate in ("README.md", "readme.md"))
    has_session_summary = (path / "SESSION_SUMMARY.md").exists()
    workflow_path = path / ".github" / "workflows"
    workflow_count = len(list(workflow_path.glob("*.*"))) if workflow_path.exists() else 0

    if dirty_files:
        status = "attention"
    elif not has_agents:
        status = "unsynced"
    else:
        status = "steady"

    return {
        "name": project_name,
        "path": str(path.resolve()),
        "exists": True,
        "tracked": True,
        "status": status,
        "organization": remote["organization"],
        "repository": remote["repository"] or project_name,
        "host": remote["host"],
        "branch": branch,
        "dirtyCount": len(dirty_files),
        "dirtyFiles": dirty_files[:8],
        "lastCommitAt": last_commit_at,
        "lastCommitMessage": last_commit_message,
        "hasAgents": has_agents,
        "hasReadme": has_readme,
        "hasSessionSummary": has_session_summary,
        "workflowCount": workflow_count,
        "remoteUrl": remote_url,
        "ahead": ahead,
        "behind": behind,
    }


def summarize_status(projects: list[dict[str, Any]]) -> dict[str, Any]:
    existing = [project for project in projects if project["exists"]]
    missing = [project for project in projects if not project["exists"]]
    dirty = [project for project in existing if project["dirtyCount"] > 0]
    unsynced = [project for project in existing if not project["hasAgents"]]

    return {
        "trackedProjects": len(projects),
        "liveProjects": len(existing),
        "missingTrackedProjects": len(missing),
        "dirtyProjects": len(dirty),
        "unsyncedProjects": len(unsynced),
    }


def build_alerts(
    tracked_projects: list[dict[str, Any]],
    untracked_repositories: list[dict[str, Any]],
    knowledge_entries: list[dict[str, Any]],
    sync_log: dict[str, Any],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []

    missing = [project["name"] for project in tracked_projects if not project["exists"]]
    if missing:
        alerts.append(
            {
                "severity": "high",
                "title": "Tracked projects missing on disk",
                "detail": ", ".join(missing[:6]),
            }
        )

    dirty = [project["name"] for project in tracked_projects if project["dirtyCount"] > 0]
    if dirty:
        alerts.append(
            {
                "severity": "medium",
                "title": "Projects currently dirty",
                "detail": ", ".join(dirty[:6]),
            }
        )

    if untracked_repositories:
        names = ", ".join(repo["name"] for repo in untracked_repositories[:6])
        alerts.append(
            {
                "severity": "medium",
                "title": "Git repos are present but not tracked",
                "detail": names,
            }
        )

    post_mortem_count = sum(1 for entry in knowledge_entries if entry["kind"] == "post-mortem")
    if post_mortem_count == 0:
        alerts.append(
            {
                "severity": "medium",
                "title": "No post-mortems in the knowledge base",
                "detail": "Failure memory exists in the rules, but not yet in stored artifacts.",
            }
        )

    if sync_log["lastRun"] is None:
        alerts.append(
            {
                "severity": "high",
                "title": "No sync pulse found",
                "detail": "SYNC_LOG.md does not contain a parseable run yet.",
            }
        )

    return alerts


def build_organization_groups(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for project in projects:
        if not project["exists"]:
            continue
        buckets[project["organization"]].append(project)

    groups: list[dict[str, Any]] = []
    for organization, entries in sorted(buckets.items(), key=lambda item: item[0].lower()):
        dirty_count = sum(1 for entry in entries if entry["dirtyCount"] > 0)
        groups.append(
            {
                "name": organization,
                "projectCount": len(entries),
                "dirtyCount": dirty_count,
                "projects": sorted(entries, key=lambda item: item["name"].lower()),
            }
        )
    return groups


def discover_untracked_repositories(
    tracked_names: set[str], git_repositories: list[Path]
) -> list[dict[str, Any]]:
    extras: list[dict[str, Any]] = []
    for repo in git_repositories:
        if normalize_name(repo.name) in tracked_names:
            continue
        snapshot = collect_project_snapshot(repo.name, repo)
        snapshot["tracked"] = False
        extras.append(snapshot)
    return extras


def _safe_count(cursor: Any, sql: str) -> int:
    """COUNT tolerant : table absente -> 0, jamais d'exception."""
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0


def _safe_one(cursor: Any, sql: str) -> Any | None:
    """SELECT scalaire tolerant : table absente -> None."""
    try:
        cursor.execute(sql)
        row = cursor.fetchone()
        return row[0] if row else None
    except Exception:
        return None


def collect_kuro_daemon_state() -> dict[str, Any]:
    """Etat daemon Kuro : tolerant aux schemas partiels (fresh install).

    Tables lues en best-effort : heartbeat (daemon v1) OU activity_log
    (daemon v2), projects, alerts. Table absente -> compteur 0, pas "error".
    "error" uniquement si le fichier DB est illisible.
    """
    import sqlite3
    state: dict[str, Any] = {"status": "inactive", "alerts": [],
                             "projectCount": 0, "heartbeatAt": None}
    if not KURO_DB_FILE.exists():
        return state

    try:
        conn = sqlite3.connect(f"file:{KURO_DB_FILE}?mode=ro",
                               uri=True, timeout=5)
    except Exception:
        state["status"] = "error"
        return state
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Battement recent : heartbeat (v1) sinon activity_log (v2).
        last_ts_raw = _safe_one(
            cursor, "SELECT MAX(timestamp) FROM heartbeat")
        if last_ts_raw is None:
            last_ts_raw = _safe_one(
                cursor, "SELECT MAX(timestamp) FROM activity_log")
        if last_ts_raw:
            state["heartbeatAt"] = str(last_ts_raw)
            try:
                last_ts = datetime.fromisoformat(
                    str(last_ts_raw).replace('Z', '+00:00'))
                if not last_ts.tzinfo:
                    last_ts = last_ts.astimezone()
                if (datetime.now().astimezone() - last_ts).total_seconds() < 3600:
                    state["status"] = "active"
            except Exception:
                pass

        state["projectCount"] = _safe_count(
            cursor, "SELECT COUNT(*) FROM projects")
        try:
            cursor.execute(
                "SELECT a.*, p.name as project_name FROM alerts a "
                "LEFT JOIN projects p ON a.project_id = p.id "
                "WHERE a.acknowledged = 0 LIMIT 20")
            state["alerts"] = [dict(r) for r in cursor.fetchall()]
        except Exception:
            state["alerts"] = []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return state


def collect_coverage_state() -> dict[str, Any]:
    """Fraicheur de coverage.local.json (jamais d'exception).

    Le dashboard affichait des % vieux de plusieurs semaines sans le dire.
    On expose generated_at + age + pct moyen pour que l'UI previenne
    quand la mesure est stale (>7 j) au lieu d'afficher un chiffre muet.
    """
    cov_file = ROOT_DIR / "coverage.local.json"
    out: dict[str, Any] = {"present": False, "generatedAt": None,
                           "ageDays": None, "stale": True,
                           "repos": 0, "avgPct": None}
    try:
        if not cov_file.exists():
            return out
        data = json.loads(cov_file.read_text(encoding="utf-8"))
        out["present"] = True
        gen = data.get("generated_at")
        out["generatedAt"] = gen
        repos = data.get("repos") or []
        out["repos"] = len(repos)
        pcts = [r.get("pct_total") for r in repos
                if isinstance(r.get("pct_total"), (int, float))]
        out["avgPct"] = round(sum(pcts) / len(pcts), 1) if pcts else None
        if gen:
            try:
                dt = datetime.fromisoformat(str(gen).replace("Z", "+00:00"))
                if not dt.tzinfo:
                    dt = dt.astimezone()
                age_d = (datetime.now().astimezone() - dt).total_seconds() / 86400
                out["ageDays"] = round(age_d, 1)
                out["stale"] = age_d > 7
            except Exception:
                pass
    except Exception:
        pass
    return out


def collect_ci_status_state() -> dict[str, Any]:
    """Fraicheur de ci-status.json (jamais d'exception)."""
    out: dict[str, Any] = {"present": False, "generatedAt": None,
                           "ageDays": None, "stale": True,
                           "overall": None}
    for candidate in (ROOT_DIR / "ci-status.json",
                      Path.home() / "Documents" / "Lemniscate-world" / "ci-status.json"):
        try:
            if not candidate.exists():
                continue
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            out["present"] = True
            out["generatedAt"] = data.get("generated_at")
            out["overall"] = data.get("overall")
            try:
                dt = datetime.fromisoformat(
                    str(data.get("generated_at")).replace("Z", "+00:00"))
                if not dt.tzinfo:
                    dt = dt.astimezone()
                age_d = (datetime.now().astimezone() - dt).total_seconds() / 86400
                out["ageDays"] = round(age_d, 1)
                out["stale"] = age_d > 2
            except Exception:
                pass
            break
        except Exception:
            continue
    return out


def collect_kuro_rules_repo_state() -> dict[str, Any]:
    snapshot = collect_project_snapshot(ROOT_DIR.name, ROOT_DIR)
    snapshot["tracked"] = False
    return snapshot


def build_payload(use_cache: bool = True) -> dict[str, Any]:
    if use_cache:
        cached = _PAYLOAD_CACHE.get("payload")
        if cached is not None and \
                time.monotonic() - float(_PAYLOAD_CACHE.get("ts", 0.0)) < PAYLOAD_CACHE_TTL_SECONDS:
            return cached
    tracked_names = parse_list_file(PROJECTS_FILE)
    tracked_lookup = {name: DOCS_DIR / name for name in tracked_names}
    git_repositories = detect_git_repositories()
    git_lookup = {normalize_name(repo.name): repo for repo in git_repositories}

    tracked_projects = [
        collect_project_snapshot(name, git_lookup.get(normalize_name(name)) or tracked_lookup.get(name))
        for name in tracked_names
    ]
    untracked_repositories = discover_untracked_repositories(
        {normalize_name(name) for name in tracked_names},
        git_repositories,
    )
    knowledge_entries = collect_knowledge_entries()
    sync_log = parse_sync_log()
    rule_highlights = collect_rule_highlights()
    status_summary = summarize_status(tracked_projects)
    organizations = build_organization_groups(tracked_projects)
    knowledge_counts = Counter(entry["kind"] for entry in knowledge_entries)
    alerts = build_alerts(tracked_projects, untracked_repositories, knowledge_entries, sync_log)

    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspaceRoot": str(DOCS_DIR.resolve()) if DOCS_DIR.exists() else str(DOCS_DIR),
        "kuroRulesRoot": str(ROOT_DIR.resolve()) if ROOT_DIR.exists() else str(ROOT_DIR),
        "summary": {
            **status_summary,
            "organizationCount": len(organizations),
            "untrackedRepositories": len(untracked_repositories),
            "knowledgeEntries": len(knowledge_entries),
            "postMortems": knowledge_counts.get("post-mortem", 0),
            "momTests": knowledge_counts.get("mom-test", 0),
        },
        "alerts": alerts,
        "trackedProjects": tracked_projects,
        "untrackedRepositories": untracked_repositories,
        "organizations": organizations,
        "knowledgeBase": {
            "counts": dict(knowledge_counts),
            "entries": knowledge_entries,
        },
        "ruleHighlights": rule_highlights,
        "syncLog": sync_log,
        "kuroDaemon": collect_kuro_daemon_state(),
        "kuroRulesRepo": collect_kuro_rules_repo_state(),
        "coverage": collect_coverage_state(),
        "ciStatus": collect_ci_status_state(),
    }
    _PAYLOAD_CACHE["ts"] = time.monotonic()
    _PAYLOAD_CACHE["payload"] = payload
    return payload


def main() -> int:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = build_payload(use_cache=False)
    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[+] Wrote dashboard snapshot to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
