#!/usr/bin/env python3
"""kuro_testhealth.py — sante des suites de tests sur tout le portfolio (100% local, lecture seule).

Adopte la discipline OpenQuant (conftest hermetique, regression-first,
recovery-paths testes) en version portfolio : au lieu d'executer 50 suites
(heures de calcul), scanne chaque repo git et rend un verdict deterministe :

  VERT   : tests presents + conftest hermetique + touche il y a < 30 j
  ORANGE : tests presents mais non hermetiques ou stables depuis >= 30 j
  ROUGE  : aucun test detecte

Hermetique = tests/conftest.py neutralise l'exterieur (cles API videes,
webhooks vides, fichiers prod rediriges vers tmp) a la maniere de
OpenQuant/tests/conftest.py (fixture autouse + monkeypatch).

Usage:
    python scripts/kuro_testhealth.py [--json] [--top 20]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))

STALE_DAYS = 30

# Motifs conftest hermetique (cles videes, monkeypatch, tmp, offline).
HERMETIC_MARKS = (
    'os.environ[',
    'monkeypatch',
    'tmp_path',
    'OFFLINE',
    'FORCE_ONLINE',
    'TEST_MODE',
    '_MODE"] = "0"',
    '_MODE\'] = \'0\'',
    '= ""',
)


def run_git(path: Path, *args: str) -> str:
    try:
        out = subprocess.run(
            ["git", *args], cwd=path, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def test_files(repo: Path) -> list[Path]:
    import kuro_coverage
    found = []
    try:
        all_tests = list(repo.rglob("test_*.py"))
    except OSError:
        return []
    for f in all_tests:
        if kuro_coverage._skipped(f.parts):
            continue
        found.append(f)
    return sorted(found)[:500]


def is_hermetic(repo: Path) -> bool:
    conf = repo / "tests" / "conftest.py"
    if not conf.exists():
        conf = repo / "conftest.py"
    if not conf.exists():
        return False
    try:
        text = conf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return sum(1 for m in HERMETIC_MARKS if m in text) >= 2


def last_tests_touch(repo: Path) -> str | None:
    out = run_git(repo, "log", "-1", "--format=%cI", "--", "tests", "test")
    return out.splitlines()[0].strip() if out else None


def days_since(iso: str | None) -> int | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


def assess(repo: Path) -> dict:
    files = test_files(repo)
    if not files:
        return {"name": repo.name, "verdict": "ROUGE", "tests": 0,
                "hermetic": False, "days_since_touch": None}
    herm = is_hermetic(repo)
    days = days_since(last_tests_touch(repo))
    verdict = "VERT" if herm and days is not None and days < STALE_DAYS else "ORANGE"
    return {"name": repo.name, "verdict": verdict, "tests": len(files),
            "hermetic": herm, "days_since_touch": days}


def build_payload() -> dict:
    import kuro_metrics
    repos = kuro_metrics.detect_git_repositories()
    projects = [assess(r) for r in repos]
    counts = {"VERT": 0, "ORANGE": 0, "ROUGE": 0}
    for p in projects:
        counts[p["verdict"]] += 1
    order = {"ROUGE": 0, "ORANGE": 1, "VERT": 2}
    projects.sort(key=lambda p: (order[p["verdict"]], p["name"].lower()))
    return {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "project_count": len(projects), "counts": counts, "projects": projects}


def render(payload: dict) -> str:
    c = payload["counts"]
    lines = [f"Sante tests portfolio ({payload['project_count']} repos) : "
             f"{c['VERT']} verts · {c['ORANGE']} orange · {c['ROUGE']} rouges"]
    for p in payload["projects"]:
        if p["verdict"] == "VERT":
            continue
        touch = "jamais" if p["days_since_touch"] is None else f"il y a {p['days_since_touch']}j"
        herm = "hermetique" if p["hermetic"] else "non hermetique"
        lines.append(f"  [{p['verdict']}] {p['name']:<26} {p['tests']:>3} tests · {herm} · {touch}")
    lines.append("Regle : tout ROUGE avec velocite > 0 doit ecrire ses premiers tests "
                 "avant toute feature (R102). Template : OpenQuant/tests/conftest.py.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sante des suites de tests du portfolio")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    payload = build_payload()
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else render(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
