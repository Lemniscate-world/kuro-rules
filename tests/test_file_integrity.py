"""Garde integrite (R116 + R41) : sources ni nulles ni amputees.

Motivation 2026-10-03 : src/kuro_dashboard/api.py retrouve ENTIEREMENT
rempli d octets nuls (17 Ko), masque par des .pyc perimes ; def
_llm_last_path supprimee par une edit, masquee pareil. Ces tests lisent
les OCTETS et le TEXTE SOURCES (insensibles au cache d import).
"""

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SOURCE_GLOBS = ["scripts/*.py", "src/kuro_dashboard/*.py", "tests/*.py",
                "dashboard/*.js", "dashboard/*.html", "dashboard/*.css"]


def _sources() -> list[Path]:
    out: list[Path] = []
    for pattern in SOURCE_GLOBS:
        out.extend(sorted(REPO.glob(pattern)))
    return out


def test_no_null_bytes():
    bad = [str(p.relative_to(REPO)) for p in _sources()
           if b"\x00" in p.read_bytes()]
    assert not bad, f"fichiers corrompus (octets nuls) : {bad}"


def test_critical_symbols_present_in_source():
    checks = {
        "scripts/kuro_llm.py": ["def _llm_last_path", "def _local_ollama",
                                "def _litellm_router", "def drain_queue"],
        "src/kuro_dashboard/api.py": ["def get_system", "def get_status",
                                      "class Handler"],
        "src/kuro_dashboard/tui.py": ["def watch", "def sec_brain"],
    }
    missing = []
    for rel, symbols in checks.items():
        source = (REPO / rel).read_text(encoding="utf-8")
        for sym in symbols:
            if sym not in source:
                missing.append(f"{rel}: {sym}")
    assert not missing, f"symboles critiques absents des sources : {missing}"
