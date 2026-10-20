"""Tests du harness d evals deterministe (evals/eval_posts.py) - R102."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

import eval_posts  # noqa: E402


def test_dataset_golden_complet():
    """Le dataset reel doit etre non vide et passer a 100% (contrat CI)."""
    cases = eval_posts.load_cases()
    assert len(cases) >= 10, "dataset golden trop maigre"
    summary = eval_posts.evaluate(cases)
    assert summary["failed"] == 0, [
        r for r in summary["results"] if r["fails"]]
    assert summary["pass_rate"] == 1.0


def test_run_case_detecte_lint_absent():
    case = {"id": "x", "projet": "openquant", "lang": "fr",
            "themes": ["tests"], "text": "Texte sans mot muselle du tout.",
            "expect_lint_any": ["edge"]}
    res = eval_posts.run_case(case)
    assert res["fails"] and "lint attendu" in res["fails"][0]


def test_run_case_detecte_issue_absente():
    case = {"id": "x", "projet": "helium", "lang": "fr", "themes": ["tests"],
            "text": "Un post correct avec assez de longueur pour ne pas "
                    "declencher la regle de longueur minimale du score.",
            "expect_issue_any": ["trop court"]}
    res = eval_posts.run_case(case)
    assert res["fails"] and "issue attendue" in res["fails"][0]


def test_run_case_detecte_score_hors_borne():
    case = {"id": "x", "projet": "helium", "lang": "fr", "themes": [],
            "text": "Patch.", "expect_score_min": 90}
    res = eval_posts.run_case(case)
    assert res["fails"] and "score" in res["fails"][0]


def test_load_cases_ignore_comments_et_blanks(tmp_path):
    p = tmp_path / "cases.jsonl"
    p.write_text("# commentaire\n\n"
                 + json.dumps({"id": "a", "text": "t"}) + "\n",
                 encoding="utf-8")
    cases = eval_posts.load_cases(p)
    assert [c["id"] for c in cases] == ["a"]


def test_main_code_retour(tmp_path, capsys):
    data = tmp_path / "ok.jsonl"
    data.write_text(json.dumps({
        "id": "ok", "projet": "helium", "lang": "fr", "themes": ["tests"],
        "text": "Helium : le scan bloque les cles avant le push du soir, "
                "avec quatre tests d integration sur la file d attente.",
        "expect_lint_none": True}) + "\n", encoding="utf-8")
    report = tmp_path / "report.json"
    code = eval_posts.main(["--data", str(data), "--report", str(report)])
    assert code == 0
    assert json.loads(report.read_text(encoding="utf-8"))["failed"] == 0
    assert "1/1" in capsys.readouterr().out
