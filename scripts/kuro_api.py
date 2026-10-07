#!/usr/bin/env python3
"""Shim repo (dev) : l API Kuro vit dans le paquet `kuro_dashboard` (src/).

Contexte installe (pip) : utilisez `kuro-dashboard` / `python -m kuro_dashboard`.
Contexte repo : ce shim expose les memes noms qu avant (tests + run-api.ps1
inchanges) et pointe l UI vers dashboard/ et le scan vers ce repo.
"""

import os
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent
sys.path.insert(0, str(_REPO / "src"))
sys.path.insert(0, str(_HERE))  # kuro_llm, kuro_finance, kuro_metrics, kuro_strategy
os.environ.setdefault("KURO_RULES_DIR", str(_REPO))
os.environ.setdefault("KURO_STATIC_DIR", str(_REPO / "dashboard"))

from kuro_dashboard.api import (  # noqa: E402
    DB_PATH,
    STATIC_FILES,
    Handler,
    KuroServer,
    answer_question,
    build_summary,
    db,
    get_alerts,
    get_finance,
    get_memory,
    get_metrics,
    get_project,
    get_projects,
    get_robot,
    get_sessions,
    get_status,
    get_strategy,
    get_system,
    main,
    rows,
)

__all__ = [
    "DB_PATH", "STATIC_FILES", "Handler", "KuroServer", "answer_question",
    "build_summary", "db", "get_alerts", "get_finance", "get_memory",
    "get_metrics", "get_project", "get_projects", "get_robot", "get_sessions",
    "get_status", "get_strategy", "get_system", "main", "rows",
]

if __name__ == "__main__":
    sys.exit(main())
