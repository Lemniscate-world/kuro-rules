"""Tests unites Xenon v2 : system / kuro_state / projects / agents, hermetique."""

import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import agents as ag  # noqa: E402
from kuro_dashboard import kuro_state as ks  # noqa: E402
from kuro_dashboard import projects as pr  # noqa: E402
from kuro_dashboard import system as sy  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh():
    pr._CACHE.update({"ts": 0.0, "roots": None, "repos": []})
    ks._FS_CACHE.update({"ts": 0.0, "signals": {}})
    ag._AGENTS_CACHE.update({"ts": 0.0, "lines": []})
    sy._SNAP_CACHE.update({"ts": 0.0, "payload": None})
    yield
    pr._CACHE.update({"ts": 0.0, "roots": None, "repos": []})
    ks._FS_CACHE.update({"ts": 0.0, "signals": {}})
    ag._AGENTS_CACHE.update({"ts": 0.0, "lines": []})
    sy._SNAP_CACHE.update({"ts": 0.0, "payload": None})


# -- system ---------------------------------------------------------------------

def test_psutil_absent_si_import_casse(monkeypatch):
    monkeypatch.setitem(sys.modules, "psutil", None)
    assert sy._psutil() is None


def test_disk_fallback_et_robuste(monkeypatch):
    monkeypatch.setattr(sy, "_psutil", lambda: None)
    monkeypatch.setattr(sy.shutil, "disk_usage",
                        lambda anchor: (_ for _ in ()).throw(OSError("verrouille")))
    assert sy._disk(None) == {"partitions": [], "io": {}}
    monkeypatch.setattr(sy.shutil, "disk_usage", lambda anchor: (100, 40, 60))
    parts = sy._disk(None)["partitions"]
    assert parts[0]["mount"] == "fallback" and parts[0]["percent"] == 40.0


def test_gpu_retours_non_zero_et_timeout(monkeypatch):
    class _Done:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(sy.subprocess, "run", lambda *a, **k: _Done())
    assert sy._gpu() == []
    monkeypatch.setattr(sy.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(
                            subprocess.TimeoutExpired(cmd="n", timeout=1)))
    assert sy._gpu() == []
    assert sy._docker() == {"available": False, "count": 0, "containers": []}


def test_docker_timeout_compte(monkeypatch):
    class _Done:
        returncode = 0
        stdout = "abc123 mon-nom Up 2 hours\n"

    monkeypatch.setattr(sy.subprocess, "run", lambda *a, **k: _Done())
    got = sy._docker()
    assert got == {"available": True, "count": 1,
                   "containers": [{"line": "abc123 mon-nom Up 2 hours"}]}


def test_proc_detail_branches(monkeypatch):
    class _P:
        def oneshot(self):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def name(self):
            return "x"

        def cmdline(self):
            raise RuntimeError("x")

        def username(self):
            raise RuntimeError("x")

        def num_threads(self):
            raise RuntimeError("x")

        def memory_info(self):
            raise RuntimeError("x")

        def status(self):
            raise RuntimeError("x")

        def create_time(self):
            raise RuntimeError("x")

        def cpu_times(self):
            raise RuntimeError("x")

    class _Ps:
        def Process(self, pid):
            return _P()

    monkeypatch.setattr(sy, "_psutil", lambda: _Ps())
    info = sy.proc_detail(999)
    assert info["name"] == "x" and info["user"] == "?" and info["rss"] is None
    assert info["threads"] is None and info["cpu_user"] is None

    class _PsBoom:
        def Process(self, pid):
            raise RuntimeError("parti")

    monkeypatch.setattr(sy, "_psutil", lambda: _PsBoom())
    assert sy.proc_detail(999) is None


def test_top_processes_ignore_lignes_cassees(monkeypatch):
    bad = SimpleNamespace(info="pas-un-dict")

    class _Ps:
        def cpu_percent(self, interval=None, percpu=False):
            return 0.0

        def process_iter(self, _attrs):
            yield bad

    monkeypatch.setattr(sy, "_psutil", lambda: _Ps())
    monkeypatch.setattr("time.sleep", lambda s: None)
    assert sy._top_processes(_Ps(), 5) == []


def test_snapshot_cache_ttl(monkeypatch):
    monkeypatch.setattr(sy, "_psutil", lambda: None)
    monkeypatch.setattr(sy, "_gpu", lambda: [])
    monkeypatch.setattr(sy, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    first = sy.get_cached_snapshot()
    second = sy.get_cached_snapshot()
    assert first is second, "cache 2.5 s attendu"
    sy._SNAP_CACHE["ts"] = 0.0
    assert sy.get_cached_snapshot() is not first


def test_system_main_variants(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sy, "_psutil", lambda: None)
    monkeypatch.setattr(sy, "_gpu", lambda: [])
    monkeypatch.setattr(sy, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    monkeypatch.setattr(sys, "argv", ["kuro-system", "--json", "--top", "2"])
    assert sy.main() == 0
    assert '"psutil_available": false' in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["kuro-system"])
    assert sy.main() == 0
    assert "Glances Kuro" in capsys.readouterr().out
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["kuro-system", "--projects"])
    assert sy.main() == 0
    assert "Git projects: 0" in capsys.readouterr().out


def test_render_sans_processus(monkeypatch):
    monkeypatch.setattr(sy, "_psutil", lambda: None)
    monkeypatch.setattr(sy, "_gpu", lambda: [])
    monkeypatch.setattr(sy, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    text = sy.render(sy.collect_system_snapshot())
    assert "Top process:" in text


def test_host_et_cpu_sans_psutil():
    assert sy._host()["cpu_count"] >= 0
    assert sy._cpu(None)["per_cpu"] == []
    assert sy._memory(None) == {"total": None, "percent": None,
                                "swap_percent": None}
    assert sy._network(None) == {"io": {}, "interfaces": {}}
    assert sy._sensors(None) == {"temperatures": [], "fans": {}}


# -- kuro_state -------------------------------------------------------------------

def test_connect_absent_et_rows_tolerants(tmp_path, monkeypatch):
    monkeypatch.setattr(ks, "DB_PATH", tmp_path / "dossier")
    (tmp_path / "dossier").mkdir()
    assert ks._connect() is None  # sqlite sur un dossier -> None, pas d'exception
    db = tmp_path / "k.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE t (a INTEGER)")
    assert ks._rows(conn, "SELECT * FROM nope") == []
    assert ks._count(conn, "SELECT * FROM t") == 0
    conn.close()


def test_heartbeat_illisible(tmp_path, monkeypatch):
    db = tmp_path / "k.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE heartbeat (timestamp TEXT)")
    conn.execute("INSERT INTO heartbeat VALUES ('pas-une-date')")
    conn.execute("CREATE TABLE projects (id INTEGER)")
    conn.execute("CREATE TABLE sessions (id INTEGER)")
    conn.execute("CREATE TABLE alerts (id INTEGER, alert_type TEXT, message TEXT,"
                 " severity TEXT, acknowledged INTEGER, created_at TEXT,"
                 " project_id INTEGER)")
    conn.execute("CREATE TABLE memory_nodes (id INTEGER)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(ks, "DB_PATH", db)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    snap = ks.collect_kuro_snapshot()
    assert snap["db_present"] is True
    assert snap["heartbeat_age_min"] is None


def test_hb_detail_types_bizarres():
    assert ks._hb_detail(None)["hb_projects_scanned"] is None
    assert ks._hb_detail({"projects_scanned": "bad",
                          "alerts_active": "bad"})["hb_projects_scanned"] is None


def test_count_summaries_jamais_d_exception(tmp_path):
    assert ks._count_summaries(tmp_path / "nope") == 0
    (tmp_path / "SESSION_SUMMARY.md").write_text("x", encoding="utf-8")
    assert ks._count_summaries(tmp_path) == 1


def test_replica_erreur_lecture(tmp_path, monkeypatch):
    live = tmp_path / "live.db"
    live.write_text("pas-une-db", encoding="utf-8")
    rep = tmp_path / "rep.db"
    rep.write_text("pas-une-db-non-plus", encoding="utf-8")
    monkeypatch.setattr(ks, "DB_PATH", live)
    monkeypatch.setenv("KURO_REPLICA_PATH", str(rep))
    assert ks._replica_snapshot(live) is None


def test_snapshot_ferme_connexion_en_erreur(tmp_path, monkeypatch):
    db = tmp_path / "k.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE heartbeat (timestamp TEXT)")
    conn.commit()

    class _Conn:
        def execute(self, *a, **k):
            raise sqlite3.OperationalError("table manquante")

        def close(self):
            raise RuntimeError("close casse")

    monkeypatch.setattr(ks, "_connect", lambda: _Conn())
    conn.close()
    snap = ks.collect_kuro_snapshot()
    assert snap["db_present"] is True and snap["recent_alerts"] == []


# -- projects -----------------------------------------------------------------------

def test_roots_env_avec_vides(tmp_path, monkeypatch):
    monkeypatch.setenv("KURO_PROJECTS_ROOTS",
                       f" {tmp_path} {__import__('os').pathsep}  ")
    assert pr.roots() == [tmp_path]


def test_git_exception_ne_leve_jamais(tmp_path, monkeypatch):
    monkeypatch.setattr(pr.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("git mort")))
    assert pr._git(tmp_path, "status") is None


def test_scan_repo_sans_upstream(tmp_path, monkeypatch):
    import subprocess as _sp
    repo = tmp_path / "R"
    repo.mkdir()
    _sp.run(["git", "init", "-q"], cwd=repo, check=True)
    _sp.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
    _sp.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    _sp.run(["git", "add", "."], cwd=repo, check=True)
    _sp.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    got = pr.scan_repo(repo)
    assert got["ahead"] == 0 and got["behind"] == 0 and got["dirty"] == 0


def test_discover_replis(tmp_path, monkeypatch):
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path / "nope"))
    assert pr.discover(force=True) == []
    (tmp_path / "W" / ".git").mkdir(parents=True)
    (tmp_path / "W" / ".git").rmdir()
    (tmp_path / "W" / ".git").write_text("gitdir: x", encoding="utf-8")
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    assert pr.discover(force=True) == [], "worktree ignore"

    class _PoolBoom:
        def __init__(self, *a, **k):
            raise RuntimeError("pas de threads ici")

    monkeypatch.setattr("concurrent.futures.ThreadPoolExecutor", _PoolBoom)
    assert isinstance(pr.discover(force=True), list)


def test_quick_lines_exception():
    import kuro_dashboard.projects as _p
    _p._CACHE.update({"ts": 9999999999.0, "repos": [{"oups": 1}]})
    try:
        assert _p.quick_lines() == []
    finally:
        _p._CACHE.update({"ts": 0.0, "repos": []})


# -- agents --------------------------------------------------------------------------

def test_openclaw_variants(monkeypatch, tmp_path):
    monkeypatch.setattr(ag.shutil, "which", lambda name: "openclaw")
    monkeypatch.setattr(ag.subprocess, "run",
                        lambda *a, **k: (_ for _ in ()).throw(
                            subprocess.TimeoutExpired(cmd="o", timeout=1)))
    assert ag._openclaw_json("agents", "list") is None

    class _Bad:
        returncode = 0
        stdout = "pas-du-json{"
        stderr = ""

    monkeypatch.setattr(ag.subprocess, "run", lambda *a, **k: _Bad())
    assert ag._openclaw_json("agents", "list") is None

    class _Rc:
        returncode = 1
        stdout = ""
        stderr = ""

    monkeypatch.setattr(ag.subprocess, "run", lambda *a, **k: _Rc())
    assert ag._openclaw_json("agents", "list") is None
    assert ag._rel("bad", 1.0) == "jamais"


def test_is_problem_et_collect_robuste(monkeypatch):
    assert ag._is_problem({"enabled": False}) is True
    assert ag._is_problem({"state": {"lastRunStatus": "idle"}}) is False
    class _StrBoom:
        def __str__(self):
            raise RuntimeError("boom")

    assert ag._short_model(_StrBoom()) == "?"
    assert ag._short_model(123) == "123"
    monkeypatch.setattr(ag.shutil, "which", lambda name: "openclaw")
    monkeypatch.setattr(ag, "_openclaw_json",
                        lambda *a: "ni-liste-ni-dict")
    data = ag.collect_agents()
    assert data["agents"] == [] and data["crons"] == []
    assert data["crons_ok"] is False
    monkeypatch.setattr(ag, "_openclaw_json", lambda *a: ["pas-un-dict", 42])
    assert ag.collect_agents()["agents"] == []
    monkeypatch.setattr(ag, "_openclaw_json",
                        lambda *a: {"jobs": ["pas-un-dict"]})
    assert ag.collect_agents()["crons"] == []


def test_agents_lines_cache_et_present(monkeypatch):
    monkeypatch.setattr(ag.shutil, "which", lambda name: "openclaw")
    monkeypatch.setattr(ag, "_openclaw_json",
                        lambda *a: ([{"id": "m", "identityName": "K",
                                      "model": "m"}]
                                    if a[0] == "agents" else {"jobs": []}))
    first = ag.agents_lines()
    assert any("aucune tache" in line for line in first)
    second = ag.agents_lines()
    assert first == second, "2e appel servi par le cache"


def test_openclaw_sans_binaire_appel_direct(monkeypatch):
    monkeypatch.setattr(ag.shutil, "which", lambda name: None)
    assert ag._openclaw_json("agents", "list") is None


def test_rel_maintenant():
    import time as _t
    now_ms = _t.time() * 1000
    assert ag._rel(now_ms, now_ms) == "maintenant"


def test_collect_jobs_non_liste_et_boom(monkeypatch):
    monkeypatch.setattr(ag.shutil, "which", lambda name: "openclaw")
    monkeypatch.setattr(ag, "_openclaw_json",
                        lambda *a: ([{"id": "m"}] if a[0] == "agents"
                                     else {"jobs": "nope"}))
    data = ag.collect_agents()
    assert data["crons"] == [] and data["crons_ok"] is False
    assert data["agents_ok"] is True
    monkeypatch.setattr(ag, "_openclaw_json",
                        lambda *a: (_ for _ in ()).throw(RuntimeError("cli mort")))
    data2 = ag.collect_agents()
    assert data2["present"] is False


def test_agents_lines_avec_taches(monkeypatch):
    monkeypatch.setattr(ag.shutil, "which", lambda name: "openclaw")
    monkeypatch.setattr(ag, "_openclaw_json",
                        lambda *a: ([{"id": "m", "identityName": "K",
                                      "model": "m"}] if a[0] == "agents" else
                                    {"jobs": [
                                        {"name": "bad", "agentId": "m",
                                         "enabled": True,
                                         "state": {"lastRunStatus": "error",
                                                   "nextRunAtMs": 1,
                                                   "lastRunAtMs": 1}},
                                        {"name": "ok", "agentId": "m",
                                         "enabled": True,
                                         "state": {"lastRunStatus": "ok",
                                                   "nextRunAtMs": 1,
                                                   "lastRunAtMs": 1}}]}))
    lines = ag.agents_lines()
    assert lines[0].startswith("agents : m")
    assert any(line.startswith(" ! bad") for line in lines)
    assert any(re.match(r"^\s+ok\s", line) for line in lines)


def test_disk_partition_illisible_sautee(monkeypatch):
    from types import SimpleNamespace as _NS

    class _Ps:
        def disk_partitions(self, all=False):
            return [_NS(mountpoint="/ok", fstype="ext4"),
                    _NS(mountpoint="/ko", fstype="ext4"),
                    _NS(mountpoint="/snap/core22", fstype="squashfs"),
                    _NS(mountpoint="/snap/data", fstype="ext4")]

        def disk_usage(self, mount):
            if mount == "/ko":
                raise PermissionError("verrouille")
            return _NS(_asdict=lambda: {"total": 100, "used": 10,
                                        "percent": 10.0})

        def disk_io_counters(self):
            raise RuntimeError("no io")

    monkeypatch.setattr(sy, "_psutil", lambda: _Ps())
    mounts = [p["mount"] for p in sy._disk(_Ps())["partitions"]]
    assert mounts == ["/ok"]


def test_git_dirs_racine_fichier(tmp_path):
    f = tmp_path / "pas-un-dossier.txt"
    f.write_text("x", encoding="utf-8")
    assert ks._count_git_dirs([f]) == 0


def test_sensors_avec_donnees(monkeypatch):
    from types import SimpleNamespace as _NS

    class _Ps:
        def sensors_temperatures(self):
            return {"cpu": [_NS(label="t", current=55.0, high=90.0)]}

        def sensors_fans(self):
            return {"f": [_NS(label="v", current=1200)]}

    got = sy._sensors(_Ps())
    assert got["temperatures"][0]["current"] == 55.0
    assert got["fans"] == {"f": [{"label": "v", "current": 1200}]}


def test_gpu_ligne_malformee_sautee(monkeypatch):
    class _Done:
        returncode = 0
        stdout = "ligne-poubelle\n0, RTX, 10, 100, 200, 50\n"

    monkeypatch.setattr(sy.subprocess, "run", lambda *a, **k: _Done())
    cards = sy._gpu()
    assert len(cards) == 1 and cards[0]["name"] == "RTX"

    class _Rc1:
        returncode = 1
        stdout = ""

    monkeypatch.setattr(sy.subprocess, "run", lambda *a, **k: _Rc1())
    assert sy._docker() == {"available": False, "count": 0, "containers": []}


def test_render_avec_processus(monkeypatch):
    monkeypatch.setattr(sy, "_psutil", lambda: None)
    monkeypatch.setattr(sy, "_gpu", lambda: [])
    monkeypatch.setattr(sy, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    payload = sy.collect_system_snapshot()
    payload["processes"] = [{"pid": 7, "name": "demo", "cpu": 1.0, "mem": 2.0}]
    assert "demo" in sy.render(payload)


def test_system_main_projects_formats(monkeypatch, tmp_path, capsys):
    (tmp_path / "R" / ".git").mkdir(parents=True)
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    monkeypatch.setattr(sys, "argv", ["kuro-system", "--projects", "--json"])
    assert sy.main() == 0
    assert '"projects"' in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["kuro-system", "--projects"])
    assert sy.main() == 0
    assert "Git projects: 1" in capsys.readouterr().out


def test_count_valeur_illisible(tmp_path):
    db = tmp_path / "k.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE t (n TEXT)")
    conn.execute("INSERT INTO t VALUES ('bad')")
    try:
        assert ks._count(conn, "SELECT n FROM t") == 0
    finally:
        conn.close()


def test_count_summaries_entree_cassee(tmp_path, monkeypatch):
    import os as _os

    class _Evil:
        name = "x"
        path = "x"

        def is_dir(self, follow_symlinks=False):
            raise RuntimeError("readdir mort")

        def is_file(self, follow_symlinks=False):
            raise RuntimeError("readdir mort")

    class _FakeIt:
        def __enter__(self):
            return [_Evil()]

        def __exit__(self, *a):
            return None

    monkeypatch.setattr(_os, "scandir", lambda cur: _FakeIt())
    assert ks._count_summaries(tmp_path) == 0


def test_count_summaries_saute_bruit(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "node_modules").mkdir()
    sub = tmp_path / "Projet"
    sub.mkdir()
    (sub / "SESSION_SUMMARY.md").write_text("x", encoding="utf-8")
    assert ks._count_summaries(tmp_path) == 1


def test_git_dirs_iterdir_mort(tmp_path, monkeypatch):
    (tmp_path / "R").mkdir()
    monkeypatch.setattr(Path, "iterdir",
                        lambda self: (_ for _ in ()).throw(OSError("mort")))
    try:
        assert ks._count_git_dirs([tmp_path]) == 0
    finally:
        pass
    assert ks._count_git_dirs(None) == 0


def test_git_dirs_resolve_mort(tmp_path, monkeypatch):
    (tmp_path / "R" / ".git").mkdir(parents=True)
    monkeypatch.setattr(Path, "resolve",
                        lambda self: (_ for _ in ()).throw(OSError("mort")))
    try:
        assert ks._count_git_dirs([tmp_path]) == 1
    finally:
        pass


def test_git_dirs_enfant_mort(tmp_path, monkeypatch):
    (tmp_path / "R" / ".git").mkdir(parents=True)
    real_is_dir = Path.is_dir
    monkeypatch.setattr(Path, "is_dir",
                        lambda self: (_ for _ in ()).throw(OSError("mort"))
                        if self.name == "R" else real_is_dir(self))
    assert ks._count_git_dirs([tmp_path]) == 0


def test_project_roots_replis(monkeypatch, tmp_path):
    import kuro_dashboard.projects as _pr
    monkeypatch.setattr(_pr, "roots",
                        lambda: (_ for _ in ()).throw(RuntimeError("mort")))
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    assert ks._project_roots() == [tmp_path]

    class _BoomGet(dict):
        def get(self, *a, **k):
            raise RuntimeError("env mort")

    monkeypatch.setattr(ks.os, "environ", _BoomGet())
    assert ks._project_roots() == []


def test_fs_signals_cache_vide_et_tout_mort(tmp_path, monkeypatch):
    import kuro_dashboard.projects as _pr
    monkeypatch.setattr(_pr, "roots",
                        lambda: (_ for _ in ()).throw(RuntimeError("mort")))
    monkeypatch.delenv("KURO_PROJECTS_ROOTS", raising=False)
    monkeypatch.setattr(Path, "home",
                        classmethod(lambda cls: (_ for _ in ()).throw(
                            OSError("home mort"))))
    monkeypatch.setattr(ks, "_FS_CACHE", {})
    sig = ks._fs_signals()
    assert sig["repos_fs"] == 0


def test_replica_close_mort(tmp_path, monkeypatch):
    import sqlite3 as _sq
    rep = tmp_path / "rep.db"
    c = _sq.connect(rep)
    c.execute("CREATE TABLE projects (id INTEGER)")
    c.execute("INSERT INTO projects VALUES (1)")
    c.commit()
    c.close()
    live = tmp_path / "live.db"
    live.write_text("x", encoding="utf-8")
    real_connect = _sq.connect
    opened = []

    class _C:
        def __init__(self, *a, **k):
            self._c = real_connect(*a, **k)
            opened.append(self._c)

        def execute(self, *a, **k):
            return self._c.execute(*a, **k)

        def close(self):
            raise RuntimeError("close mort")

    monkeypatch.setattr(_sq, "connect", _C)
    monkeypatch.setenv("KURO_REPLICA_PATH", str(rep))
    try:
        snap = ks._replica_snapshot(live)
        assert snap["projects"] == 1
        assert isinstance(snap["file_age_min"], float)
    finally:
        for c in opened:
            try:
                c.close()
            except Exception:
                pass


def test_roots_sans_env(monkeypatch):
    monkeypatch.delenv("KURO_PROJECTS_ROOTS", raising=False)
    assert pr.roots() == [Path.home() / "repos", Path.home() / "Documents"]


def test_scan_repo_upstream_mocks(monkeypatch, tmp_path):
    def _fake(path, *args):
        cmd = " ".join(args)
        return {"branch --show-current": "main",
                "status --porcelain": "",
                "log -1 --format=%h %cs %s": "abc 2026-01-01 msg",
                "rev-parse --abbrev-ref --symbolic-full-name @{upstream}":
                    "origin/main",
                "rev-list --left-right --count HEAD...origin/main":
                    "2 3"}.get(cmd)

    monkeypatch.setattr(pr, "_git", _fake)
    got = pr.scan_repo(tmp_path)
    assert (got["behind"], got["ahead"]) == (2, 3)

    def _bad(path, *args):
        if "rev-list" in " ".join(args):
            return "nimporte-quoi"
        return _fake(path, *args)

    monkeypatch.setattr(pr, "_git", _bad)
    got2 = pr.scan_repo(tmp_path)
    assert (got2["behind"], got2["ahead"]) == (0, 0)


def test_discover_iterdir_mort_et_fallback(tmp_path, monkeypatch):
    (tmp_path / "R" / ".git").mkdir(parents=True)
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    real_iterdir = Path.iterdir
    monkeypatch.setattr(Path, "iterdir",
                        lambda self: (_ for _ in ()).throw(OSError("mort")))
    assert pr.discover(force=True) == []
    monkeypatch.setattr(Path, "iterdir", real_iterdir)

    class _PoolBoom:
        def __init__(self, *a, **k):
            raise RuntimeError("pas de threads ici")

    monkeypatch.setattr("concurrent.futures.ThreadPoolExecutor", _PoolBoom)
    found = pr.discover(force=True)
    assert [r["name"] for r in found] == ["R"]


def test_discover_resolve_mort(tmp_path, monkeypatch):
    (tmp_path / "R" / ".git").mkdir(parents=True)
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
    real_resolve = Path.resolve
    monkeypatch.setattr(Path, "resolve",
                        lambda self: (_ for _ in ()).throw(OSError("mort"))
                        if self.name == "R" else real_resolve(self))
    found = pr.discover(force=True)
    assert [r["name"] for r in found] == ["R"]
