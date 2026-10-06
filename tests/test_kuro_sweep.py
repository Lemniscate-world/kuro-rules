"""Tests kuro_security_sweep — parsers et rendus purs, zero reseau."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_security_sweep as sw  # noqa: E402


def test_parse_github_url():
    assert sw.parse_github_url("https://github.com/Org/Repo.git") == ("Org", "Repo")
    assert sw.parse_github_url("git@github.com:Org/Repo.git") == ("Org", "Repo")
    assert sw.parse_github_url("https://github.com/Org/Repo") == ("Org", "Repo")
    assert sw.parse_github_url("nimporte-quoi") == ("", "")
    assert sw.parse_github_url("") == ("", "")
    assert sw.parse_github_url(None) == ("", "")


def test_sonar_key_properties_dabord(tmp_path):
    (tmp_path / "sonar-project.properties").write_text(
        "sonar.projectKey=Ma_Cle\n", encoding="utf-8")
    assert sw.sonar_key_for(tmp_path, "Org", "Repo") == "Ma_Cle"


def test_sonar_key_devine(tmp_path):
    assert sw.sonar_key_for(tmp_path, "Org", "Repo") == "Org_Repo"
    assert sw.sonar_key_candidates(tmp_path, "Org", "Repo") == [
        "Org_Repo", "Lemniscate-world_Repo"]
    assert sw.sonar_key_candidates(tmp_path, "Lemniscate-world", "Repo") == [
        "Lemniscate-world_Repo"]


def test_sweep_repo_saute_fork():
    out = sw.sweep_repo({"name": "pytorch-fork", "org": "O", "repo": "R",
                         "branch": "main"}, Path("."))
    assert "fork" in out["skipped"]


def test_render_human_cas():
    payload = {"generated_at": "t", "repo_count": 3, "with_alerts": 1, "repos": [
        {"name": "F", "skipped": "fork/miroir : x"},
        {"name": "A", "github": {"archived": True}},
        {"name": "B", "github": {"available": True, "archived": False,
                                 "alerts": [{"severity": "high"}]},
         "sonar": {"available": True, "quality_gate": "ERROR",
                   "security_open": 2, "stale": True}},
    ]}
    text = sw.render_human(payload)
    assert "SKIP" in text and "ARCHIVE" in text
    assert "CodeQL 1 (high:1)" in text
    assert "STALE" in text and "perimees" in text


def test_get_json_jamais_d_exception(monkeypatch):
    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("mort")))
    assert sw._get_json("https://x", {}) == (None, 0)
    assert sw.parse_github_url(None) == ("", "")
