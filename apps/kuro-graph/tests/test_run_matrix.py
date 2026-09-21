import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH = ROOT / "apps" / "kuro-graph"
sys.path.insert(0, str(GRAPH))

from run_matrix import run_batch, TARGET_RUNS


def test_target_is_30():
    assert TARGET_RUNS == 30


def test_single_iteration_all_green():
    report = run_batch(1)
    assert report["ok"] is True
    assert report["green"] == 1
    names = set(report["iterations"][0]["scenarios"].keys())
    assert names == {"validation-pass", "validation-halt", "multirepo", "compile-4"}
