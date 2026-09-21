"""Tests kuro_testhealth — verdicts deterministes sur repos factices."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_testhealth as th  # noqa: E402


def _repo(tmp_path, name, with_tests=True, hermetic=True, old=False):
    repo = tmp_path / name
    (repo / ".git").mkdir(parents=True)
    if with_tests:
        tdir = repo / "tests"
        tdir.mkdir(parents=True)
        (tdir / "test_x.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        if hermetic:
            (tdir / "conftest.py").write_text(
                'import os\nos.environ["KEY"] = ""\n'
                'import pytest\n@pytest.fixture(autouse=True)\ndef _h(tmp_path, monkeypatch):\n'
                '    monkeypatch.setenv("MODE", "0")\n    yield\n',
                encoding="utf-8")
    return repo


def test_rouge_sans_tests(tmp_path):
    r = _repo(tmp_path, "Vide", with_tests=False)
    out = th.assess(r)
    assert out["verdict"] == "ROUGE" and out["tests"] == 0


def test_orange_tests_non_hermetiques(tmp_path):
    r = _repo(tmp_path, "Brut", hermetic=False)
    out = th.assess(r)
    assert out["verdict"] == "ORANGE" and out["hermetic"] is False


def test_is_hermetic_seuil_deux_marques(tmp_path):
    r = _repo(tmp_path, "H", hermetic=False)
    (r / "tests" / "conftest.py").write_text('x = "tmp_path"\n', encoding="utf-8")
    assert th.is_hermetic(r) is False  # 1 seule marque : insuffisant


def test_vert_si_recent_et_hermetique(tmp_path):
    import subprocess
    r = _repo(tmp_path, "Bon")
    for args in (["init", "-q"], ["add", "-A"],
                 ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "t"]):
        subprocess.run(["git", "-C", str(r)] + args, capture_output=True)
    out = th.assess(r)
    assert out["verdict"] == "VERT" and out["days_since_touch"] == 0


def test_render_cache_les_verts_et_cite_r102(tmp_path):
    payload = {"generated_at": "x", "project_count": 2,
               "counts": {"VERT": 1, "ORANGE": 0, "ROUGE": 1},
               "projects": [
                   {"name": "Bon", "verdict": "VERT", "tests": 5,
                    "hermetic": True, "days_since_touch": 1},
                   {"name": "Nul", "verdict": "ROUGE", "tests": 0,
                    "hermetic": False, "days_since_touch": None}]}
    text = th.render(payload)
    assert "1 verts" in text and "Nul" in text and "Bon" not in text.split("verts", 1)[1]
    assert "R102" in text
