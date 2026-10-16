import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH = ROOT / "apps" / "kuro-graph"
sys.path.insert(0, str(GRAPH))

import pytest

from run_matrix import resolve_out, run_batch, TARGET_RUNS, default_out


def test_target_is_30():
    assert TARGET_RUNS == 30


def test_single_iteration_all_green():
    report = run_batch(1)
    assert report["ok"] is True
    assert report["green"] == 1
    names = set(report["iterations"][0]["scenarios"].keys())
    assert names == {"validation-pass", "validation-halt", "multirepo", "compile-4"}


def test_resolve_out_confined_to_repo():
    default = default_out()
    assert resolve_out("", default) == default
    assert resolve_out("logs/custom.json", default).name == "custom.json"
    with pytest.raises(ValueError):
        resolve_out("../../outside.json", default)
    outside_abs = str(Path(GRAPH.anchor) / "outside-repo-evil.json")
    with pytest.raises(ValueError):
        resolve_out(outside_abs, default)
