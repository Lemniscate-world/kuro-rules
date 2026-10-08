#!/usr/bin/env python3
"""kuro_omnigraph_branch.py — harvester R69 sur branches isolees (phase 2).

Un run harvester stage ses decouvertes (delta JSONL) sur une branche
Omnigraph isolee. Rien ne touche `main` sans review humaine explicite :
`merge` exige `--i-reviewed "<motif>"`, sinon refus (exit 2).

Sous-commandes :
  harvest --store GRAPH --branch NAME --delta FILE [--from main]
  diff    --store GRAPH --branch NAME [--from main] [--limit N]
  merge   --store GRAPH --branch NAME [--into main] --i-reviewed "..."

Garde-fous :
  - delta valide : JSON par ligne, forme noeud {"type","data.slug"} ou
    edge {"edge","from","to"} ; cles privees refusees (R111 : montants,
    tokens, secrets) meme dans un delta.
  - binaire resolu via --bin, OMNIGRAPH_BIN, ou PATH (shutil.which).
  - zero reseau, cross-platform (R93) : pathlib + subprocess liste d'args.

Usage :
  python scripts/kuro_omnigraph_branch.py harvest --store g.omni --branch agent/h1 --delta d.jsonl
  python scripts/kuro_omnigraph_branch.py diff --store g.omni --branch agent/h1
  python scripts/kuro_omnigraph_branch.py merge --store g.omni --branch agent/h1 --i-reviewed "vu: 1 decision"
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess  # nosec B404 : wrapper CLI, jamais shell=True (voir run_omnigraph)
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_paths import confine_arg  # noqa: E402

# Cles interdites dans un delta (R111 : financier + secrets, meme en staging).
PRIVATE_KEYS = {
    "amount", "expenses", "revenues", "cash", "mrr", "burn", "runway",
    "cac", "ltv", "arpu", "token", "secret", "password", "api_key", "apikey",
}


class HarvestError(Exception):
    pass


def resolve_bin(explicit: str | None = None) -> str:
    if explicit:
        return explicit
    from_env = os.environ.get("OMNIGRAPH_BIN", "").strip()
    if from_env:
        return from_env
    found = shutil.which("omnigraph")
    if found:
        return found
    raise HarvestError(
        "Binaire omnigraph introuvable. Passer --bin PATH ou OMNIGRAPH_BIN. "
        "Windows : gh release download v0.11.0 --repo ModernRelay/omnigraph "
        '--pattern "omnigraph-windows-x86_64.zip".'
    )


def run_omnigraph(bin_path: str, args: list[str]) -> str:
    try:
        proc = subprocess.run(  # nosec B603 : forme liste sans shell, binaire explicite
            [bin_path, *args],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=300,
        )
    except FileNotFoundError as exc:
        raise HarvestError(f"Binaire inexecutable : {bin_path}") from exc
    if proc.returncode != 0:
        raise HarvestError(f"omnigraph {' '.join(args)} a echoue : {proc.stderr.strip()}")
    return proc.stdout


def _private_keys_in(obj: object, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in PRIVATE_KEYS:
                hits.append(f"{path}.{key}")
            hits.extend(_private_keys_in(value, f"{path}.{key}"))
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            hits.extend(_private_keys_in(value, f"{path}[{i}]"))
    return hits


def parse_delta(text: str) -> list[dict]:
    """Valide un delta JSONL. Leve HarvestError avec l'index de ligne."""
    records: list[dict] = []
    lines = (text or "").splitlines()
    if not any(line.strip() for line in lines):
        raise HarvestError("Delta vide : rien a stager.")
    for i, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise HarvestError(f"Ligne {i} : JSON invalide ({exc})") from exc
        if not isinstance(record, dict):
            raise HarvestError(f"Ligne {i} : objet JSON requis.")
        if "edge" in record:
            for key in ("edge", "from", "to"):
                if not isinstance(record.get(key), str) or not record[key].strip():
                    raise HarvestError(f"Ligne {i} : edge requiert '{key}' non vide.")
        elif "type" in record:
            data = record.get("data")
            if not isinstance(record["type"], str) or not isinstance(data, dict):
                raise HarvestError(f"Ligne {i} : noeud requiert type str + data objet.")
            if not isinstance(data.get("slug"), str) or not data["slug"].strip():
                raise HarvestError(f"Ligne {i} : noeud requiert data.slug non vide.")
        else:
            raise HarvestError(f"Ligne {i} : ni noeud (type/data) ni edge (edge/from/to).")
        hits = _private_keys_in(record.get("data", record))
        if hits:
            raise HarvestError(f"Ligne {i} : cles privees refusees (R111) : {', '.join(hits)}")
        records.append(record)
    if not records:
        raise HarvestError("Delta vide : rien a stager.")
    return records


def entity_key(record: dict) -> str:
    if "edge" in record:
        return f"edge:{record['edge']}:{record.get('id', '')}"
    return f"{record.get('type', '?')}:{record.get('id', '')}"


def diff_entities(main_lines: list[str], branch_lines: list[str]) -> dict:
    """Compare deux exports JSONL. Logique pure."""
    def keys(lines: list[str]) -> set[str]:
        out: set[str] = set()
        for line in lines:
            if line.strip():
                out.add(entity_key(json.loads(line)))
        return out
    main_keys, branch_keys = keys(main_lines), keys(branch_lines)
    added = sorted(branch_keys - main_keys)
    removed = sorted(main_keys - branch_keys)
    return {"added": added, "removed": removed,
            "added_count": len(added), "removed_count": len(removed)}


def check_reviewed(reason: str | None) -> str:
    reason = (reason or "").strip()
    if not reason:
        raise HarvestError(
            "Merge refuse : review humaine requise. "
            'Relire le diff puis repasser --i-reviewed "<motif>".'
        )
    return reason


def cmd_harvest(bin_path: str, store: str, branch: str, delta: Path, from_branch: str) -> str:
    records = parse_delta(Path(delta).read_text(encoding="utf-8"))
    run_omnigraph(bin_path, ["branch", "create", branch, "--from", from_branch, "--store", store])
    run_omnigraph(bin_path, ["load", "--data", str(delta), "--mode", "append",
                             "--branch", branch, store])
    return f"[OK] Branche {branch} depuis {from_branch} : {len(records)} entites stagees."


def cmd_diff(bin_path: str, store: str, branch: str, from_branch: str, limit: int) -> str:
    main_out = run_omnigraph(bin_path, ["export", "--store", store, "--branch", from_branch])
    branch_out = run_omnigraph(bin_path, ["export", "--store", store, "--branch", branch])
    result = diff_entities(main_out.splitlines(), branch_out.splitlines())
    lines = [f"[DIFF] {branch} vs {from_branch} : "
             f"+{result['added_count']} -{result['removed_count']}"]
    for key in result["added"][:limit]:
        lines.append(f"  + {key}")
    for key in result["removed"][:limit]:
        lines.append(f"  - {key}")
    return "\n".join(lines)


def cmd_merge(bin_path: str, store: str, branch: str, into: str, reason: str | None) -> str:
    motif = check_reviewed(reason)
    run_omnigraph(bin_path, ["branch", "merge", branch, "--into", into, "--store", store])
    return f"[OK] {branch} merge dans {into} (review : {motif})."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harvester Omnigraph sur branches.")
    parser.add_argument("--bin", default=None)
    parser.add_argument("--store", required=True)
    parser.add_argument("--branch", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_harvest = sub.add_parser("harvest")
    p_harvest.add_argument("--delta", required=True)
    p_harvest.add_argument("--from", dest="from_branch", default="main")
    p_diff = sub.add_parser("diff")
    p_diff.add_argument("--from", dest="from_branch", default="main")
    p_diff.add_argument("--limit", type=int, default=20)
    p_merge = sub.add_parser("merge")
    p_merge.add_argument("--into", default="main")
    p_merge.add_argument("--i-reviewed", default=None)
    args = parser.parse_args(argv)
    try:
        bin_path = resolve_bin(args.bin)
        if args.cmd == "harvest":
            print(cmd_harvest(bin_path, args.store, args.branch,
                              confine_arg(args.delta, ROOT), args.from_branch))
        elif args.cmd == "diff":
            print(cmd_diff(bin_path, args.store, args.branch, args.from_branch, args.limit))
        elif args.cmd == "merge":
            print(cmd_merge(bin_path, args.store, args.branch, args.into, args.i_reviewed))
    except HarvestError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
