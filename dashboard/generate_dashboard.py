from __future__ import annotations

import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parent.parent
DASHBOARD_DIR = ROOT_DIR / "dashboard"
DOCS_DIR = ROOT_DIR.parent
KNOWLEDGE_DIR = ROOT_DIR / "KNOWLEDGE_BASE"
PROJECTS_FILE = ROOT_DIR / "projects.txt"
EXCLUDE_FILE = ROOT_DIR / "exclude.txt"
AGENTS_FILE = ROOT_DIR / "AGENTS.md"
SYNC_LOG_FILE = ROOT_DIR / "SYNC_LOG.md"
OUTPUT_FILE = DASHBOARD_DIR / "dashboard-data.json"

RULE_PATTERN = re.compile(r"^## RULE\s+(\d+):\s*(.+)$")


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
        )
    except FileNotFoundError:
        return GitResult(False, "git not available")

    if completed.returncode != 0:
        return GitResult(False, completed.stderr.strip() or completed.stdout.strip())

    return GitResult(True, completed.stdout.strip())


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().isoformat(timespec="seconds")


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


def collect_kuro_rules_repo_state() -> dict[str, Any]:
    snapshot = collect_project_snapshot(ROOT_DIR.name, ROOT_DIR)
    snapshot["tracked"] = False
    return snapshot


def main() -> int:
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

    payload: dict[str, Any] = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "workspaceRoot": str(DOCS_DIR.resolve()),
        "kuroRulesRoot": str(ROOT_DIR.resolve()),
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
        "kuroRulesRepo": collect_kuro_rules_repo_state(),
    }

    OUTPUT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[+] Wrote dashboard snapshot to {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
