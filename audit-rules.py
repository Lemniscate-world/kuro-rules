#!/usr/bin/env python3
"""
audit-rules.py

Purpose
- Audit shared rule synchronization for kuro-rules.
- Support two execution modes:
  1. workspace mode: checks repositories listed in ~/Documents/kuro-rules/projects.txt
  2. repo mode: checks only the current kuro-rules repository itself
- Enforce the canonical GitHub Copilot instruction target:
  .github/copilot-instructions.md inside synced projects
- Detect drift in shared rule files
- Detect missing or extra rule numbers in AGENTS.md
- Optionally perform safe cleanup of redundant root-level
  copilot-instructions.md files when they are byte-identical to the
  canonical .github copy
- Optionally write Markdown and CSV reports for humans

Design notes
- This script is intentionally conservative.
- --fix-safe only performs actions that are provably non-destructive.
- If two files differ, the script reports the issue and does not delete.
- repo mode is intended for CI and pre-commit inside the kuro-rules repo.
- workspace mode is intended for local machine validation across all tracked repos.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

DEFAULT_BASE = Path.home() / "Documents"
DEFAULT_RULES_DIR = DEFAULT_BASE / "kuro-rules"

MASTER_RULE_FILES = [
    ".cursorrules",
    "AGENTS.md",
    "AI_GUIDELINES.md",
    "GAD.md",
]

RULE_SET_DISPLAY = [
    "AGENTS.md",
    "AI_GUIDELINES.md",
    ".cursorrules",
    "GAD.md",
    "copilot-instructions.md -> .github/copilot-instructions.md",
]

CANONICAL_COPILOT_TARGET = Path(".github") / "copilot-instructions.md"
LEGACY_ROOT_COPILOT = Path("copilot-instructions.md")


@dataclass(frozen=True)
class AuditIssue:
    project: str
    status: str
    details: str


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_master_hashes(rules_dir: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in MASTER_RULE_FILES:
        hashes[name] = sha256_file(rules_dir / name)
    hashes["copilot-instructions.md"] = sha256_file(
        rules_dir / "copilot-instructions.md"
    )
    return hashes


def load_master_rule_numbers(rules_dir: Path) -> set[int]:
    agents_path = rules_dir / "AGENTS.md"
    text = agents_path.read_text(encoding="utf-8", errors="replace")
    return {int(n) for n in re.findall(r"^##\s+RULE\s+(\d+):", text, flags=re.M)}


def extract_rule_numbers(agents_path: Path) -> set[int]:
    text = agents_path.read_text(encoding="utf-8", errors="replace")
    return {int(n) for n in re.findall(r"^##\s+RULE\s+(\d+):", text, flags=re.M)}


def relative_display(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base))
    except ValueError:
        return str(path)


def safe_remove_redundant_root_copilot(repo: Path, base: Path) -> list[str]:
    actions: list[str] = []

    root_copy = repo / LEGACY_ROOT_COPILOT
    canonical_copy = repo / CANONICAL_COPILOT_TARGET

    if not root_copy.exists() or not canonical_copy.exists():
        return actions

    try:
        if sha256_file(root_copy) == sha256_file(canonical_copy):
            root_copy.unlink()
            actions.append(
                f"removed redundant root copilot file at {relative_display(root_copy, base)}"
            )
    except Exception as exc:
        actions.append(
            f"could not evaluate redundant root copilot cleanup in "
            f"{relative_display(repo, base)} ({exc})"
        )

    return actions


def discover_untracked_git_repos(
    base: Path,
    tracked_repo_paths: Iterable[Path],
    rules_dir: Path,
) -> list[str]:
    tracked_paths = {repo.resolve() for repo in tracked_repo_paths}
    rules_dir_path = rules_dir.resolve()
    discovered: list[str] = []

    for candidate in sorted(base.iterdir()):
        if not candidate.is_dir():
            continue

        candidate_path = candidate.resolve()
        if candidate_path == rules_dir_path:
            continue
        if candidate_path in tracked_paths:
            continue
        if (candidate / ".git").exists():
            discovered.append(candidate.name)

    return discovered


def audit_master_rule_files(
    project_name: str,
    repo: Path,
    master_hashes: dict[str, str],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    for file_name in MASTER_RULE_FILES:
        target = repo / file_name
        if not target.exists():
            issues.append(AuditIssue(project_name, "FAIL", f"missing {file_name}"))
            continue

        if sha256_file(target) != master_hashes[file_name]:
            issues.append(AuditIssue(project_name, "FAIL", f"diff {file_name}"))

    return issues


def audit_agents_rule_numbers(
    project_name: str,
    repo: Path,
    master_rule_numbers: set[int],
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    agents_path = repo / "AGENTS.md"
    if not agents_path.exists():
        return issues

    repo_rule_numbers = extract_rule_numbers(agents_path)
    extra = sorted(repo_rule_numbers - master_rule_numbers)
    missing = sorted(master_rule_numbers - repo_rule_numbers)

    if extra:
        issues.append(AuditIssue(project_name, "FAIL", f"extra rule numbers {extra}"))
    if missing:
        issues.append(
            AuditIssue(project_name, "FAIL", f"missing rule numbers {missing}")
        )

    return issues


def audit_copilot_policy(
    project_name: str,
    repo: Path,
    master_hashes: dict[str, str],
    require_project_target: bool,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    canonical_copy = repo / CANONICAL_COPILOT_TARGET
    root_copy = repo / LEGACY_ROOT_COPILOT

    if require_project_target:
        if not canonical_copy.exists():
            issues.append(
                AuditIssue(
                    project_name,
                    "FAIL",
                    f"missing {CANONICAL_COPILOT_TARGET.as_posix()}",
                )
            )
        else:
            if sha256_file(canonical_copy) != master_hashes["copilot-instructions.md"]:
                issues.append(
                    AuditIssue(
                        project_name,
                        "FAIL",
                        f"diff {CANONICAL_COPILOT_TARGET.as_posix()}",
                    )
                )

        if root_copy.exists():
            issues.append(
                AuditIssue(
                    project_name,
                    "FAIL",
                    f"unexpected legacy root {LEGACY_ROOT_COPILOT.as_posix()}",
                )
            )
    else:
        if not root_copy.exists():
            issues.append(
                AuditIssue(
                    project_name,
                    "FAIL",
                    "missing master source copilot-instructions.md",
                )
            )
        elif sha256_file(root_copy) != master_hashes["copilot-instructions.md"]:
            issues.append(
                AuditIssue(
                    project_name,
                    "FAIL",
                    "diff master source copilot-instructions.md",
                )
            )

    return issues


def audit_projects_txt_duplicates(duplicates: Iterable[str]) -> list[AuditIssue]:
    return [
        AuditIssue(name, "FAIL", "duplicate project entry in projects.txt")
        for name in duplicates
    ]


def audit_repo(
    project_name: str,
    repo: Path,
    scope: str,
    master_hashes: dict[str, str],
    master_rule_numbers: set[int],
    require_project_target: bool,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []

    if not repo.exists():
        issues.append(AuditIssue(project_name, "FAIL", "repository directory missing"))
        return issues

    if scope in {"master", "all"}:
        issues.extend(audit_master_rule_files(project_name, repo, master_hashes))
        issues.extend(
            audit_agents_rule_numbers(project_name, repo, master_rule_numbers)
        )

    if scope in {"copilot", "all"}:
        issues.extend(
            audit_copilot_policy(
                project_name,
                repo,
                master_hashes,
                require_project_target=require_project_target,
            )
        )

    return issues


def write_reports(rows: list[AuditIssue], reports_dir: Path) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)

    md_path = reports_dir / "audit-rules-report.md"
    csv_path = reports_dir / "audit-rules-report.csv"

    md_lines = [
        "# Audit Rules Report",
        "",
        "| Project | Status | Details |",
        "|---|---|---|",
    ]
    for row in rows:
        safe_details = row.details.replace("|", "/")
        md_lines.append(f"| {row.project} | {row.status} | {safe_details} |")
    md_lines.append("")

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["project", "status", "details"])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "project": row.project,
                    "status": row.status,
                    "details": row.details,
                }
            )

    return md_path, csv_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit kuro-rules synchronization and canonical Copilot policy."
    )
    parser.add_argument(
        "--mode",
        choices=["workspace", "repo"],
        default="workspace",
        help=(
            "workspace = audit repositories listed in projects.txt under ~/Documents; "
            "repo = audit only the current kuro-rules repository"
        ),
    )
    parser.add_argument(
        "--scope",
        choices=["master", "copilot", "all"],
        default="all",
        help=(
            "master = shared rule files + AGENTS rule numbers, "
            "copilot = Copilot file policy only, "
            "all = everything"
        ),
    )
    parser.add_argument(
        "--fix-safe",
        action="store_true",
        help=(
            "Apply only provably safe fixes. In workspace mode, currently removes a "
            "redundant root-level copilot-instructions.md only when it is "
            "byte-identical to the canonical .github copy."
        ),
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write Markdown and CSV reports under reports/.",
    )
    parser.add_argument(
        "--rules-dir",
        type=Path,
        default=None,
        help=(
            "Override the kuro-rules directory path. "
            "Useful for tests, CI, or running the audit from a different location."
        ),
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        help=(
            "Override the base directory that contains tracked repositories. "
            "Useful for tests or custom workspace layouts."
        ),
    )
    return parser.parse_args()


def determine_runtime_context(
    mode: str,
    rules_dir_override: Path | None,
    base_dir_override: Path | None,
) -> tuple[Path, Path, Path]:
    if mode == "repo":
        rules_dir = (
            rules_dir_override.resolve()
            if rules_dir_override is not None
            else Path.cwd().resolve()
        )
        base = (
            base_dir_override.resolve()
            if base_dir_override is not None
            else rules_dir.parent
        )
        projects_file = rules_dir / "projects.txt"
        return base, rules_dir, projects_file

    base = (
        base_dir_override.resolve()
        if base_dir_override is not None
        else DEFAULT_BASE.resolve()
    )
    rules_dir = (
        rules_dir_override.resolve()
        if rules_dir_override is not None
        else (base / "kuro-rules").resolve()
    )
    projects_file = rules_dir / "projects.txt"
    return base, rules_dir, projects_file


def load_projects_for_mode(
    mode: str,
    rules_dir: Path,
    projects_file: Path,
    base: Path,
) -> tuple[list[str], list[str], dict[str, Path]]:
    if mode == "repo":
        project_name = rules_dir.name
        return [project_name], [], {project_name: rules_dir}

    raw = [
        line.strip()
        for line in projects_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    seen: set[str] = set()
    duplicates: list[str] = []
    for name in raw:
        if name in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(name)

    repo_map = {name: base / name for name in raw}
    return raw, duplicates, repo_map


def build_policy_summary(mode: str) -> str:
    if mode == "repo":
        return (
            "repo mode validates the current kuro-rules repository itself, including "
            "master rule files and the root source copilot-instructions.md."
        )
    return (
        "workspace mode validates all repositories listed in projects.txt, including "
        "shared rule files and canonical .github/copilot-instructions.md targets. "
        "It also reports untracked git repositories as NOTICE entries without "
        "failing the audit."
    )


def main() -> int:
    args = parse_args()

    base, rules_dir, projects_file = determine_runtime_context(
        args.mode,
        args.rules_dir,
        args.base_dir,
    )
    if not rules_dir.exists():
        print(f"AUDIT FAILED\n- rules directory missing: {rules_dir}")
        return 1
    if args.mode == "workspace" and not projects_file.exists():
        print(f"AUDIT FAILED\n- projects.txt missing: {projects_file}")
        return 1

    master_hashes = load_master_hashes(rules_dir)
    master_rule_numbers = load_master_rule_numbers(rules_dir)

    projects, duplicates, repo_map = load_projects_for_mode(
        args.mode, rules_dir, projects_file, base
    )

    fix_messages: list[str] = []
    if args.fix_safe and args.mode == "workspace":
        for name in projects:
            repo = repo_map[name]
            if repo.exists():
                fix_messages.extend(safe_remove_redundant_root_copilot(repo, base))

    issues: list[AuditIssue] = []
    if args.mode == "workspace":
        issues.extend(audit_projects_txt_duplicates(duplicates))

    for project_name in projects:
        repo = repo_map[project_name]
        issues.extend(
            audit_repo(
                project_name=project_name,
                repo=repo,
                scope=args.scope,
                master_hashes=master_hashes,
                master_rule_numbers=master_rule_numbers,
                require_project_target=(args.mode == "workspace"),
            )
        )

    notices: list[AuditIssue] = []
    if args.mode == "workspace":
        for repo_name in discover_untracked_git_repos(base, repo_map.values(), rules_dir):
            notices.append(
                AuditIssue(
                    repo_name,
                    "NOTICE",
                    "git repository discovered under base directory but not tracked in projects.txt",
                )
            )

    seen_failures = {issue.project for issue in issues}
    report_rows = list(issues)

    for notice in notices:
        report_rows.append(notice)

    for project_name in projects:
        if project_name not in seen_failures:
            report_rows.append(
                AuditIssue(
                    project_name, "PASS", f"mode={args.mode}; scope={args.scope}"
                )
            )

    reports_dir = rules_dir / "reports"
    if args.write_report:
        md_path, csv_path = write_reports(report_rows, reports_dir)
        print(f"REPORT_WRITTEN_MD={md_path}")
        print(f"REPORT_WRITTEN_CSV={csv_path}")

    for message in fix_messages:
        print(f"FIX_SAFE: {message}")

    for notice in notices:
        print(f"NOTICE: {notice.project}: {notice.details}")

    if issues:
        print("AUDIT FAILED")
        for issue in issues:
            print(f"- {issue.project}: {issue.details}")
        return 1

    print(
        "AUDIT PASSED: "
        f"{len(projects)} target(s) conform to kuro-rules policy "
        f"(mode={args.mode}, scope={args.scope})"
    )
    print(f"POLICY: {build_policy_summary(args.mode)}")
    print(f"RULE_SET: {', '.join(RULE_SET_DISPLAY)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
