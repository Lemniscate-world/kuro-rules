"""Tests fraicheur TUI Xenon : CPU amorce, repos reels, humeur nommee, ages visibles.

Cible les "infos pas a jour" constatees sur machine reelle :
- TOP a 0.0 partout sur la 1re frame (psutil non amorce)
- "[reel: 0 repos]" alors que ~/Documents contient 50+ depots (~/repos absent)
- "disque plein a 100%" sans dire lequel
- cerveau/jambes/marketing sans age (chiffres vieux de 2 semaines = live)
- "agents : aucun" sur timeout gateway OpenClaw (flaky une frame sur deux)
"""

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import agents as wag  # noqa: E402
from kuro_dashboard import face as wface  # noqa: E402
from kuro_dashboard import kuro_state as wks  # noqa: E402
from kuro_dashboard import system as wsys  # noqa: E402
from kuro_dashboard import tui as wtui  # noqa: E402


@pytest.fixture(autouse=True)
def _fast_caches(monkeypatch):
    monkeypatch.setattr(wtui, "agents_lines", lambda: [])
    import urllib.request as _url
    monkeypatch.setattr(_url, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(
                            OSError("pas de reseau en test")))
    monkeypatch.setattr(wtui, "_OLLAMA_CACHE", {"ts": 0.0, "ok": False,
                                                "names": []})
    monkeypatch.setattr(wks, "_FS_CACHE", {"ts": 0.0, "signals": {}})
    import kuro_dashboard.projects as _pr
    monkeypatch.setattr(_pr, "_CACHE", {"ts": 0.0, "roots": None, "repos": []})
    monkeypatch.setattr(wag, "_AGENTS_CACHE", {"ts": 0.0, "lines": []})


# -- CPU amorce ---------------------------------------------------------------

class _PrimedProc:
    """Fake psutil.Process : cpu 0.0 avant amorce, reel apres."""

    def __init__(self, pid, name, real_cpu, mem):
        self._calls = 0
        self.info = {"pid": pid, "name": name, "cpu_percent": 0.0,
                     "memory_percent": mem, "status": "running"}
        self._real = real_cpu

    def cpu_percent(self):
        self._calls += 1
        self.info["cpu_percent"] = self._real
        return self._real


class _PrimePsutil:
    def __init__(self):
        self.procs = [_PrimedProc(1, "a", 42.0, 1.0),
                      _PrimedProc(2, "b", 7.0, 2.0)]

    def process_iter(self, _attrs):
        return list(self.procs)

    def cpu_percent(self, interval=None, percpu=False):
        return 10.0

    def cpu_count(self, logical=True):
        return 2

    def virtual_memory(self):
        return SimpleNamespace(_asdict=lambda: {"total": 8, "available": 4,
                                                "used": 4, "percent": 50.0})

    def swap_memory(self):
        return SimpleNamespace(_asdict=lambda: {"total": 2, "used": 1,
                                                "percent": 50.0})

    def disk_partitions(self, all=False):
        return []

    def disk_io_counters(self):
        raise RuntimeError("no io")

    def net_io_counters(self):
        return SimpleNamespace(_asdict=lambda: {"bytes_sent": 5, "bytes_recv": 9})

    def net_if_addrs(self):
        return {}

    def sensors_temperatures(self):
        return {}

    def sensors_fans(self):
        return {}


def test_top_processes_amorces_premiere_frame(monkeypatch):
    fake = _PrimePsutil()
    monkeypatch.setattr(wsys, "_psutil", lambda: fake)
    monkeypatch.setattr(wsys, "_gpu", lambda: [])
    monkeypatch.setattr(wsys, "_docker",
                        lambda: {"available": False, "count": 0, "containers": []})
    monkeypatch.setattr("time.sleep", lambda s: None)
    payload = wsys.collect_system_snapshot(top_n=5)
    assert all(p._calls >= 1 for p in fake.procs), "amorce psutil attendue"
    by_pid = {p["pid"]: p for p in payload["processes"]}
    assert by_pid[1]["cpu"] == 42.0, "TOP fige a 0.0 sans amorce"
    assert [p["pid"] for p in payload["processes"]] == [1, 2]


def test_prime_ne_bloque_jamais(monkeypatch):
    class _Boom:
        def process_iter(self, _attrs):
            raise RuntimeError("psutil casse")

    wsys._prime_process_cpu(_Boom())  # ne leve pas
    wsys._prime_process_cpu(None)  # ne leve pas non plus


# -- repos reels ----------------------------------------------------------------

def test_fs_signals_compte_depots_git_reels(tmp_path, monkeypatch):
    docs = tmp_path / "Documents"
    (docs / "ProjA" / ".git").mkdir(parents=True)
    (docs / "ProjB" / ".git").mkdir(parents=True)
    (docs / "PasUnRepo").mkdir(parents=True)
    (docs / "Worktree" / ".git").mkdir(parents=True)
    (docs / "Worktree" / ".git").rmdir()
    (docs / "Worktree" / ".git").write_text("gitdir: ailleurs", encoding="utf-8")
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(docs))
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert wks._project_roots() == [docs]
    assert wks._count_git_dirs([docs]) == 2, "worktree (.git fichier) exclu"
    sig = wks._fs_signals()
    assert sig["repos_fs"] == 2, "etait 0 quand ~/repos absent"


def test_fs_signals_cache_ttl(tmp_path, monkeypatch):
    monkeypatch.setattr(wks, "_count_git_dirs", lambda roots: 99)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    (tmp_path / "Documents").mkdir(exist_ok=True)
    first = wks._fs_signals()
    assert first["repos_fs"] == 99
    monkeypatch.setattr(wks, "_count_git_dirs",
                        lambda roots: (_ for _ in ()).throw(AssertionError("cache")))
    assert wks._fs_signals()["repos_fs"] == 99, "2e appel servi par le cache 120 s"


# -- humeur nommee ---------------------------------------------------------------

def test_humeur_disque_nomme_son_mount():
    system = {"cpu": {"percent": 5.0}, "memory": {"percent": 10.0},
              "disk": {"partitions": [
                  {"mount": "C:\\", "percent": 40.0},
                  {"mount": "G:\\", "percent": 100.0}]},
              "sensors": {}}
    mood, reason = wface.mood_for(system, {"db_present": False})
    assert mood == "critical"
    assert "G:\\" in reason, f"quel disque ? {reason!r}"


def test_humeur_ignore_partitions_illisibles():
    system = {"cpu": {"percent": 5.0}, "memory": {"percent": 10.0},
              "disk": {"partitions": [{"mount": "X", "percent": None}]},
              "sensors": {}}
    # cpu 5% < 8 -> idle ("calme plat"), surtout pas d'alerte disque
    assert wface.mood_for(system, {"db_present": False})[0] == "idle"


# -- cerveau / jambes dates -------------------------------------------------------

def test_rel_age_unites():
    assert wtui._rel_age(None) == ""
    assert wtui._rel_age("nimporte-quoi") == ""
    assert wtui._rel_age("") == ""
    now = __import__("datetime").datetime.now().astimezone()
    assert wtui._rel_age(now.isoformat()) == "a l'instant"
    old = (now - timedelta(days=3, hours=2)).replace(microsecond=0)
    assert wtui._rel_age(old.isoformat(timespec="seconds")) == "il y a 3j"
    hours = (now - timedelta(hours=10)).replace(microsecond=0)
    assert wtui._rel_age(hours.isoformat(timespec="seconds")) == "il y a 10h"


def test_sec_brain_affiche_age(tmp_path, monkeypatch):
    from datetime import datetime
    now = datetime.now().astimezone().replace(microsecond=0)
    brain = tmp_path / "llm.json"
    brain.write_text(json.dumps({"engine": "openrouter", "latency_s": 2.0,
                                 "at": now.isoformat(timespec="seconds")}),
                     encoding="utf-8")
    monkeypatch.setattr(wtui, "LLM_LAST_FILE", brain)
    monkeypatch.setattr(wtui, "LLM_USAGE_FILE", tmp_path / "nope.jsonl")
    line = wtui.sec_brain()[0]
    assert "openrouter" in line and "l'instant" in line


def test_recent_legs_ignore_statuts_anciens(tmp_path, monkeypatch):
    usage = tmp_path / "u.jsonl"
    ancient = (date.today() - timedelta(days=30)).isoformat()
    usage.write_text(
        json.dumps({"day": ancient, "legs": [["openrouter", "error-boom"]]}) + "\n"
        + json.dumps({"day": date.today().isoformat(),
                      "legs": [["deepseek", "ok"]]}) + "\n"
        + json.dumps({"legs": [["local", "weird-sans-date"]]}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(wtui, "LLM_USAGE_FILE", usage)
    legs = wtui._recent_legs()
    assert legs.get("deepseek") == "ok"
    assert legs.get("local") == "weird-sans-date", "sans date -> conserve"
    assert "openrouter" not in legs, "DOWN vieux de 30 j filtre"


# -- marketing date -----------------------------------------------------------------

def test_sec_marketing_affiche_age_sources(tmp_path, monkeypatch):
    root = tmp_path / "rules"
    root.mkdir()
    (root / "pipeline.local.json").write_text(
        json.dumps({"entries": [{"type": "interview", "date": "2026-10-05",
                                 "insight": "x", "next_step": "y"}]}),
        encoding="utf-8")
    old_ts = __import__("time").time() - 17 * 86400
    os.utime(root / "pipeline.local.json", (old_ts, old_ts))
    (root / "LAUNCH_POSTS.md").write_text("## Post 1\n- [ ] publier\n",
                                          encoding="utf-8")
    (root / "acquisition_tracker.md").write_text("| **Reddit** | x |\n",
                                                 encoding="utf-8")
    monkeypatch.setenv("KURO_RULES_DIR", str(root))
    lines = wtui.sec_marketing()
    assert any("maj il y a 17j" in line for line in lines), lines


def test_file_age_txt_unites(tmp_path):
    assert wtui._file_age_txt(tmp_path / "nope") == ""
    assert "min" in wtui._file_age_txt(tmp_path)


# -- agents gateway ------------------------------------------------------------------

def test_openclaw_json_rejette_stderr_gateway(monkeypatch):
    calls = []

    class _Done:
        returncode = 0
        stdout = "[]"
        stderr = "gateway connect failed: unauthorized (token mismatch)"

    def _run(*a, **k):
        calls.append(a)
        return _Done()

    monkeypatch.setattr(wag.shutil, "which", lambda name: "openclaw")
    monkeypatch.setattr(wag.subprocess, "run", _run)
    assert wag._openclaw_json("agents", "list") is None


def test_openclaw_json_ok_sans_stderr(monkeypatch):
    class _Done:
        returncode = 0
        stdout = '[{"id": "main"}]'
        stderr = ""

    monkeypatch.setattr(wag.shutil, "which", lambda name: "openclaw")
    monkeypatch.setattr(wag.subprocess, "run", lambda *a, **k: _Done())
    assert wag._openclaw_json("agents", "list") == [{"id": "main"}]


def test_agents_lines_distinguent_panne_et_vide(monkeypatch):
    monkeypatch.setattr(wag.shutil, "which", lambda name: "openclaw")

    def _fake(*args):
        if args[0] == "agents":
            return [{"id": "main", "identityName": "K",
                      "model": "deepseek/deepseek-chat"}]
        return None  # cron KO (gateway)

    monkeypatch.setattr(wag, "_openclaw_json", _fake)
    data = wag.collect_agents()
    assert data["agents_ok"] is True and data["crons_ok"] is False
    lines = wag.agents_lines()
    assert any("indisponible" in line for line in lines)
    assert not any("aucune tache" in line for line in lines)

    monkeypatch.setattr(wag, "_openclaw_json", lambda *a: None)
    wag._AGENTS_CACHE.update({"ts": 0.0, "lines": []})
    lines2 = wag.agents_lines()
    assert any("liste indisponible" in line for line in lines2)
