#!/usr/bin/env python3
"""Shim repo (dev) : le generateur dashboard vit dans `kuro_dashboard` (src/).

Contexte repo : `python dashboard/generate_dashboard.py` et run-dashboard.ps1
continuent de fonctionner a l identique (dossiers repo par defaut).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard.scan import *  # noqa: F401,F403 (parite generate_dashboard)
from kuro_dashboard.scan import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
