#!/usr/bin/env python3
"""Shim repo (dev) : le snapshot systeme vit dans `kuro_dashboard` (src/).

Contexte installe (pip) : utilisez `kuro-system`.
Contexte repo : ce shim expose les memes noms qu avant (tests inchanges).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard.system import (  # noqa: E402
    DEFAULT_TOP_N,
    collect_system_snapshot,
    get_cached_snapshot,
    main,
    render,
)

__all__ = [
    "DEFAULT_TOP_N",
    "collect_system_snapshot",
    "get_cached_snapshot",
    "main",
    "render",
]

if __name__ == "__main__":
    sys.exit(main())
