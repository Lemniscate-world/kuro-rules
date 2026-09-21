"""Registre ecosysteme Q7 : pilotes, ownership R87, sync guard R105.

Stdlib uniquement. Aucune ecriture dans les repos membres (audit lecture seule).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

OWNED_ORG_MARKERS = (
    "github.com/Lemniscate-world/",
    "github.com/Lemniscate-SHA-256/",
    "github.com/pbakaus/",
)

EXTERNAL_ORG_MARKERS = (
    "github.com/Demeter-Financial-Labs/",
)

PILOT_REPOS = ("LifeTrack", "Forma")

DOCUMENTS = Path.home() / "Documents"


def classify_remote(remote_url: str) -> str:
    """Pure : OWNED / EXTERNAL / UNKNOWN. Jamais d'exception."""
    url = (remote_url or "").strip()
    if not url:
        return "UNKNOWN"
    for marker in OWNED_ORG_MARKERS:
        if marker in url:
            return "OWNED"
    for marker in EXTERNAL_ORG_MARKERS:
        if marker in url:
            return "EXTERNAL"
    if "github.com" in url:
        return "UNKNOWN"
    return "UNKNOWN"


def classify_repo(repo_path: Path) -> tuple[str, str]:
    """Retourne (label, remote). Non-git ou erreur -> (UNKNOWN, '')."""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=15,
            encoding="utf-8", errors="replace",
        )
        remote = (r.stdout or "").strip() if r.returncode == 0 else ""
        return classify_remote(remote), remote
    except Exception:
        return "UNKNOWN", ""


def sync_scope(label: str) -> str:
    """R105 : OWNED=full, sinon redirector-only (AGENTS.md seul)."""
    return "full" if label == "OWNED" else "redirector-only"


def session_summary_head(repo_path: Path, max_chars: int = 2000) -> tuple[bool, str]:
    """Lit le debut de SESSION_SUMMARY.md. Retourne (ok, texte_ou_erreur)."""
    target = Path(repo_path) / "SESSION_SUMMARY.md"
    try:
        text = target.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return False, f"unreadable SESSION_SUMMARY.md: {exc}"
    lines = text.splitlines()[:40]
    head = "\n".join(lines)[:max_chars]
    if not head.strip():
        return False, "SESSION_SUMMARY.md vide"
    return True, head


def pilot_paths(documents: Path | None = None) -> list[Path]:
    base = Path(documents) if documents else DOCUMENTS
    return [base / name for name in PILOT_REPOS]


def build_impact(change_desc: str, repos: dict[str, Any]) -> dict[str, Any]:
    """Matrice d'impact R105 : impacted, breaking, matrix_updated, cross_issue."""
    impacted = sorted(repos.keys())
    breaking = "breaking" in (change_desc or "").lower()
    return {
        "change": (change_desc or "")[:300],
        "impacted": impacted,
        "breaking": breaking,
        "matrix_updated": False,
        "cross_issue": "",
    }
