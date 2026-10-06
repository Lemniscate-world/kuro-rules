"""Tests kuro_coverage — mapping statique + parse coverage.json (sans pytest)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_coverage as kc  # noqa: E402


def _repo(tmp_path):
    repo = tmp_path / "Demo"
    (repo / "pkg").mkdir(parents=True)
    (repo / "pkg" / "a.py").write_text("x = 1\n" * 50, encoding="utf-8")
    (repo / "pkg" / "b.py").write_text("y = 2\n" * 10, encoding="utf-8")
    (repo / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (repo / "setup.py").write_text("", encoding="utf-8")
    tests = repo / "tests"
    tests.mkdir()
    (tests / "test_a.py").write_text("def test_x():\n    assert True\n", encoding="utf-8")
    return repo


def test_static_gaps_b_seul_non_teste_trie_taille(tmp_path):
    out = kc.static_gaps(_repo(tmp_path))
    assert out["modules"] == 2 and out["tested"] == 1
    assert [u["path"] for u in out["untested"]] == ["pkg/b.py"]
    assert out["untested"][0]["lines"] == 10


def test_test_stems_deux_conventions(tmp_path):
    repo = tmp_path / "R"
    (repo / "tests").mkdir(parents=True)
    (repo / "tests" / "test_foo.py").write_text("", encoding="utf-8")
    (repo / "tests" / "bar_test.py").write_text("", encoding="utf-8")
    assert kc.test_stems(repo) == {"foo", "bar"}


def test_parse_coverage_json_ordonne_moins_couverts():
    data = {"files": {
        "a.py": {"summary": {"percent_covered": 100}, "missing_lines": []},
        "b.py": {"summary": {"percent_covered": 20}, "missing_lines": [3, 4, 5]},
        "c.py": {"summary": {"percent_covered": 0}, "missing_lines": [1]},
    }}
    out = kc.parse_coverage_json(data)
    assert [f["path"] for f in out] == ["c.py", "b.py"]
    assert out[0]["missing"] == 1 and out[1]["lines"] == "3,4,5"


def test_save_entry_remplace_meme_repo(tmp_path, monkeypatch):
    f = tmp_path / "cov.json"
    monkeypatch.setattr(kc, "COVERAGE_FILE", f)
    kc.save_entry({"name": "X", "untested": [{"path": "a", "pct": 0}]})
    kc.save_entry({"name": "X", "untested": []})
    data = json.loads(f.read_text(encoding="utf-8"))
    assert len(data["repos"]) == 1 and data["repos"][0]["untested"] == []


def test_run_repo_introuvable():
    out = kc.run_repo("RepoQuiNexistePas123", timeout=5)
    assert "error" in out


def test_run_all_saute_sans_tests_et_limite(tmp_path, monkeypatch):
    import kuro_metrics
    vide = tmp_path / "Vide"
    (vide / ".git").mkdir(parents=True)
    (vide / "a.py").write_text("x = 1\n", encoding="utf-8")
    plein = tmp_path / "Plein"
    (plein / ".git").mkdir(parents=True)
    (plein / "t").mkdir()
    (plein / "t" / "test_q.py").write_text("def test_q():\n    assert True\n", encoding="utf-8")
    monkeypatch.setattr(kuro_metrics, "detect_git_repositories", lambda: [vide, plein])
    monkeypatch.setattr(kc, "run_repo", lambda name, timeout=240: {"name": name, "pct_total": 80.0,
                                                                   "untested": []})
    out = kc.run_all(timeout=5)
    by_name = {r["name"]: r for r in out}
    assert by_name["Vide"]["skipped"] == "aucun fichier de test"
    assert by_name["Plein"]["pct_total"] == 80.0
    out2 = kc.run_all(timeout=5, only={"vide"})
    assert [r["name"] for r in out2] == ["Vide"]
    out3 = kc.run_all(timeout=5, limit=1)
    measured = [r for r in out3 if "pct_total" in r]
    assert len(measured) == 1  # limite = 1 mesure pytest max, les sautes ne comptent pas


def test_render_run_all_classe_par_pct():
    text = kc.render_run_all([
        {"name": "B", "pct_total": 90.0, "gaps": 1},
        {"name": "A", "pct_total": 10.0, "gaps": 5},
        {"name": "C", "error": "boom"},
    ])
    assert text.index("A") < text.index("B")
    assert "NON MESURE : boom" in text
