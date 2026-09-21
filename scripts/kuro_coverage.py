#!/usr/bin/env python3
"""kuro_coverage.py — ou sont les trous de tests, et quoi ecrire (100% local).

Deux vitesses :
  1. Statique (defaut, tout le portfolio, secondes) : pour chaque repo Python,
     mappe modules sources -> fichiers de tests (test_<mod>.py / <mod>_test.py).
     Sort les modules sans test, tries par taille decroissante.
  2. Mesuree (--repo NOM --run, minutes) : lance pytest --cov dans UN repo,
     parse coverage.json -> fichiers les moins couverts + lignes non couvertes.
     Resultat memorise dans coverage.local.json (gitignore) pour l'Oracle.

Usage:
    python scripts/kuro_coverage.py [--json]
    python scripts/kuro_coverage.py --repo OpenQuant --run [--timeout 600]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))
DOCS_DIR = ROOT_DIR.parent
COVERAGE_FILE = ROOT_DIR / "coverage.local.json"

SKIP_DIRS = {".git", "venv", "node_modules", "dist", "build",
             "__pycache__", ".hypothesis", ".pytest_cache", ".mypy_cache",
             ".ruff_cache", "htmlcov", ".benchmarks",
             "site-packages", "target", "outputs", "workspace", "sandbox"}
SKIP_PREFIXES = (".venv",)  # .venv, .venv310, ...
SKIP_FILES = {"setup.py", "conftest.py", "__init__.py"}


def _skipped(parts) -> bool:
    return any(p in SKIP_DIRS or p.startswith(SKIP_PREFIXES) for p in parts)


def source_modules(repo: Path) -> list[Path]:
    """Modules sources .py hors tests, venv et bruit."""
    out = []
    try:
        candidates = list(repo.rglob("*.py"))
    except OSError:
        return []
    for f in candidates:
        if _skipped(f.parts):
            continue
        if f.name in SKIP_FILES:
            continue
        stem = f.stem
        if stem.startswith("test_") or stem.endswith("_test"):
            continue
        if "test" in [p.lower() for p in f.parent.parts[-2:]]:
            continue
        out.append(f)
    return out


def test_stems(repo: Path) -> set[str]:
    """Stems couverts : test_<mod>.py ou <mod>_test.py, n'importe ou."""
    stems = set()
    try:
        candidates = list(repo.rglob("test_*.py")) + list(repo.rglob("*_test.py"))
    except OSError:
        return set()
    for f in candidates:
        if _skipped(f.parts):
            continue
        s = f.stem
        if s.startswith("test_"):
            stems.add(s[5:])
        elif s.endswith("_test"):
            stems.add(s[:-5])
    return stems


def file_lines(path: Path) -> int:
    try:
        with path.open(encoding="utf-8", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def test_file_count(repo: Path) -> int:
    """Nombre de fichiers test_*.py / *_test.py hors bruit."""
    try:
        candidates = list(repo.rglob("test_*.py")) + list(repo.rglob("*_test.py"))
    except OSError:
        return 0
    return sum(1 for f in candidates if not _skipped(f.parts))


def static_gaps(repo: Path, limit: int = 10) -> dict:
    """Modules sans test, tries par taille. Pur (hors lecture disque)."""
    mods = source_modules(repo)
    covered = test_stems(repo)
    untested = [{"path": str(m.relative_to(repo)).replace("\\", "/"),
                 "lines": file_lines(m), "pct": 0}
                for m in mods if m.stem not in covered]
    untested.sort(key=lambda u: -u["lines"])
    return {"name": repo.name,
            "modules": len(mods),
            "tested": len(mods) - len(untested),
            "untested": untested[:limit],
            "untested_total": len(untested)}


def static_payload(limit: int = 10) -> dict:
    import kuro_metrics
    repos = kuro_metrics.detect_git_repositories()
    rows = []
    for r in repos:
        if r.name.lower().endswith("-fork"):
            continue  # forks tiers : pas d'exigence de tests maison
        info = static_gaps(r, limit)
        if info["modules"] == 0:
            continue  # non Python : hors sujet couverture
        rows.append(info)
    rows.sort(key=lambda x: (-x["untested_total"], x["name"].lower()))
    return {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "repos": rows}


def parse_coverage_json(data: dict, limit: int = 10) -> list[dict]:
    """Extrait les fichiers les moins couverts d'un coverage.json."""
    files = []
    for path, info in (data.get("files") or {}).items():
        summary = info.get("summary") or {}
        pct = summary.get("percent_covered", 100)
        if pct >= 100:
            continue
        missing = info.get("missing_lines") or []
        files.append({"path": path, "pct": round(float(pct), 1),
                      "missing": len(missing),
                      "lines": (",".join(str(n) for n in missing[:6]))})
    files.sort(key=lambda f: (f["pct"], -f["missing"]))
    return files[:limit]


def run_repo(repo_name: str, timeout: int = 600) -> dict:
    """Lance pytest --cov dans UN repo, parse, memorise. Lecture+ecriture bornees."""
    repo = DOCS_DIR / repo_name
    if not repo.is_dir():
        return {"name": repo_name, "error": "repo introuvable"}
    out_file = repo / ".kuro_cov.json"
    cmd = [sys.executable, "-m", "pytest", "--cov=.", "--cov-report=json:" + str(out_file),
           "-q", "-p", "no:cacheprovider", "-x", "--timeout=300"]
    # pytest-timeout absent partout : on s'appuie sur timeout global du subprocess.
    cmd = [c for c in cmd if not c.startswith("--timeout")]
    try:
        proc = subprocess.run(cmd, cwd=repo, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return {"name": repo_name, "error": f"timeout {timeout}s depasse"}
    except Exception as exc:
        return {"name": repo_name, "error": str(exc)[:120]}
    try:
        data = json.loads(out_file.read_text(encoding="utf-8"))
    except Exception:
        tail = (proc.stdout + proc.stderr)[-500:]
        return {"name": repo_name, "error": "pas de coverage.json", "log": tail}
    finally:
        for junk in (out_file, repo / ".coverage"):
            try:
                junk.unlink()
            except OSError:
                pass
    total = (data.get("totals") or {}).get("percent_covered", 0)
    entry = {"name": repo_name,
             "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
             "pct_total": round(float(total), 1),
             "untested": [{"path": f["path"], "pct": f["pct"],
                           "missing": f["missing"], "lines": f["lines"]}
                          for f in parse_coverage_json(data)]}
    save_entry(entry)
    return entry


def run_all(timeout: int = 240, only: set[str] | None = None, limit: int = 0) -> list[dict]:
    """Mesure pytest --cov sur TOUS les repos Python avec tests, avec sauvegarde incrementale.

    Chaque repo est borne par `timeout` (defaut 4 min) : timeout, erreur ou
    absence de tests -> entree d'echec explicite, on continue. Le resultat
    partiel est sauve a chaque repo (un crash ne perd rien).
    """
    import kuro_metrics
    results: list[dict] = []
    done = 0
    for repo in kuro_metrics.detect_git_repositories():
        if repo.name.lower().endswith("-fork"):
            continue
        if only and repo.name.lower() not in only:
            continue
        if limit and done >= limit:
            break
        if test_file_count(repo) == 0:
            results.append({"name": repo.name, "skipped": "aucun fichier de test"})
            continue
        entry = run_repo(repo.name, timeout)
        done += 1
        if "error" in entry:
            results.append({"name": repo.name, "error": entry["error"]})
        else:
            results.append({"name": repo.name, "pct_total": entry["pct_total"],
                            "gaps": len(entry["untested"])})
    return results


def render_run_all(results: list[dict]) -> str:
    ok = [r for r in results if "pct_total" in r]
    lines = [f"Couverture mesuree : {len(ok)}/{len(results)} repos"]
    for r in sorted(ok, key=lambda x: x["pct_total"]):
        lines.append(f"  - {r['name']:<26} {r['pct_total']:>5}% · {r['gaps']} fichiers a couvrir")
    bad = [r for r in results if "pct_total" not in r]
    for r in bad[:10]:
        reason = r.get("error", r.get("skipped", "?"))
        lines.append(f"  - {r['name']:<26} NON MESURE : {reason}"[:120])
    if len(bad) > 10:
        lines.append(f"  - ... +{len(bad) - 10} autres non mesures")
    return "\n".join(lines)


def save_entry(entry: dict) -> None:
    try:
        data = json.loads(COVERAGE_FILE.read_text(encoding="utf-8"))
        repos = data.get("repos", []) if isinstance(data, dict) else []
    except Exception:
        repos = []
    repos = [r for r in repos if str(r.get("name", "")).lower() != entry["name"].lower()]
    repos.append(entry)
    COVERAGE_FILE.write_text(json.dumps(
        {"generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
         "repos": repos}, indent=2, ensure_ascii=False), encoding="utf-8")


def render_static(payload: dict) -> str:
    lines = [f"Trous de tests (statique, {len(payload['repos'])} repos Python) :"]
    for r in payload["repos"][:15]:
        if r["untested_total"] == 0:
            continue
        top = ", ".join(f"{u['path']} ({u['lines']}l)" for u in r["untested"][:3])
        lines.append(f"  - {r['name']:<26} {r['tested']}/{r['modules']} modules testes · "
                     f"a ecrire : {top}")
    lines.append("Mesure reelle : `python scripts/kuro_coverage.py --repo <nom> --run` "
                 "(pytest --cov, resultat en coverage.local.json pour l'Oracle).")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Trous de couverture du portfolio")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo", default="")
    ap.add_argument("--run", action="store_true", help="lance pytest --cov sur --repo")
    ap.add_argument("--run-all", action="store_true",
                    help="mesure pytest --cov sur TOUS les repos avec tests (long)")
    ap.add_argument("--only", default="", help="limite run-all : noms separes par virgule")
    ap.add_argument("--limit", type=int, default=0, help="limite run-all : N repos max (0 = tous)")
    ap.add_argument("--timeout", type=int, default=240,
                    help="plafond secondes par repo (defaut 240)")
    args = ap.parse_args()
    if args.run_all:
        only = {n.strip().lower() for n in args.only.split(",") if n.strip()} or None
        results = run_all(timeout=args.timeout, only=only, limit=args.limit)
        print(render_run_all(results))
        return 0
    if args.run and args.repo:
        entry = run_repo(args.repo, args.timeout)
        print(json.dumps(entry, indent=2, ensure_ascii=False))
        return 0 if "error" not in entry else 1
    payload = static_payload()
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else render_static(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
