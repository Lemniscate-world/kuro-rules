"""Tests kuro_pr_agent — helpers purs (aucun reseau)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_pr_agent as ka  # noqa: E402


def test_run_id_from_url():
    url = "https://github.com/o/r/actions/runs/123456/job/789"
    assert ka.run_id_from_url(url) == 123456
    assert ka.run_id_from_url("https://example.com/x") is None
    assert ka.run_id_from_url("") is None


def test_already_commented(monkeypatch):
    comments = [{"body": "<!-- kuro-pr-agent --> run=11 bla"}]
    monkeypatch.setattr(ka, "api", lambda *a, **k: (200, comments))
    assert ka.already_commented("o/r", 1, 11, "t") is True
    assert ka.already_commented("o/r", 1, 22, "t") is False
    monkeypatch.setattr(ka, "api", lambda *a, **k: (500, None))
    assert ka.already_commented("o/r", 1, 11, "t") is False


def _pr(head="fix/x", fork=False, number=7, sha="abc"):
    return {"number": number,
            "head": {"ref": head, "sha": sha, "repo": {"fork": fork}}}


def test_process_pr_verte(monkeypatch):
    monkeypatch.setattr(ka, "failing_checks", lambda *a: [])
    assert ka.process_pr("o/r", _pr(), "t", True) == ["o/r#7 (fix/x) : verte"]


def test_process_pr_branche_protegee():
    assert ka.process_pr("o/r", _pr(head="main"), "t", True) == [
        "o/r#7 (main) : branche protegee, ignore"]


def test_fixable_push_gardes_sans_reseau():
    assert ka.fixable_push("o/r", "mypy", "", "", "t", "fix/x", False, True) == \
        "classe non auto-reparable"
    assert ka.fixable_push("o/r", "lint_dead", "", "", "t", "fix/x", True, True) == \
        "fork : push refuse, commentaire seul"
    assert ka.fixable_push("o/r", "lint_dead", "", "", "t", "fix/x", False, False) == \
        "dry-run : lint_dead serait pousse sur fix/x"
