"""Tests kuro_autotest — generation bornee et reversible (LLM moque)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_autotest as at  # noqa: E402


def test_top_functions_pur():
    src = "import os\n\ndef f():\n    pass\nclass C:\n    pass\ndef _h():\n    pass\n"
    assert at.top_functions(src) == ["f", "C"]
    assert at.top_functions("def broken(:") == []


def test_smoke_source_compile_et_symboles():
    code = at.smoke_source("m.py", ["f", "C"])
    compile(code, "<t>", "exec")
    assert "test_smoke_imports" in code and '"f"' in code


def test_valid_test_code_filtre():
    assert at.valid_test_code("def test_a():\n    assert True\n") is True
    assert at.valid_test_code("x = 1\n") is False
    assert at.valid_test_code("def test_a():\n    import os; os.remove('x')\n") is False
    assert at.valid_test_code("def test_a(:\n") is False
    assert at.valid_test_code("def test_a():\n    p = 'C:/Users/x'\n") is False
    assert at.valid_test_code("def test_a(tmp_path):\n    f = tmp_path / 'a'\n") is True


def test_extract_python_bloc():
    assert at.extract_python("bla\n```python\ndef test_a():\n    pass\n```\nfin") == \
        "def test_a():\n    pass\n"
    assert "def test_a" in at.extract_python("def test_a():\n    pass\n")


def test_failure_excerpt_garde_failed_et_fin():
    filler = [f"warn{i}" for i in range(100)]
    out = "\n".join(filler[:50] + ["FAILED t.py::test_x", "E   assert 1 == 2"] + filler[50:] + ["fin"])
    ex = at.failure_excerpt(out, limit=400)
    assert "FAILED" in ex and "fin" in ex and "warn0" not in ex and len(ex) <= 400


def _repo(tmp_path):
    repo = tmp_path / "R"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "mod.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    return repo


def test_repo_introuvable():
    res = at.autotest_repo(str("Nope"), max_n=1)
    assert res[0]["error"] == "repo introuvable"


def test_smoke_bout_en_bout_fichier_garde(tmp_path, monkeypatch):
    import kuro_coverage
    repo = _repo(tmp_path)
    monkeypatch.setattr(kuro_coverage, "test_stems", lambda r: set())
    monkeypatch.setattr(at, "run_pytest_file", lambda *a, **k: (True, "1 passed"))
    import kuro_autotest as atm
    monkeypatch.setattr(atm, "DOCS_DIR", tmp_path)
    res = at.autotest_repo("R", max_n=1)
    assert res[0]["kept"] is True and res[0]["file"] == "test_mod_smoke.py"
    assert (repo / "tests" / "test_mod_smoke.py").exists()


def test_rouge_supprime_apres_essais(tmp_path, monkeypatch):
    import kuro_coverage
    import kuro_llm
    repo = _repo(tmp_path)
    monkeypatch.setattr(kuro_coverage, "test_stems", lambda r: set())
    monkeypatch.setattr(kuro_llm, "ask", lambda *a, **k: "def test_a():\n    assert False\n")
    monkeypatch.setattr(at, "run_pytest_file", lambda *a, **k: (False, "FAILED"))
    import kuro_autotest as atm
    monkeypatch.setattr(atm, "DOCS_DIR", tmp_path)
    res = at.autotest_repo("R", llm=True, max_n=1)
    assert res[0]["kept"] is False and "supprime" in res[0]["reason"]
    assert not (repo / "tests" / "test_mod_auto.py").exists()


def test_llm_vert_au_2e_essai(tmp_path, monkeypatch):
    import kuro_coverage
    import kuro_llm
    repo = _repo(tmp_path)
    monkeypatch.setattr(kuro_coverage, "test_stems", lambda r: set())
    monkeypatch.setattr(kuro_llm, "ask", lambda *a, **k: "def test_a():\n    assert True\n")
    calls = {"n": 0}

    def fake_run(*a, **k):
        calls["n"] += 1
        return (calls["n"] >= 2, "ok" if calls["n"] >= 2 else "FAILED")

    monkeypatch.setattr(at, "run_pytest_file", fake_run)
    import kuro_autotest as atm
    monkeypatch.setattr(atm, "DOCS_DIR", tmp_path)
    res = at.autotest_repo("R", llm=True, max_n=1)
    assert res[0]["kept"] is True and res[0]["tries"] == 2
