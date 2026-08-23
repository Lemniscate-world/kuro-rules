#!/usr/bin/env python3
"""kuro_skills.py — skills vérifiés par preuves, détectés automatiquement.

Principe : un pourcentage de skill se mérite par des signaux mesurés dans les
repos locaux (aucune auto-déclaration, aucun quiz) :
  - volume      : poids du code (Ko) par langage/techno, plafonné par repo
  - pénétration : nombre de repos où la techno est détectée
  - activité    : commits 90 j dans les repos concernés
  - profondeur  : tests présents + CI verte (ci-status.json)

Détection automatique : extensions git ls-files + manifests (requirements,
package.json, cargo, go.mod, pubspec, csproj...) + workflows. Un skill nouveau
apparaît seul, marqué NEW s'il n'existait pas au relevé précédent (skills.json).

Le bloc README est régénéré entre marqueurs KURO-SKILLS:START/END.

Usage:
    python scripts/kuro_skills.py [--docs ~/Documents] [--readme README.md]
                                  [--output skills.json] [--top 15] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_metrics import (  # noqa: E402
    GitResult,
    commits_in_window,
    detect_git_repositories,
    load_ci_status,
    parse_list_file,
    read_text,
    run_git,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = ROOT_DIR.parent
DEFAULT_README = DEFAULT_DOCS / "Lemniscate-world" / "README.md"
DEFAULT_OUTPUT = ROOT_DIR / "skills.json"
WINDOW_DAYS = 90
LOC_CAP_KB_PER_REPO = 400
FILES_CAP_PER_LANG = 3000
MAX_PCT = 95
MIN_PCT = 5
TOP_N = 15

VOL_CAP_KB = 5000.0
PEN_CAP_REPOS = 25.0
ACT_CAP_COMMITS = 400.0

HIDDEN_SKILLS = {"pip", "npm", "cargo", "gomod", "conda", "bundler", "composer"}

RENAME_SKILLS = {
    "github-actions": "GitHub Actions",
    "scikit-learn": "scikit-learn",
    "next.js": "Next.js",
    "d3.js": "D3.js",
    "docker": "Docker",
}

LANG_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "Python": (".py", ".ipynb"),
    "JavaScript": (".js", ".jsx", ".mjs"),
    "TypeScript": (".ts", ".tsx"),
    "Rust": (".rs",),
    "Go": (".go",),
    "Java": (".java",),
    "Kotlin": (".kt",),
    "Swift": (".swift",),
    "C": (".c", ".h"),
    "C++": (".cpp", ".hpp", ".cc"),
    "C#": (".cs",),
    "PHP": (".php",),
    "Ruby": (".rb",),
    "Dart": (".dart",),
    "Scala": (".scala",),
    "Haskell": (".hs",),
    "Julia": (".jl",),
    "R": (".r",),
    "Lua": (".lua",),
    "SQL": (".sql",),
    "HTML": (".html",),
    "CSS": (".css", ".scss"),
    "Shell": (".sh", ".bash"),
    "PowerShell": (".ps1",),
    "Q": (".q",),
}

MANIFEST_TECHS: dict[str, tuple[str, ...]] = {
    "requirements.txt": ("pip",),
    "pyproject.toml": ("pip",),
    "environment.yml": ("conda",),
    "package.json": ("npm",),
    "cargo.toml": ("cargo",),
    "go.mod": ("gomod",),
    "pubspec.yaml": ("flutter",),
    "gemfile": ("bundler",),
    "composer.json": ("composer",),
    "dockerfile": ("docker",),
    "docker-compose.yml": ("docker",),
}

PY_TECH_MAP: dict[str, str] = {
    "tensorflow": "TensorFlow", "torch": "PyTorch", "keras": "Keras",
    "pandas": "Pandas", "numpy": "NumPy", "scikit-learn": "scikit-learn",
    "sklearn": "scikit-learn", "fastapi": "FastAPI", "flask": "Flask",
    "django": "Django", "pytest": "Pytest", "optuna": "Optuna",
    "plotly": "Plotly", "selenium": "Selenium", "transformers": "Transformers",
    "langchain": "LangChain", "streamlit": "Streamlit", "qiskit": "Qiskit",
    "scipy": "SciPy", "statsmodels": "Statsmodels", "airflow": "Airflow",
}
JS_TECH_MAP: dict[str, str] = {
    "react": "React", "next": "Next.js", "vue": "Vue", "svelte": "Svelte",
    "electron": "Electron", "vite": "Vite", "tailwindcss": "Tailwind",
    "typescript": "TypeScript", "vitest": "Vitest", "jest": "Jest",
    "d3": "D3.js", "express": "Express", "prisma": "Prisma",
}
WORKFLOW_TECHS = ("github-actions",)
CONFIG_TECHS: dict[str, str] = {
    "vercel.json": "Vercel", "tailwind.config.js": "Tailwind",
    "tailwind.config.ts": "Tailwind", "nginx.conf": "Nginx",
    "vite.config.ts": "Vite", "vite.config.js": "Vite",
    "next.config.js": "Next.js", "next.config.mjs": "Next.js",
}


def repo_tech_signals(repo: Path) -> tuple[dict[str, int], set[str]]:
    """(Ko par langage, set de technos détectées) pour un repo."""
    kb_by_lang: dict[str, int] = defaultdict(int)
    techs: set[str] = set()
    files_raw = run_git(repo, "ls-files")
    if not files_raw.ok:
        return dict(kb_by_lang), techs
    per_lang_count: dict[str, int] = defaultdict(int)
    for rel in files_raw.output.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        lower = rel.lower()
        name = lower.rsplit("/", 1)[-1]
        if name in MANIFEST_TECHS:
            techs.update(MANIFEST_TECHS[name])
        if name in CONFIG_TECHS:
            techs.add(CONFIG_TECHS[name])
        for lang, exts in LANG_EXTENSIONS.items():
            if per_lang_count[lang] >= FILES_CAP_PER_LANG:
                continue
            if lower.endswith(exts):
                path = repo / rel
                try:
                    kb = path.stat().st_size // 1024
                except OSError:
                    continue
                kb_by_lang[lang] += min(kb, LOC_CAP_KB_PER_REPO)
                per_lang_count[lang] += 1
                break
    if (repo / ".github" / "workflows").exists():
        techs.update(WORKFLOW_TECHS)
    techs.update(_manifest_dep_techs(repo))
    return dict(kb_by_lang), techs


def _manifest_dep_techs(repo: Path) -> set[str]:
    found: set[str] = set()
    reqs = list(repo.glob("requirements*.txt")) + list(repo.glob("pyproject.toml"))
    pkg = repo / "package.json"
    try:
        for req in reqs:
            text = read_text(req).lower()
            for dep, tech in PY_TECH_MAP.items():
                if dep in text:
                    found.add(tech)
        if pkg.exists():
            data = json.loads(read_text(pkg))
            deps = set(data.get("dependencies", {})) | set(data.get("devDependencies", {}))
            for dep, tech in JS_TECH_MAP.items():
                if dep in deps:
                    found.add(tech)
    except Exception:
        return found
    return found


def has_tests(repo: Path) -> bool:
    for candidate in ("tests", "test"):
        if (repo / candidate).is_dir():
            return True
    files_raw = run_git(repo, "ls-files", "test_*.py", "*_test.go", "*.test.ts", "*.test.js")
    return files_raw.ok and bool(files_raw.output.strip())


def normalize(name: str) -> str:
    return name.strip().lower()


def build_payload(docs_dir: Path, window_days: int = WINDOW_DAYS) -> dict[str, Any]:
    ci_status = load_ci_status()
    ci_green: dict[str, bool] = {}
    if isinstance(ci_status, dict):
        for r in ci_status.get("repos", []):
            repo_name = str(r.get("name") or "").split("/")[-1]
            ci_green[normalize(repo_name)] = r.get("health") == "green"

    tracked = set(parse_list_file(ROOT_DIR / "projects.txt"))
    repos = detect_git_repositories(docs_dir)
    by_name = {repo.name: repo for repo in repos}
    for name in tracked:
        path = docs_dir / name
        if name not in by_name and (path / ".git").exists():
            by_name[name] = path

    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "kb": 0, "repos": set(), "commits": 0, "ci_green": 0, "ci_total": 0,
        "tests": 0, "last_seen": "",
    })

    for name, repo in sorted(by_name.items()):
        kb_by_lang, techs = repo_tech_signals(repo)
        commits = commits_in_window(repo, window_days)
        tests = has_tests(repo)
        green = ci_green.get(normalize(name))
        skill_names = {lang for lang, kb in kb_by_lang.items() if kb > 0} | techs
        for skill in skill_names:
            s = stats[skill]
            s["kb"] += kb_by_lang.get(skill, 0)
            s["repos"].add(name)
            s["commits"] += commits
            if tests:
                s["tests"] += 1
            if green is not None:
                s["ci_total"] += 1
                if green:
                    s["ci_green"] += 1

    previous: dict[str, Any] = {}
    if DEFAULT_OUTPUT.exists():
        try:
            data = json.loads(read_text(DEFAULT_OUTPUT))
            previous = {normalize(x["name"]): x for x in data.get("skills", [])}
        except Exception:
            previous = {}

    skills: list[dict[str, Any]] = []
    for name, s in stats.items():
        if normalize(name) in HIDDEN_SKILLS:
            continue
        display = RENAME_SKILLS.get(normalize(name), name)
        vol = min(1.0, s["kb"] / VOL_CAP_KB)
        pen = min(1.0, len(s["repos"]) / PEN_CAP_REPOS)
        act = min(1.0, s["commits"] / ACT_CAP_COMMITS)
        signals = []
        if s["ci_total"]:
            signals.append(s["ci_green"] / s["ci_total"])
        if len(s["repos"]):
            signals.append(s["tests"] / len(s["repos"]))
        depth = sum(signals) / len(signals) if signals else 0.5
        raw = 100 * (0.35 * vol + 0.25 * pen + 0.25 * act + 0.15 * depth)
        pct = int(round(raw / 5.0) * 5)
        pct = max(MIN_PCT, min(MAX_PCT, pct))
        prev = previous.get(normalize(name))
        skills.append({
            "name": display,
            "pct": pct,
            "kb": s["kb"],
            "repos": len(s["repos"]),
            "commits_90d": s["commits"],
            "ci_green_frac": round(s["ci_green"] / s["ci_total"], 2) if s["ci_total"] else None,
            "tests_frac": round(s["tests"] / len(s["repos"]), 2) if s["repos"] else 0,
            "new": prev is None,
        })

    skills.sort(key=lambda x: (-x["pct"], -x["repos"], x["name"]))
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "window_days": window_days,
        "repo_count": len(by_name),
        "skills": skills,
    }


def bar(pct: int, width: int = 10) -> str:
    filled = round(pct * width / 100.0)
    return "█" * filled + "░" * (width - filled)


def render_section(payload: dict[str, Any], top: int = TOP_N) -> str:
    lines = [
        f"_Skills mesurés automatiquement depuis les repos — preuves dans `skills.json`"
        f" · fenêtre {payload['window_days']} j · relevé {payload['generated_at'][:10]}_",
        "",
    ]
    for s in payload["skills"][:top]:
        flag = " 🆕" if s.get("new") else ""
        ci = f" · CI {int(s['ci_green_frac'] * 100)}% vert" if s["ci_green_frac"] is not None else ""
        lines.append(
            f"- **{s['name']}**{flag} `{bar(s['pct'])}` **{s['pct']}%**"
            f" — {s['repos']} repo(s) · {s['commits_90d']} commits {payload['window_days']}j{ci}"
        )
    rest = payload["skills"][top:]
    if rest:
        lines.append(f"- _+ {len(rest)} autres : {', '.join(x['name'] for x in rest)}_")
    return "\n".join(lines)


START_MARK = "<!-- KURO-SKILLS:START -->"
END_MARK = "<!-- KURO-SKILLS:END -->"


def update_readme(readme_path: Path, section: str) -> bool:
    text = readme_path.read_text(encoding="utf-8")
    block = f"{START_MARK}\n{section}\n{END_MARK}"
    if START_MARK in text and END_MARK in text:
        pre = text.split(START_MARK, 1)[0]
        post = text.split(END_MARK, 1)[1]
        new_text = pre + block + post
    elif START_MARK not in text:
        raise SystemExit(
            f"Marqueurs {START_MARK} absents de {readme_path}. "
            "Insérez-les une fois autour de la section Skills."
        )
    else:
        raise SystemExit(f"{START_MARK} présent sans {END_MARK} dans {readme_path}")
    if new_text == text:
        return False
    readme_path.write_text(new_text, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Skills vérifiés Kuro")
    parser.add_argument("--docs", type=Path, default=DEFAULT_DOCS)
    parser.add_argument("--readme", type=Path, default=DEFAULT_README)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--window-days", type=int, default=WINDOW_DAYS)
    parser.add_argument("--top", type=int, default=TOP_N)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-readme", action="store_true")
    args = parser.parse_args()

    payload = build_payload(args.docs, args.window_days)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    if not args.no_readme:
        changed = update_readme(args.readme, render_section(payload, args.top))
        print(f"[{'+' if changed else '='}] README {args.readme}" + (" mis à jour" if changed else " inchangé"))
    print(f"[+] {len(payload['skills'])} skills détectés dans {payload['repo_count']} repos -> {args.output}")
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(render_section(payload, args.top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
