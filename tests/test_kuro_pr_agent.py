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
    monkeypatch.setattr(ka, "pr_commands", lambda *a: [])
    monkeypatch.setattr(ka, "failing_checks", lambda *a: [])
    assert ka.process_pr("o/r", _pr(), "t", True) == ["o/r#7 (fix/x)", "  verte"]


def test_process_pr_branche_protegee():
    assert ka.process_pr("o/r", _pr(head="main"), "t", True) == [
        "o/r#7 (main) : branche protegee, ignore"]


def test_fixable_push_gardes_sans_reseau(monkeypatch, tmp_path):
    monkeypatch.setattr(ka.P, "STORE", tmp_path / "p.json")
    assert ka.fixable_push("o/r", _pr(), "mypy", "", "", "t", True, True) == \
        "classe non auto-reparable"
    assert ka.fixable_push("o/r", _pr(fork=True), "lint_dead", "", "", "t", True, True) == \
        "fork : push refuse, commentaire seul"
    msg = ka.fixable_push("o/r", _pr(), "lint_dead", "detail", "", "t", False, False)
    assert msg.startswith("proposition P-") and "kuro-auto" in msg
    assert ka.fixable_push("o/r", _pr(), "lint_dead", "", "", "t", False, True) == \
        "dry-run : lint_dead serait pousse sur fix/x"


def test_maybe_automerge_refus_sans_reseau(monkeypatch):
    monkeypatch.setattr(ka, "failing_checks", lambda *a: [])
    base = {"node_id": "N", "number": 1, "additions": 10,
            "user": {"login": "Lemniscate-world"}, "head": {"sha": "s"}}
    assert ka.maybe_automerge("o/r", dict(base, labels=[]), "t", True) is None
    assert ka.maybe_automerge("o/r", dict(base, labels=[{"name": "valide"}, {"name": "do-not-merge"}]), "t", True) == \
        "merge refuse (do-not-merge)"
    big = dict(base, labels=[{"name": "valide"}], additions=500)
    assert ka.maybe_automerge("o/r", big, "t", True).startswith("merge refuse (diff")
    stranger = dict(base, labels=[{"name": "valide"}], user={"login": "inconnu"})
    assert ka.maybe_automerge("o/r", stranger, "t", True).startswith("merge refuse (auteur")
    ok = dict(base, labels=[{"name": "valide"}])
    assert ka.maybe_automerge("o/r", ok, "t", False) == "dry-run : merge envisageable (tout vert + label)"
