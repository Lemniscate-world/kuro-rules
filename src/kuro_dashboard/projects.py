#!/usr/bin/env python3
"""projects.py — sensing git generique, zero convention maison requise.

Decouvre les depots git sous des racines (env KURO_PROJECTS_ROOTS, sinon
~/repos puis ~/Documents) et resume chacun : branche, fichiers sales,
dernier commit, avance/retard vs upstream. Zero dependance, jamais
d exception levee, resultats en cache 60 s (un refresh TUI ne doit pas
lancer 50x5 sous-processus git toutes les 2 secondes).

C est le socle "paquet generique" : le TUI et kuro-system s en servent
quand aucune base Kuro (convention maison) n est presente.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

CACHE_TTL = 60.0
_CACHE: dict[str, Any] = {"ts": 0.0, "roots": None, "repos": []}


def roots() -> list[Path]:
    """Racines scannees : env KURO_PROJECTS_ROOTS (os.pathsep) sinon defauts."""
    raw = os.environ.get("KURO_PROJECTS_ROOTS")
    if raw:
        return [Path(p.strip()).expanduser()
                for p in raw.split(os.pathsep) if p.strip()]
    home = Path.home()
    return [home / "repos", home / "Documents"]


def _git(path: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True, text=True, timeout=10,
            encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def scan_repo(path: Path) -> dict[str, Any]:
    """Resume d un depot (jamais d exception)."""
    name = path.name
    branch = _git(path, "branch", "--show-current") or ""
    dirty_raw = _git(path, "status", "--porcelain")
    dirty = len(dirty_raw.splitlines()) if dirty_raw else 0
    log = (_git(path, "log", "-1", "--format=%h %cs %s") or "").strip()
    ahead = behind = 0
    upstream = _git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    if upstream:
        counts = _git(path, "rev-list", "--left-right", "--count", f"HEAD...{upstream}")
        if counts:
            try:
                bwd, fwd = counts.split()
                behind, ahead = int(bwd), int(fwd)
            except Exception:
                pass
    return {"name": name, "path": str(path), "branch": branch, "dirty": dirty,
            "last": log[:90], "ahead": ahead, "behind": behind}


def discover(force: bool = False) -> list[dict[str, Any]]:
    """Tous les depots git sous les racines (cache 60 s, scan parallele)."""
    now = time.monotonic()
    if not force and _CACHE["repos"] and (now - _CACHE["ts"]) < CACHE_TTL:
        return _CACHE["repos"]
    targets: list[Path] = []
    seen: set[str] = set()
    for root in roots():
        try:
            if not root.is_dir():
                continue
            children = sorted([p for p in root.iterdir() if p.is_dir()],
                              key=lambda p: p.name.lower())
        except Exception:
            continue
        for child in children:
            try:
                key = str(child.resolve())
            except Exception:
                key = str(child)
            if key in seen or not (child / ".git").exists():
                continue
            seen.add(key)
            # worktree (.git fichier) : pointeur invalide hors machine -> skip
            if (child / ".git").is_file():
                continue
            targets.append(child)
    found: list[dict[str, Any]] = []
    if targets:
        try:
            from concurrent.futures import ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=8) as pool:
                found = list(pool.map(scan_repo, targets))
        except Exception:
            found = [scan_repo(t) for t in targets]
    _CACHE.update({"ts": now, "repos": found})
    return found


def summary() -> dict[str, Any]:
    """Compteurs + top sales (tries par dirty decroissant)."""
    repos = discover()
    dirty = [r for r in repos if r["dirty"] > 0]
    dirty.sort(key=lambda r: (-r["dirty"], r["name"].lower()))
    return {"count": len(repos), "dirty": len(dirty),
            "top": [{"name": r["name"], "branch": r["branch"],
                     "dirty": r["dirty"], "last": r["last"]} for r in dirty[:8]]}


def quick_lines(limit: int = 6) -> list[str]:
    """Section TUI : 1 ligne resume + sales (jamais d exception)."""
    try:
        info = summary()
    except Exception:
        return []
    lines = [f"PROJETS git : {info['count']} ({info['dirty']} sales)"]
    for entry in info["top"][: max(0, limit)]:
        branch = f" [{entry['branch']}]" if entry["branch"] else ""
        lines.append(f"  {entry['name']}{branch} +{entry['dirty']}")
    return lines
