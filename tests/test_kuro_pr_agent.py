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
    monkeypatch.setattr(ka, "review_comments", lambda *a: [])
    assert ka.process_pr("o/r", _pr(), "t", True) == ["o/r#7 (fix/x)", "  verte"]


def test_parse_suggestions():
    body = "Change ca :\n```suggestion\nx = 1\ny = 2\n```\nEt aussi :\n```suggestion\nz = 3\n```"
    out = ka.parse_suggestions(body)
    assert out == [["x = 1", "y = 2"], ["z = 3"]]
    assert ka.parse_suggestions("aucun bloc") == []
    assert ka.parse_suggestions("```suggestion\n   \n```") == []


def test_suggestion_range():
    assert ka.suggestion_range({"line": 10}) == (10, 10)
    assert ka.suggestion_range({"start_line": 4, "line": 6}) == (4, 6)
    assert ka.suggestion_range({"original_line": 7}) == (7, 7)
    assert ka.suggestion_range({}) == (0, 0)


def _agent_src():
    return (Path(__file__).resolve().parent.parent / "scripts" / "kuro_pr_agent.py").read_text(encoding="utf-8")


def test_constante_bot_unique():
    assert _agent_src().count('"github-actions[bot]"') == 1


def test_constante_cause_unique():
    assert _agent_src().count('"cause inconnue"') == 1


def test_apply_suggestion(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("l1\nl2\nl3\nl4\n", encoding="utf-8")
    assert ka.apply_suggestion(tmp_path, "a.py", 2, 3, ["n2", "n3"]) is True
    assert f.read_text(encoding="utf-8").splitlines() == ["l1", "n2", "n3", "l4"]
    assert ka.apply_suggestion(tmp_path, "a.py", 9, 9, ["x"]) is False
    assert ka.apply_suggestion(tmp_path, "../echappe.py", 1, 1, ["x"]) is False
    assert ka.apply_suggestion(tmp_path, "a.py", 1, 1, []) is False
    bad = tmp_path / "b.py"
    bad.write_text("ok = 1\n", encoding="utf-8")
    assert ka.apply_suggestion(tmp_path, "b.py", 1, 1, ["def broken(:"]) is False
    assert bad.read_text(encoding="utf-8") == "ok = 1\n"


def test_review_comments_filtre_bots(monkeypatch):
    data = [
        {"user": {"login": "sourcery-ai[bot]"}, "body": "nit"},
        {"user": {"login": "humain"}, "body": "ok"},
        {"user": {"login": "github-actions[bot]"}, "body": "x"},
        {"user": {"login": "coderabbitai[bot]"}, "body": "<!-- kuro-pr-agent --> y"},
    ]
    monkeypatch.setattr(ka, "api", lambda *a, **k: (200, data))
    out = ka.review_comments("o/r", 1, "t")
    assert [c["user"]["login"] for c in out] == ["sourcery-ai[bot]"]


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


def test_explain_external_connus_et_inconnu():
    cause, fix = ka.explain_external("SonarCloud Code Analysis")
    assert "Quality Gate" in cause and "SonarCloud" in fix
    cause, fix = ka.explain_external("SonarQube")
    assert "Quality Gate" in cause
    cause, fix = ka.explain_external("pre-commit")
    assert "pre-commit run" in fix
    assert ka.explain_external("Build") is None
    assert ka.explain_external("") is None


def test_check_annotations_parse_et_echec(monkeypatch):
    data = [
        {"path": "a.py", "start_line": 12, "annotation_level": "failure", "message": "x" * 300},
        {"path": None, "line": "bad", "message": None},
        "bruit",
    ]
    monkeypatch.setattr(ka, "api", lambda *a, **k: (200, data))
    out = ka.check_annotations("o/r", 99, "t")
    assert out[0] == {"path": "a.py", "line": 12, "level": "failure", "message": "x" * 200}
    assert out[1]["line"] == 0 and len(out) == 2
    assert ka.check_annotations("o/r", None, "t") == []
    monkeypatch.setattr(ka, "api", lambda *a, **k: (500, None))
    assert ka.check_annotations("o/r", 99, "t") == []


def test_format_annotations_compact():
    notes = [{"path": "a.py", "line": 1, "message": "m1"},
             {"path": "b.py", "line": 2, "message": "m2"},
             {"path": "c.py", "line": 3, "message": "m3"}]
    assert ka.format_annotations(notes) == "a.py:1 m1; b.py:2 m2; c.py:3 m3"
    assert ka.format_annotations(notes, limit=2) == "a.py:1 m1; b.py:2 m2"
    assert ka.format_annotations([]) == ""


def _api_sonar(url: str):
    if "annotations" in url:
        return (200, [{"path": "src/x.py", "start_line": 42,
                       "annotation_level": "warning", "message": "Duplicated block"}])
    if "/pulls/7/files" in url:
        return (200, [{"filename": "src/x.py", "additions": 10, "deletions": 2}])
    return (404, None)


def _pr_sonar():
    return {"number": 7, "head": {"ref": "fix/y", "sha": "abc", "repo": {"fork": False}}}


def _check_sonar():
    return {"id": 123, "name": "SonarCloud Code Analysis", "conclusion": "failure",
            "html_url": "https://sonarcloud.io/project/issues?id=x"}


def test_process_check_sonar_explique_sans_cause_inconnue(monkeypatch, tmp_path):
    monkeypatch.setattr(ka.P, "STORE", tmp_path / "p.json")
    monkeypatch.setattr(ka, "api", lambda m, url, *a, **k: _api_sonar(url))
    line = ka.process_check("o/r", _pr_sonar(), _check_sonar(), "t", False, False)
    assert "Quality Gate" in line
    assert "cause inconnue" not in line
    assert "fichiers: +10/-2 : src/x.py" in line
    assert "1 annotation(s): src/x.py:42 Duplicated block" in line
    assert line.startswith("SonarCloud Code Analysis [Quality Gate")


def test_process_check_externe_inconnu_garde_garde_fou(monkeypatch, tmp_path):
    monkeypatch.setattr(ka.P, "STORE", tmp_path / "p.json")
    monkeypatch.setattr(ka, "api", lambda *a, **k: (404, None))
    check = {"id": 9, "name": "MysteryCheck", "conclusion": "failure",
             "html_url": "https://example.com/checks/9"}
    line = ka.process_check("o/r", _pr_sonar(), check, "t", False, False)
    assert "cause inconnue" in line  # aucun log, ni annotation, ni explication : garde-fou garde
