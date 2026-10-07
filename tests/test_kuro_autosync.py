"""Tests kuro_autosync : périmètre, refus R76/R101, dry-run hermétique."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_autosync as autosync


def test_classify_garde_bot_et_autorise_code():
    ok, skipped = autosync.classify([
        "src/kuro_dashboard/tui.py", "tests/test_x.py", ".github/workflows/q.yml",
        "TRUTH_DAILY.md", "tasks_anydo.json", "outputs/x_post_1.md",
        "pyproject.toml", "random.bin",
    ])
    assert "src/kuro_dashboard/tui.py" in ok
    assert "tests/test_x.py" in ok
    assert ".github/workflows/q.yml" in ok
    assert "pyproject.toml" in ok
    assert "TRUTH_DAILY.md" in skipped
    assert "tasks_anydo.json" in skipped
    assert "outputs/x_post_1.md" in skipped
    assert "random.bin" in skipped


def test_refus_main_protege_secret(monkeypatch):
    monkeypatch.setattr(autosync, "_git", lambda *a, **k: subprocess.CompletedProcess(a, 0, "", ""))
    assert any("protégée" in r for r in autosync.refusal_reasons("main", ["src/a.py"], "", False))
    assert autosync.refusal_reasons("feat/x", ["src/a.py"], "", False) == []
    assert any("R76" in r for r in autosync.refusal_reasons("feat/x", [".env"], "", False))
    assert any("R76" in r for r in autosync.refusal_reasons("feat/x", ["sub/k.pem"], "", False))
    assert any("R101" in r for r in autosync.refusal_reasons(
        "feat/x", ["src/a.py"], 'api_key = "abcdefgh123"', False))
    assert autosync.refusal_reasons("feat/x", ["src/a.py"], "code propre", True) == []


def test_build_message():
    msg = autosync.build_message("feat/x", ["a.py", "b.py"])
    assert "feat/x" in msg
    assert "2 fichiers" in msg


def test_classify_inclut_dashboard():
    ok, _skipped = autosync.classify(["dashboard/app.js", "dashboard/styles.css"])
    assert ok == ["dashboard/app.js", "dashboard/styles.css"]


def test_dry_run_depot_temporaire(tmp_path, monkeypatch, capsys):
    repo = tmp_path / "r"
    repo.mkdir()
    for cmd in (["init"], ["config", "user.email", "t@t.t"], ["config", "user.name", "t"],
                ["checkout", "-b", "feat/tmp"]):
        subprocess.run(["git", *cmd], cwd=repo, capture_output=True)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    (repo / "TRUTH_DAILY.md").write_text("bot\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
    (repo / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    monkeypatch.setattr(autosync, "REPO", repo)
    assert autosync.main(["--dry-run", "--no-gate"]) == 0
    assert "DRY-RUN" in capsys.readouterr().out
