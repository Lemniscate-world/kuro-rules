"""Garde R116 : les chemins de rapports ne doivent jamais dependre d un
nom de dossier hardcode (bug 2026-10-02 : "Kuro" capital = crash Linux,
invisible sur Windows insensible a la casse).

Contrat cross-repo (R105) : les rapports vivent a la racine du checkout Kuro,
derivee du fichier lui-meme.
"""

import importlib.util
import re
from pathlib import Path

import pytest

KURO_PKG = Path.home() / "Documents" / "kuro" / "kuro"
MODULES = {
    "kuro_epingle_sync": (KURO_PKG / "epingle_sync.py", "PENDING_UPDATE_PATH",
                          "EPINGLE_PENDING_UPDATE.md"),
    "kuro_r90_monitor": (KURO_PKG / "r90_monitor.py", "KURO_ROOT", None),
}


def _load(name, path):
    if not path.exists():
        pytest.skip("checkout Kuro absent (test local uniquement)")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_paths_inside_own_repo():
    for name, (path, attr, filename) in MODULES.items():
        mod = _load(name, path)
        target = getattr(mod, attr)
        if filename is not None:
            assert target.parent == path.parent.parent
            assert target.name == filename
        else:
            assert target == path.parent.parent


def test_no_hardcoded_checkout_name():
    for name, (path, _attr, _filename) in MODULES.items():
        if not path.exists():
            pytest.skip("checkout Kuro absent (test local uniquement)")
        source = path.read_text(encoding="utf-8")
        assert not re.search(r"/\s*['\"]Kuro['\"]\s*/", source), \
            f"nom de dossier hardcode dans {path.name} (bug 2026-10-02)"
