import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH = ROOT / "apps" / "kuro-graph"
sys.path.insert(0, str(GRAPH))

from state import new_state
from nodes_validation import check_gate
from nodes_radar import route_radar
from nodes_daily import should_publish


def test_state_defaults():
    s = new_state(write=False, dry_run=True)
    assert s["state_version"] == 3
    assert s["fails"] == 0
    assert s["halted"] is False
    assert s["metrics"] == {"durations": {}}
    assert s["retries"] == {}
    assert s["human_approved"] is False


def test_gates_r115_thresholds():
    assert check_gate("fuzzer", {"detection_rate": 0.85})[0] is True
    assert check_gate("fuzzer", {"detection_rate": 0.5})[0] is False
    assert check_gate("stress", {"passed": 15, "total": 15, "crashes": 0, "false_positives": 0})[0] is True
    assert check_gate("stress", {"passed": 14, "total": 15, "crashes": 0, "false_positives": 0})[0] is False
    assert check_gate("combinatorial", {"overall": 0.9, "worst_family": 0.75})[0] is True
    assert check_gate("combinatorial", {"overall": 0.9, "worst_family": 0.5})[0] is False
    assert check_gate("oos", {"detected": 6, "total": 6, "fp_events": 5})[0] is True
    assert check_gate("oos", {"detected": 5, "total": 6, "fp_events": 0})[0] is False
    assert check_gate("benchmark", {"detection_gain_vs_best": 0.6})[0] is True
    assert check_gate("benchmark", {"detection_gain_vs_best": 0.2})[0] is False


def test_daily_publish_gate():
    s = new_state(write=True, dry_run=False)
    s = {**s, "doctor_ok": True, "truth_ok": True}
    assert should_publish(s) == "publish"
    s2 = {**s, "doctor_ok": False}
    assert should_publish(s2) == "end"
    s3 = new_state(write=False, dry_run=True)
    assert should_publish({**s3, "doctor_ok": True, "truth_ok": True}) == "end"


def test_radar_routing():
    assert route_radar({"radar_signals": []}) == "end"
    one = {"radar_signals": [{"title": "a", "llm_label": "discard"}]}
    assert route_radar(one) == "archive"
    two = {"radar_signals": [{"title": "a", "llm_label": "keep"}, {"title": "b", "llm_label": "keep"}]}
    assert route_radar(two) == "draft"
