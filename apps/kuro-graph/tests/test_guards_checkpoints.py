import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH = ROOT / "apps" / "kuro-graph"
sys.path.insert(0, str(GRAPH))

import utils
from state import new_state
from nodes_daily import node_publish


def _flaky_node(state):
    # Echoue une fois puis reussit : simule retry.
    n = int(state.get("steps", {}).get("_flaky", {}).get("tries", 0))
    steps = dict(state.get("steps", {}))
    if n == 0:
        steps["_flaky"] = {"tries": 1}
        steps["flaky_node"] = {"ok": False, "detail": "first fail"}
        return {**state, "steps": steps}
    steps["flaky_node"] = {"ok": True, "detail": "second ok"}
    return {**state, "steps": steps}


_flaky_node.__name__ = "flaky_node"


def test_retry_second_try_marks_retried():
    s = new_state()
    wrapped = utils.with_retry(_flaky_node, attempts=2)
    out = wrapped(s)
    assert out["steps"]["flaky_node"]["ok"] is True
    assert out["steps"]["flaky_node"]["retried"] is True
    assert out["retries"]["flaky_node"] == 1


def test_timed_records_duration():
    def _fast(state):
        return state

    _fast.__name__ = "fast_node"
    out = utils.timed(_fast)(new_state())
    assert "fast_node" in out["metrics"]["durations"]


def test_checkpoint_roundtrip(tmp_path):
    p = tmp_path / "ck.sqlite3"
    s = new_state(write=False, dry_run=True)
    s["thread_id"] = "t1"
    assert utils.save_checkpoint(p, "t1", s) is True
    loaded = utils.load_checkpoint(p, "t1")
    assert loaded is not None
    assert loaded["thread_id"] == "t1"
    assert loaded["state_version"] == 3
    assert utils.load_checkpoint(p, "missing") is None


def test_approval_gates():
    dry = new_state(write=True, dry_run=True)
    dry["human_approved"] = True
    assert utils.approval_required(dry) is False
    assert utils.is_approved(dry) is False
    full = new_state(write=True, dry_run=False)
    full["human_approved"] = False
    # approval_required depend des vacances ; si vacances ON, False attendu.
    # Dans les deux cas is_approved reste False sans flag.
    assert utils.is_approved(full) is False
    full["human_approved"] = True
    # Si pas en vacances, approved. Si vacances, False (lecture seule forcee).
    if utils.vacances_on():
        assert utils.is_approved(full) is False
    else:
        assert utils.is_approved(full) is True


def test_publish_needs_approval():
    s = new_state(write=True, dry_run=False)
    s["human_approved"] = False
    out = node_publish({**s, "doctor_ok": True, "truth_ok": True})
    assert out["steps"]["publish"]["ok"] is True
    detail = out["steps"]["publish"]["detail"]
    assert ("approval" in detail) or ("vacances" in detail) or ("deferred" in detail)


def test_merge_metrics_shape():
    s = new_state()
    s["metrics"] = {"durations": {"a": 0.1}}
    s["retries"] = {"a": 1}
    m = utils.merge_metrics(s)
    assert m["durations"] == {"a": 0.1}
    assert m["retries"] == {"a": 1}
    assert m["fails"] == 0
