#!/usr/bin/env python3
"""kuro_omnigraph_export.py — export lecture seule vers Omnigraph (R86/R112).

Lit le portfolio PUBLIC (Epingle_Projets.md + projects.txt) et produit un
JSONL chargeable dans Omnigraph (`init` + `load --mode overwrite`).
Phase 1 : noeuds uniquement, aucune edge inventee. Zero reseau, zero LLM.

Fichiers PRIVES jamais lus (R101/R111) : finances/strategie/pipeline
`*.local.json`, `PLAN.md`, `SESSION_SUMMARY.md`, `docs/tracking/`,
`SYNC_BACKUPS/`, canaux Discord locaux. Toute tentative leve ExportError.

Cross-platform (R93) : pathlib + utf-8, pas de binaire externe.

Usage :
  python scripts/kuro_omnigraph_export.py --out export.jsonl
  python scripts/kuro_omnigraph_export.py --out export.jsonl --write-assets out_dir
  python scripts/kuro_omnigraph_export.py --out export.jsonl --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_EPINGLE = ROOT_DIR / "Epingle_Projets.md"
DEFAULT_PROJECTS = ROOT_DIR / "projects.txt"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_paths import confine_arg  # noqa: E402

# Basenames ou motifs refuses meme si demandes explicitement (R101/R111).
DENY_BASENAMES = {
    "finances.local.json",
    "strategy.local.json",
    "pipeline.local.json",
    "strategy_decisions.local.json",
    "proposals.local.json",
    "watchdog.local.json",
    "cowork_last_pick.local.json",
    "coverage.local.json",
    "kuro_discord_channels.local.json",
    "kuro_discord_map.local.json",
    "kuro_discord_rename.local.json",
    "PLAN.md",
    "SESSION_SUMMARY.md",
    "LAUNCH_POSTS.md",
    "decision-memo.md",
    "acquisition_tracker.md",
}
DENY_DIR_PARTS = {"docs", "SYNC_BACKUPS", "research", "concept"}
DENY_TRACKING_NAMES = {"tracking"}

SCHEMA_PG = """node Project {
  slug: String @key
  name: String
  status: String
  progress: I32
}

node Rule {
  slug: String @key
  title: String
}

node Decision {
  slug: String @key
  statement: String
}

edge Follows: Project -> Rule
edge Makes: Project -> Decision
"""

QUERIES_GQ = """query active_projects() {
  match {
    $p: Project { status: "Actif" }
  }
  return { $p.name as project, $p.slug as slug }
  order { project asc }
}

query projects_for_rule($rule: String) {
  match {
    $proj: Project
    $r: Rule { slug: $rule }
    $proj follows $r
  }
  return { $proj.name as project, $proj.status as status }
  order { project asc }
}
"""

RULE_NODES = (
    ("r111", "Local Finance Data 100% locales (R111)"),
    ("r93", "Cross-Platform Reliability Windows Linux (R93)"),
    ("r112", "Standard Tooling Agent-Reach + Codebase-Memory (R112)"),
)

_ROW_SPLIT = re.compile(r"\|")
_PROGRESS_NUM = re.compile(r"(\d{1,3})")


class ExportError(Exception):
    pass


def assert_public_path(path: Path) -> Path:
    resolved = Path(path)
    name = resolved.name
    if name in DENY_BASENAMES or name.endswith(".local.json"):
        raise ExportError(f"Refuse (prive R101/R111) : {path}")
    parts = {p for p in resolved.parts}
    if parts & DENY_DIR_PARTS and "tracking" in parts:
        raise ExportError(f"Refuse (dossier prive) : {path}")
    if "SYNC_BACKUPS" in parts:
        raise ExportError(f"Refuse (dossier prive) : {path}")
    return resolved


def slugify(name: str) -> str:
    slug = (name or "").strip().lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "projet"


def _clean_cell(cell: str) -> str:
    return cell.replace("**", "").strip()


def parse_epingle_projects(text: str) -> list[dict]:
    """Parse UNIQUEMENT les tableaux `| Projet | Progression | Statut | ... |`.

    Logique pure. Le tableau des livrables (R90, `Projet | Section | ...`)
    est ignore via gating sur l'en-tete. Progression `--` -> 0.
    """
    projects: list[dict] = []
    in_project_table = False
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_project_table = False
            continue
        if "---" in stripped:
            continue
        cells = [_clean_cell(c) for c in _ROW_SPLIT.split(stripped.strip("|"))]
        if len(cells) < 3:
            continue
        lowered = [c.lower() for c in cells]
        if lowered[0] == "projet":
            # Gating : seul l'en-tete Projet|Progression|Statut active le parse.
            in_project_table = "progression" in lowered[1] and "statut" in lowered[2]
            continue
        if not in_project_table:
            continue
        name = cells[0].strip()
        progress_raw = cells[1] if len(cells) > 1 else ""
        status = cells[2] if len(cells) > 2 else ""
        match = _PROGRESS_NUM.search(progress_raw or "")
        progress = int(match.group(1)) if match else 0
        progress = max(0, min(100, progress))
        projects.append(
            {"name": name, "progress": progress, "status": status or "Inconnu"}
        )
    return projects


def read_projects_txt(path: Path) -> list[str]:
    assert_public_path(path)
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as exc:
        raise ExportError(f"projects.txt introuvable : {path}") from exc
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def build_records(
    epingle_projects: list[dict], tracked: list[str] | None = None
) -> list[dict]:
    """Construit les enregistrements JSONL (noeuds uniquement, phase 1)."""
    records: list[dict] = []
    seen: set[str] = set()
    for entry in epingle_projects or []:
        name = str(entry.get("name", "")).strip()
        if not name:
            continue
        slug = slugify(name)
        if slug in seen:
            continue
        seen.add(slug)
        try:
            progress = int(entry.get("progress", 0))
        except (TypeError, ValueError):
            progress = 0
        records.append(
            {
                "type": "Project",
                "data": {
                    "slug": slug,
                    "name": name,
                    "status": str(entry.get("status", "Inconnu")),
                    "progress": max(0, min(100, progress)),
                },
            }
        )
    for slug, title in RULE_NODES:
        records.append({"type": "Rule", "data": {"slug": slug, "title": title}})
    return records


def write_jsonl(records: list[dict], path: Path) -> int:
    lines = [json.dumps(r, ensure_ascii=False) for r in (records or [])]
    Path(path).write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return len(lines)


def write_assets(directory: Path) -> dict[str, Path]:
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    schema_path = target / "schema.pg"
    queries_path = target / "queries.gq"
    schema_path.write_text(SCHEMA_PG, encoding="utf-8")
    queries_path.write_text(QUERIES_GQ, encoding="utf-8")
    return {"schema": schema_path, "queries": queries_path}


def run_export(epingle: Path, projects_txt: Path, out: Path) -> dict:
    assert_public_path(epingle)
    assert_public_path(projects_txt)
    assert_public_path(out)
    text = Path(epingle).read_text(encoding="utf-8")
    epingle_projects = parse_epingle_projects(text)
    try:
        tracked = read_projects_txt(projects_txt)
    except ExportError:
        tracked = []
    records = build_records(epingle_projects, tracked)
    count = write_jsonl(records, out)
    kinds: dict[str, int] = {}
    for record in records:
        kinds[str(record.get("type", "?"))] = kinds.get(str(record.get("type", "?")), 0) + 1
    return {
        "out": str(out),
        "lines": count,
        "projects": kinds.get("Project", 0),
        "rules": kinds.get("Rule", 0),
        "tracked": len(tracked),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Export public Epingle -> JSONL Omnigraph.")
    parser.add_argument("--epingle", default=str(DEFAULT_EPINGLE))
    parser.add_argument("--projects", default=str(DEFAULT_PROJECTS))
    parser.add_argument("--out", required=True)
    parser.add_argument("--write-assets", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        stats = run_export(confine_arg(args.epingle, ROOT_DIR, "Epingle_Projets.md"),
                           confine_arg(args.projects, ROOT_DIR, "projects.txt"),
                           confine_arg(args.out, ROOT_DIR))
        if args.write_assets:
            assets = write_assets(confine_arg(args.write_assets, ROOT_DIR))
            stats["schema"] = str(assets["schema"])
            stats["queries"] = str(assets["queries"])
    except ExportError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(stats, ensure_ascii=False))
    else:
        print(
            "[OK] Export %d lignes (%d projets, %d regles) -> %s"
            % (stats["lines"], stats["projects"], stats["rules"], stats["out"])
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
