#!/usr/bin/env python3
from pathlib import Path
import argparse
import csv
import hashlib
import re
import sys

BASE = Path.home() / "Documents"
RULES_DIR = BASE / "kuro-rules"
PROJECTS_FILE = RULES_DIR / "projects.txt"
RULE_FILES = [".cursorrules", "AGENTS.md", "AI_GUIDELINES.md", "GAD.md"]
MASTER_RULE_NUMS = sorted({int(n) for n in re.findall(r"^##\s+RULE\s+(\d+):", (RULES_DIR / "AGENTS.md").read_text(encoding="utf-8", errors="replace"), flags=re.M)})
MASTER_RULE_SET = set(MASTER_RULE_NUMS)
MASTER_HASHES = {name: hashlib.sha256((RULES_DIR / name).read_bytes()).hexdigest() for name in RULE_FILES + ["copilot-instructions.md"]}

def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_projects():
    raw = [line.strip() for line in PROJECTS_FILE.read_text(encoding="utf-8").splitlines() if line.strip() and not line.strip().startswith("#")]
    return raw, sorted({name for name in raw if raw.count(name) > 1})

def audit_project(name, scope):
    failures = []
    repo = BASE / name
    if not repo.exists():
        failures.append(f"{name}: repository directory missing")
        return failures
    if scope in ("master", "all"):
        for rule_file in RULE_FILES:
            target = repo / rule_file
            if not target.exists():
                failures.append(f"{name}: missing {rule_file}")
            elif sha(target) != MASTER_HASHES[rule_file]:
                failures.append(f"{name}: diff {rule_file}")
        agents = repo / "AGENTS.md"
        if agents.exists():
            nums = {int(n) for n in re.findall(r"^##\s+RULE\s+(\d+):", agents.read_text(encoding="utf-8", errors="replace"), flags=re.M)}
            extra = sorted(nums - MASTER_RULE_SET)
            missing = sorted(MASTER_RULE_SET - nums)
            if extra:
                failures.append(f"{name}: extra rule numbers {extra}")
            if missing:
                failures.append(f"{name}: missing rule numbers {missing}")
    if scope in ("copilot", "all"):
        gh = repo / ".github" / "copilot-instructions.md"
        root = repo / "copilot-instructions.md"
        if not gh.exists():
            failures.append(f"{name}: missing .github/copilot-instructions.md")
        elif sha(gh) != MASTER_HASHES["copilot-instructions.md"]:
            failures.append(f"{name}: diff .github/copilot-instructions.md")
        if root.exists():
            failures.append(f"{name}: unexpected root copilot-instructions.md")
    return failures

def fix_safe(name):
    repo = BASE / name
    if not repo.exists():
        return []
    actions = []
    root = repo / "copilot-instructions.md"
    gh = repo / ".github" / "copilot-instructions.md"
    if root.exists() and gh.exists():
        try:
            if sha(root) == sha(gh):
                root.unlink()
                actions.append(f"{name}: removed redundant root copilot-instructions.md")
        except Exception as exc:
            actions.append(f"{name}: could not evaluate root copilot cleanup ({exc})")
    return actions

def write_reports(report_rows):
    reports_dir = RULES_DIR / "reports"
    reports_dir.mkdir(exist_ok=True)
    md_path = reports_dir / "audit-rules-report.md"
    csv_path = reports_dir / "audit-rules-report.csv"
    md_lines = ["# Audit Rules Report", "", "| Project | Status | Details |", "|---|---|---|"]
    for row in report_rows:
        details = row["details"].replace("|", \/)
        md_lines.append(f"| {row[project]} | {row[status]} | {details} |")
    md_path.write_text("
".join(md_lines) + "
", encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["project", "status", "details"])
        writer.writeheader()
        writer.writerows(report_rows)
    return md_path, csv_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", choices=["master", "copilot", "all"], default="all")
    parser.add_argument("--fix-safe", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    projects, duplicates = load_projects()
    failures = []
    fixes = []
    if duplicates:
        failures.extend([f"projects.txt: duplicate project entry {name}" for name in duplicates])
    for name in projects:
        if args.fix_safe:
            fixes.extend(fix_safe(name))
        failures.extend(audit_project(name, args.scope))

    report_rows = []
    if duplicates:
        for name in duplicates:
            report_rows.append({"project": name, "status": "FAIL", "details": "duplicate project entry in projects.txt"})
    seen = set()
    for failure in failures:
        project = failure.split(":", 1)[0]
        report_rows.append({"project": project, "status": "FAIL", "details": failure})
        seen.add(project)
    for name in projects:
        if name not in seen:
            report_rows.append({"project": name, "status": "PASS", "details": f"scope={args.scope}"})

    if args.write_report:
        md_path, csv_path = write_reports(report_rows)
        print(f"REPORT_WRITTEN_MD={md_path}")
        print(f"REPORT_WRITTEN_CSV={csv_path}")
    for action in fixes:
        print(f"FIX_SAFE: {action}")
    if failures:
        print("AUDIT FAILED")
        for item in failures:
            print(f"- {item}")
        sys.exit(1)
    print(f"AUDIT PASSED: {len(projects)} repositories conform to canonical kuro-rules policy (scope={args.scope})")

if __name__ == "__main__":
    main()
