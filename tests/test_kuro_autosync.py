"""Tests kuro_autosync : périmètre, refus R76/R101, dry-run hermétique.

R116 (blackout git 16→19/10/2026) : index.lock orpheline retirée, échecs
git journalisés (jamais de sortie silencieuse), rotation du journal.
"""

import os
import subprocess
import sys
import time
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


def test_subprocess_sans_fenetre_console(monkeypatch):
    r"""R118 : sous pythonw, tout subprocess doit porter CREATE_NO_WINDOW
    (sinon fenêtre « C:\Windows\SYSTEM32\cmd.exe » visible à chaque cycle)."""
    captured: dict = {}

    def fake_run(args, **kwargs):
        captured.update(kwargs)
        return subprocess.CompletedProcess(args, 0, "", "")

    import types
    fake_mod = types.SimpleNamespace(run=fake_run, CREATE_NO_WINDOW=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    monkeypatch.setattr(autosync, "subprocess", fake_mod)
    autosync._git("status")
    if sys.platform == "win32":
        assert captured.get("creationflags") == subprocess.CREATE_NO_WINDOW
        assert autosync._NO_WINDOW == {"creationflags": subprocess.CREATE_NO_WINDOW}
    else:
        assert autosync._NO_WINDOW == {}


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


def _make_lock(repo: Path, age_min: float) -> Path:
    gitdir = repo / ".git"
    gitdir.mkdir(exist_ok=True)
    lock = gitdir / "index.lock"
    lock.write_text("", encoding="utf-8")
    old = time.time() - age_min * 60
    os.utime(lock, (old, old))
    return lock


def test_clear_stale_lock_retire_verrou_vieux(tmp_path, monkeypatch):
    """R116 : verrou >10 min = git mort → retirée + alerte journalisée."""
    lock = _make_lock(tmp_path, age_min=30)
    monkeypatch.setattr(autosync, "REPO", tmp_path)
    alert = autosync.clear_stale_lock()
    assert alert is not None and "orpheline" in alert
    assert not lock.exists()
    log = (tmp_path / "logs" / "autosync.log").read_text(encoding="utf-8")
    assert "ALERTE" in log and "index.lock" in log


def test_clear_stale_lock_garde_verrou_frais(tmp_path, monkeypatch):
    """Preuve négative : verrou récent = opération git vivante, intouchable."""
    lock = _make_lock(tmp_path, age_min=1)
    monkeypatch.setattr(autosync, "REPO", tmp_path)
    assert autosync.clear_stale_lock() is None
    assert lock.exists()


def test_clear_stale_lock_sans_verrou(tmp_path, monkeypatch):
    monkeypatch.setattr(autosync, "REPO", tmp_path)
    assert autosync.clear_stale_lock() is None


def test_changed_files_leve_si_git_status_casse(monkeypatch):
    """R116 : un git status en échec n'est plus masqué derrière une liste vide."""
    def broken(*args, **kwargs):
        return subprocess.CompletedProcess(args, 128, "", "fatal: index.lock exists")
    monkeypatch.setattr(autosync, "_git", broken)
    try:
        autosync.changed_files()
        raise AssertionError("AutosyncError attendu")
    except autosync.AutosyncError as exc:
        assert "git status KO" in str(exc)


def test_main_sortie_honnete_si_git_status_casse(tmp_path, monkeypatch, capsys):
    """Exit 8 + ligne de journal — l'incident : exit 0 silencieux 3 jours."""
    monkeypatch.setattr(autosync, "REPO", tmp_path)
    (tmp_path / ".git").mkdir()
    real_git = autosync._git

    def maybe_broken(*args, **kwargs):
        if args and args[0] == "status":
            return subprocess.CompletedProcess(args, 128, "", "fatal: git unusable")
        if args and args[0] == "rev-parse":
            return subprocess.CompletedProcess(args, 0, "feat/x\n", "")
        return real_git(*args, **kwargs)
    monkeypatch.setattr(autosync, "_git", maybe_broken)
    assert autosync.main([]) == 8
    out = capsys.readouterr().out
    assert "git status KO" in out
    log = (tmp_path / "logs" / "autosync.log").read_text(encoding="utf-8")
    assert "git status KO" in log


def test_main_rien_sync_est_journalise(tmp_path, monkeypatch):
    """R116 : la sortie neutre est tracée — un journal muet = tâche morte."""
    repo = tmp_path / "r"
    repo.mkdir()
    for cmd in (["init"], ["config", "user.email", "t@t.t"], ["config", "user.name", "t"]):
        subprocess.run(["git", *cmd], cwd=repo, capture_output=True)
    (repo / "seed.txt").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=repo, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "feat/clean"], cwd=repo, capture_output=True)
    monkeypatch.setattr(autosync, "REPO", repo)
    assert autosync.main([]) == 0
    log = (repo / "logs" / "autosync.log").read_text(encoding="utf-8")
    assert "rien à synchroniser" in log


def test_clear_stale_lock_en_tete_de_main(tmp_path, monkeypatch, capsys):
    """Le retrait du verrou précède tout git — un cycle répare et continue."""
    repo = tmp_path / "r"
    repo.mkdir()
    for cmd in (["init"], ["config", "user.email", "t@t.t"], ["config", "user.name", "t"],
                ["checkout", "-b", "feat/lock"]):
        subprocess.run(["git", *cmd], cwd=repo, capture_output=True)
    (repo / "src").mkdir()
    (repo / "src" / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, capture_output=True)
    (repo / "src" / "a.py").write_text("x = 2\n", encoding="utf-8")
    lock = _make_lock(repo, age_min=20)
    monkeypatch.setattr(autosync, "REPO", repo)
    assert autosync.main(["--dry-run", "--no-gate"]) == 0
    assert not lock.exists()
    assert "DRY-RUN" in capsys.readouterr().out


def test_log_line_rotation(tmp_path, monkeypatch):
    """R116 : le journal ne croît pas sans borne (rotation 512 Ko / 400 lignes)."""
    monkeypatch.setattr(autosync, "REPO", tmp_path)
    monkeypatch.setattr(autosync, "LOG_MAX_BYTES", 500)
    monkeypatch.setattr(autosync, "LOG_TAIL_LINES", 20)
    for i in range(100):
        autosync.log_line(f"ligne {i} " + "x" * 60)
    log = tmp_path / "logs" / "autosync.log"
    assert log.stat().st_size < 2500  # plafonné par la rotation
    content = log.read_text(encoding="utf-8")
    assert "ligne 99" in content  # la queue récente est conservée
    assert "ligne 0" not in content  # les plus vieilles lignes sont virées
