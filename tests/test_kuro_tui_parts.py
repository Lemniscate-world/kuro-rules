"""Tests tui.py vagues 2 : helpers purs, rendu large/compacte, clavier, watch, main.

Hermetique : integrations lentes coupees (agents, git, snapshots reels).
Portable CI : pas d hypothese Windows, pas d uptime, pas d env global.
"""

import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import projects as _git_projects  # noqa: E402
from kuro_dashboard import tui  # noqa: E402


def _stale(ttl):
    """Timestamp garanti perime, meme sur runner booté il y a 10 s.

    ts=0.0 semble FRAIS quand time.monotonic() < TTL (runner CI frais) :
    tous les tests d invalidation de cache doivent passer par ici.
    """
    return time.monotonic() - float(ttl) - 1.0


def _boom_environ(monkeypatch, key):
    """os.environ casse UNIQUEMENT pour *key* (snapshot du reste).

    Casser tout os.environ (dict vide qui leve) rend pytest fou
    (il lit $CI pendant le report) : ne jamais faire ca.
    """
    snap = dict(os.environ)

    class _SelectiveBoom(dict):
        def get(self, k, *a, **k2):
            if k == key:
                raise RuntimeError("env mort")
            return super().get(k, *a, **k2)

    monkeypatch.setattr(os, "environ", _SelectiveBoom(snap))


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(tui, "agents_lines", lambda: [])
    monkeypatch.setattr(_git_projects, "discover", lambda force=False: [])
    # Pas de reseau dans les tests TUI : la sonde Ollama voit un daemon mort.
    # Les tests de la sonde remplacent urlopen par des donnees factices.
    import urllib.request as _url

    monkeypatch.setattr(_url, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(
                            OSError("pas de reseau en test")))
    monkeypatch.setattr(tui, "_OLLAMA_CACHE", {"ts": _stale(120),
                                               "ok": False, "names": []})


def _payload(**kw):
    base = {"generated_at": "t",
            "psutil_available": True,
            "host": {"hostname": "srv", "system": "Linux", "cpu_count": 4},
            "cpu": {"percent": 42.0, "per_cpu": [10.0, 90.0],
                    "load_avg": [1.0, 0.5, 0.2]},
            "memory": {"percent": 60.0, "used": 6 * 1024 ** 3,
                       "total": 10 * 1024 ** 3, "swap_percent": 5.0},
            "disk": {"partitions": [{"mount": "/", "percent": 70.0,
                                     "used": 70, "total": 100}]},
            "network": {"io": {"bytes_sent": 1000, "bytes_recv": 2000}},
            "sensors": {"temperatures": [{"label": "cpu", "current": 55}]},
            "gpu": [{"index": "0", "name": "RTX", "util_percent": 80,
                     "temp_c": 65}],
            "docker": {"available": True, "count": 3},
            "processes": [{"pid": 1, "name": "init", "cpu": 99.0, "mem": 1.0}]}
    base.update(kw)
    return base


def _kuro(**kw):
    base = {"db_present": True, "projects": 3, "sessions": 9,
            "alerts_open": 2, "memory_nodes": 4, "heartbeat_age_min": 1.0,
            "repos_fs": 5, "summaries_fs": 6, "hb_projects_scanned": 3,
            "file_age_min": 1.0, "recent_alerts": []}
    base.update(kw)
    return base


# -- dotenv / terminal ----------------------------------------------------------

def test_load_dotenv_setdefault_et_guards(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# commentaire\nSANS_EGALE\nVIDE=\nCLE1=val1\nCLE2=\"quoted\"\n"
                   "CLE3='sq'\nCLE1=ignore-si-present\n", encoding="utf-8")
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path))
    monkeypatch.setenv("CLE1", "garde")
    monkeypatch.delenv("CLE2", raising=False)
    tui._load_dotenv()
    assert tui.os.environ["CLE1"] == "garde"
    assert tui.os.environ["CLE2"] == "quoted"
    assert tui.os.environ["CLE3"] == "sq"
    assert tui.os.environ["VIDE"] == ""
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path / "nope"))
    tui._load_dotenv()  # fichier absent -> silencieux


def test_ioctl_et_term_fallbacks(monkeypatch):
    import struct as _st
    fake_fcntl = type("F", (), {"ioctl": staticmethod(
        lambda fd, op, arg: _st.pack("HHHH", 30, 100, 0, 0))})
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    monkeypatch.setitem(sys.modules, "termios",
                        type("T", (), {"TIOCGWINSZ": 1}))
    assert tui._ioctl_size() == (100, 30)
    monkeypatch.setattr(tui, "_ioctl_size", lambda: (200, 40))
    assert tui.term_width() == 200 and tui.term_height() == 40
    monkeypatch.setattr(tui, "_ioctl_size", lambda: None)
    monkeypatch.setattr(tui.shutil, "get_terminal_size",
                        lambda fallback: (_ for _ in ()).throw(OSError()))
    assert tui.term_width() == 100 and tui.term_height() == 24


def test_ioctl_ignore_petites_valeurs(monkeypatch):
    import struct as _st
    fake_fcntl = type("F", (), {"ioctl": staticmethod(
        lambda fd, op, arg: _st.pack("HHHH", 2, 10, 0, 0))})
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    monkeypatch.setitem(sys.modules, "termios",
                        type("T", (), {"TIOCGWINSZ": 1}))
    assert tui._ioctl_size() is None


# -- largeurs / texte ------------------------------------------------------------

def test_char_et_visible_width_edges():
    assert tui._char_width("\x00") == 0
    assert tui._char_width(123) == 1  # ord() leve -> 1
    assert isinstance(tui._visible_width("\x1b[99999999999999999Xab"), int)
    assert tui._visible_width("\x1b") == 0  # ESC isole : controle -> 0
    assert tui._visible_width("") == 0


def test_fit_cap_et_reset(monkeypatch):
    assert tui._visible_width(tui._fit("x" * 100000, 20)) <= 20
    colored = "\x1b[32m" + "y" * 50
    cut = tui._fit(colored, 10)
    assert tui._visible_width(cut) <= 10 and cut.endswith("\x1b[0m")

    class _Bad:
        def __str__(self):
            raise RuntimeError("boom")

    assert tui._fit(_Bad(), 10) == ""


def test_vpad_et_split_ansi():
    assert tui._vpad("ab", 5) == "ab   "
    assert tui._vpad("ab", "bad") == "ab"
    segs = tui._split_ansi("\x1b[32mok\x1b[0mko")
    assert ("", "ko") in segs
    assert tui._split_ansi("\x1b") == [("", "\x1b")]


def test_wrap_mot_geant_et_coupe(monkeypatch):
    lines = tui._wrap("a" * 100, 10, max_lines=2)
    assert len(lines) <= 2
    long = "mot1 mot2 mot3 mot4 mot5 mot6 mot7 mot8 mot9 mot10 fin"
    cut = tui._wrap(long, 8, max_lines=2)
    assert len(cut) == 2 and cut[-1].endswith("...")
    monkeypatch.setattr(tui, "_visible_width",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    assert tui._wrap("abc", 2) == ["ab"]  # repli : _fit reel


def test_box_side_guards(monkeypatch):
    box = tui._box("T", ["x" * 200], 20, color="nope")
    assert box[0].startswith("+- T ")
    monkeypatch.setattr(tui, "_wrap", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError()))
    assert tui._box("T", ["x"], 20) == ["x"]
    assert tui._side_by_side(["a"], ["b", "c"], 40, 10)[1].strip().endswith("c")
    monkeypatch.setattr(tui, "_fit", lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError()))
    assert tui._side_by_side(["a"], ["b"], 40, 10) == ["a", "b"]
    assert tui._div("x", "bad") == ""


# -- barres / nombres / reseau ----------------------------------------------------

def test_bar_spark_sec_edges(monkeypatch):
    assert tui.bar(50, color="nope").count("\x1b[") == 0
    assert tui._num("abc") == "n/a"
    assert tui.fmt_bytes("12x") == "n/a"
    assert tui._net_rates({"network": {}}, {"network": {}}, 0) == (None, None)
    assert tui._net_rates({}, {}, 1.0) == (None, None)
    assert tui.spark(None) == " " * 24
    assert tui.spark([0, 0]) == " " * 24
    assert tui.spark("boom") == "?" * 24
    monkeypatch.setitem(sys.modules, "psutil", None)
    assert tui._uptime() == "n/a"


def test_sec_cpu_mem_hist_et_vide():
    rows = tui.sec_cpu_mem(_payload(), {"cpu": [1.0, 2.0], "mem": [3.0]})
    assert any("CPU graph" in r for r in rows)
    bare = tui.sec_cpu_mem({"cpu": {}, "memory": {}}, None)
    assert any("n/a%" in r for r in bare)


def test_sec_disk_net_variants():
    prev = {"network": {"io": {"bytes_sent": 0, "bytes_recv": 0}}}
    rows = tui.sec_disk_net(_payload(), prev, 2.0,
                            {"up": [1.0, 2.0], "down": [3.0, 4.0]})
    assert any("UP" in r and "DOWN" in r for r in [" ".join(rows)])
    vide = tui.sec_disk_net({"disk": {}, "network": {}}, None, 0.0,
                            None, max_parts=0)
    assert any("n/a" in r for r in vide)
    assert tui.sec_extra({}) == []


def test_sec_procs_filtre_vide_et_detail_sans_date():
    payload = {"processes": [{"pid": 1, "name": "ssh", "cpu": 1.0}]}
    rows = tui.sec_procs(payload, 60, filt="zzz")
    assert any("aucun processus" in r for r in rows)
    card = tui.sec_proc_detail({"pid": 1, "name": "x", "created": None,
                                "cpu_user": None})
    assert any("?" in line for line in card)


def test_sec_kuro_compteurs_degrades():
    kuro = _kuro(repos_fs="bad", file_age_min="bad")
    assert "projets 3" in tui.sec_kuro(kuro)[0]
    kuro2 = _kuro(replica={"projects": 9, "file_age_min": None})
    assert any("9 projets" in line for line in tui.sec_kuro(kuro2))
    assert tui.sec_projects(None) != []


def test_sec_agents_exception(monkeypatch):
    monkeypatch.setattr(tui, "agents_lines",
                        lambda: (_ for _ in ()).throw(RuntimeError()))
    assert tui.sec_agents() == ["AGENTS (indisponible)"]
    monkeypatch.setattr(tui, "agents_lines", lambda: ["l1"])
    assert tui.sec_agents() == ["AGENTS", "l1"]


# -- marketing / jambes / cerveau --------------------------------------------------

def test_marketing_fichiers_vides_et_bornes(tmp_path, monkeypatch):
    root = tmp_path / "r"
    root.mkdir()
    (root / "pipeline.local.json").write_text("{}", encoding="utf-8")
    (root / "LAUNCH_POSTS.md").write_text(
        "## Checklist\ngeneral\n## Post A\n- [x] 1\n- [x] 2\n- [x] 3\n",
        encoding="utf-8")
    (root / "docs" / "tracking").mkdir(parents=True)
    (root / "docs" / "tracking" / "acquisition_tracker.md").write_text(
        "rien ici\n", encoding="utf-8")
    monkeypatch.setenv("KURO_RULES_DIR", str(root))
    lines = tui.sec_marketing()
    assert any("drafts : 1 posts" in line for line in lines), lines  # cap 3->1
    assert tui._marketing_launch(root) == (1, 1)
    assert tui._marketing_tracker(root) == (0, "acquisition_tracker.md")
    assert tui._load_json_obj(root / "pipeline.local.json") == {}
    (root / "bad.json").write_text("[1,2]", encoding="utf-8")
    assert tui._load_json_obj(root / "bad.json") == {}
    assert tui._marketing_pipeline(root) == (0, 0, "", "")


def test_jambes_variantes(monkeypatch, tmp_path):
    import json as _js
    import urllib.request as _url
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", tmp_path / "nope.jsonl")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("KURO_ROUTER", raising=False)
    monkeypatch.delenv("KURO_POLLINATIONS", raising=False)
    assert "pollinations ?" in tui._legs_line()[0]
    monkeypatch.setenv("OLLAMA_MODEL", "qwen:8b")
    # fixture : urlopen mort -> daemon injoignable
    assert "local DOWN" in tui._legs_line()[0]

    class _Resp:
        def read(self):
            return _js.dumps({"models": [{"name": "qwen:8b"}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    tui._OLLAMA_CACHE.update({"ts": _stale(120), "ok": False, "names": []})
    monkeypatch.setattr(_url, "urlopen", lambda *a, **k: _Resp())
    assert "local OK" in tui._legs_line()[0]
    monkeypatch.setenv("OLLAMA_MODEL", "x:cloud")
    assert "local off" in tui._legs_line()[0]
    monkeypatch.setenv("KURO_ROUTER", "litellm")
    assert "litellm on" in tui._legs_line()[0]


def test_usage_stats_fenetre_et_casse(tmp_path, monkeypatch):
    from datetime import date, timedelta
    usage = tmp_path / "u.jsonl"
    vieux = (date.today() - timedelta(days=30)).isoformat()
    usage.write_text("pas-du-json\n"
                     + json.dumps({"day": vieux, "est_cost_usd": 9.0,
                                   "engine": "vieux"}) + "\n"
                     + json.dumps({"day": date.today().isoformat(),
                                   "est_cost_usd": "bad",
                                   "engine": "e", "latency_s": 2.0}) + "\n"
                     + json.dumps({"day": date.today().isoformat(),
                                   "engine": "cache", "latency_s": 0.0}) + "\n",
                     encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    stats = tui._usage_stats()
    (calls_d, cost_d, unk_d, cache_d,
     calls_w, cost_w, unk_w, cache_w, top, lat) = stats
    assert (calls_w, cost_w, lat) == (1, 0.0, "2.0")
    assert (cache_d, cache_w) == (1, 1)
    assert (unk_d, unk_w) == (0, 0)
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", tmp_path / "nope.jsonl")
    assert tui._usage_stats() == (0, 0.0, 0, 0, 0, 0.0, 0, 0, "?", "?")


def test_rules_dir_candidats(tmp_path, monkeypatch):
    orig = tui._rules_dir_cached
    monkeypatch.delenv("KURO_RULES_DIR", raising=False)
    monkeypatch.setattr(tui, "_rules_dir_cached", lambda: Path("/x"))
    assert tui._rules_dir() == Path("/x")
    monkeypatch.setattr(tui, "_rules_dir_cached", orig)
    cwd = tmp_path / "work"
    cwd.mkdir()
    (cwd / "pipeline.local.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(cwd)
    orig.cache_clear()
    try:
        assert tui._rules_dir() == cwd
    finally:
        orig.cache_clear()
    monkeypatch.setenv("KURO_RULES_DIR", "   ")
    orig.cache_clear()
    try:
        assert isinstance(tui._rules_dir(), Path)
    finally:
        orig.cache_clear()


# -- rendu large / compact auto ------------------------------------------------------

def test_render_wide_sidebar_et_caches(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 160)
    frame = tui.render_frame(_payload(), None, 2.0, kuro=_kuro(), now=1.0,
                             hist={"cpu": [1.0, 2.0], "mem": [1.0, 2.0],
                                   "up": [1.0, 2.0], "down": [1.0, 2.0]})
    assert "GLANCES KURO" in frame and "MARKETING" in frame
    sans = tui.render_frame(_payload(), None, 2.0, kuro=_kuro(), now=1.0,
                            hidden=("kuro", "cpu", "net", "proc", "market"))
    assert "2 CPU" not in sans and "MARKETING" not in sans


def test_render_compact_auto_et_pad(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui, "term_height", lambda: 200)
    monkeypatch.setattr(tui.sys.stdout, "isatty", lambda: True)
    frame = tui.render_frame(_payload(), kuro=_kuro(), now=1.0)
    assert "GLANCES KURO" in frame


def test_render_filtre_pied_et_detail(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    detail = {"pid": 7, "name": "x", "created": None}
    frame = tui.render_frame(_payload(), filt="ini", sel=0, detail=detail)
    assert "filtre:ini" in frame and "DETAIL pid 7" in frame


def test_visible_procs_bizarres():
    assert tui._visible_procs("boom", "cpu", "") == []
    assert len(tui._visible_procs({"processes": [{"pid": 1}]}, limit=0)) == 1


def test_collect_once_tolerant(monkeypatch):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda **k: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(tui, "collect_kuro_snapshot",
                        lambda: (_ for _ in ()).throw(RuntimeError()))
    assert tui._collect_once(10) == ({}, None)


# -- clavier / watch / main ------------------------------------------------------------

class _ScriptedKeys:
    def __init__(self, seq):
        self._seq = list(seq)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self._seq.pop(0) if self._seq else "q"


def test_read_key_sequences():
    assert tui._read_key(_ScriptedKeys(["\x1b[A"])) == "up"
    assert tui._read_key(_ScriptedKeys(["\x1b[B"])) == "down"
    assert tui._read_key(_ScriptedKeys(["x"])) == "x"

    class _Esc:
        def __init__(self):
            self._n = 0

        def read(self):
            self._n += 1
            return "\x1b" if self._n == 1 else ("[A" if self._n == 2 else None)

    assert tui._read_key(_Esc()) == "up"

    class _EscBad:
        def read(self):
            return "\x1b"

    class _EscDownTrou:
        def __init__(self):
            self._n = 0

        def read(self):
            self._n += 1
            if self._n == 1:
                return "\x1b"
            if self._n == 2:
                return None  # trou -> continue
            return "[B"

    # seq inconnue puis plus rien -> None (polls courts)
    import time as _t
    _t0 = _t.sleep
    _t.sleep = lambda s: None
    try:
        assert tui._read_key(_EscBad()) is None
        assert tui._read_key(_EscDownTrou()) == "down"
    finally:
        _t.sleep = _t0

    class _Boom:
        def read(self):
            raise RuntimeError()

    assert tui._read_key(_Boom()) is None
    assert tui._read_key(_ScriptedKeys([None])) is None


def test_read_line_edition(capsys):
    keys = _ScriptedKeys(["a", "b", "\x7f", "c", "\r"])
    assert tui._read_line(keys) == "ac"
    assert tui._read_line(_ScriptedKeys(["\x1b"])) is None

    class _Boom:
        def read(self):
            raise RuntimeError()

    assert tui._read_line(_Boom()) is None


def _save_boxes():
    return [dict(b) for b in tui._BOX_DEFS]


def _restore_boxes(saved):
    tui._BOX_DEFS.clear()
    tui._BOX_DEFS.extend(saved)


def test_register_box_cycle(monkeypatch):
    saved = _save_boxes()
    try:
        assert tui.register_box("", "X", "cyan", lambda: ["x"]) == ""
        assert tui.register_box("market", "X", "cyan", lambda: ["x"]) == ""
        assert tui.register_box("seo", "X", "cyan", lambda: ["x"]) == ""
        assert tui.register_box("cpu", "X", "cyan", lambda: ["x"]) == ""
        assert tui.register_box("x", "X", "cyan", "pas-callable") == ""
        num = tui.register_box("demo", "Demo Box", "nope-color", lambda: ["hello"])
        assert num == "8"
        assert tui._BOX_DEFS[-1]["title"] == "8 Demo Box"
        assert tui._BOX_DEFS[-1]["color"] == "cyan"
        monkeypatch.setattr(tui, "term_width", lambda: 80)
        assert "8 Demo Box" in tui.render_frame(_payload(), kuro=_kuro(), now=1.0)
        sans = tui.render_frame(_payload(), kuro=_kuro(), now=1.0,
                                hidden=("demo",))
        assert "8 Demo Box" not in sans
        assert "8 demo" in " ".join(tui._help_rows())
        # 9 puis saturation (7 pris par SEO)
        assert tui.register_box("b9", "B9", "cyan", lambda: ["9"]) == "9"
        assert tui.register_box("b10", "B10", "cyan", lambda: ["x"]) == ""
    finally:
        _restore_boxes(saved)


def test_extra_box_erreur_rendue(monkeypatch):
    saved = _save_boxes()
    try:
        def _boom():
            raise RuntimeError("panne extension")

        assert tui.register_box("boom", "Boom", "cyan", _boom) == "8"
        monkeypatch.setattr(tui, "term_width", lambda: 80)
        frame = tui.render_frame(_payload(), kuro=_kuro(), now=1.0)
        assert "(indisponible)" in frame
    finally:
        _restore_boxes(saved)


def test_use_gardes_malformes():
    assert tui._swap_rates({"memory": None}, {"memory": None}, 1.0) == (None, None)
    assert tui._disk_busy({"disk": None}, {"disk": None}, 1.0) is None
    bad = {"host": {"cpu_count": "x"}, "cpu": {"percent": 1.0,
                                               "load_avg": ["y"]}, "memory": {}}
    assert not any("charge" in r for r in tui.sec_cpu_mem(bad, None))
    assert tui.sec_procs("pas-un-dict", 60) == [
        "TOP PROCESSUS  (tri CPU)",
        "  (liste indisponible : installez psutil sur l hote)"]
    assert isinstance(tui.sec_disk_net({"network": "boom"}, None, 1.0), list)


def test_latency_pcts_gardes(tmp_path, monkeypatch):
    usage = tmp_path / "u.jsonl"
    usage.write_text("[1]\n{bad json\n", encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    assert tui._latency_pcts() == {}


def test_strat_delta_negatif_et_secours(monkeypatch):
    assert tui._strat_delta(1.0, 2.0, " mois") == "-1 mois ▼"
    assert tui._strat_delta("x", 1.0) == "?"
    monkeypatch.setattr(tui, "_strategy_history",
                        lambda: (_ for _ in ()).throw(RuntimeError()))
    assert tui.sec_strategy() == ["STRATÉGIE (indisponible)"]


def test_registre_gardes(monkeypatch):
    monkeypatch.setattr(tui, "_BOX_DEFS", None)
    assert tui._extra_boxes(set(), 80) == []
    assert tui.register_box("x", "X", "cyan", lambda: ["x"]) == ""
    assert "extensions" not in " ".join(tui._help_rows())


def test_watch_key2box_garde(monkeypatch, capsys):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    monkeypatch.setattr(tui, "_BOX_DEFS", None)
    monkeypatch.setattr(tui, "_RawKeys", lambda: _ScriptedKeys(["q"]))
    assert tui.watch(interval=5, top=3) == 0


def test_doctor_etats(monkeypatch, tmp_path):
    monkeypatch.setattr(tui, "LLM_LAST_FILE", tmp_path / "nope.json")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", tmp_path / "nope.jsonl")
    monkeypatch.setattr(tui, "collect_kuro_snapshot",
                        lambda: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    rows = dict((n, (ok, d)) for n, ok, d in tui.doctor())
    assert rows["daemon"] == (False, "erreur lecture")
    assert rows["ollama-local"][0] is True  # non configure -> off=True honnete
    assert "journal-llm" in rows
    monkeypatch.setattr(tui, "collect_kuro_snapshot",
                        lambda: {"db_present": False})
    assert dict((n, ok) for n, ok, d in tui.doctor())["daemon"] is False
    monkeypatch.setattr(tui, "collect_kuro_snapshot",
                        lambda: {"db_present": True, "heartbeat_age_min": 99.0})
    assert dict((n, ok) for n, ok, d in tui.doctor())["daemon"] is False
    monkeypatch.setenv("OLLAMA_MODEL", "qwen:8b")
    monkeypatch.setattr(tui, "_ollama_state", lambda: (True, ["qwen:8b"]))
    assert dict((n, ok) for n, ok, d in tui.doctor())["ollama-local"] is True


def test_main_doctor_codes(monkeypatch, capsys):
    monkeypatch.setattr(tui, "doctor", lambda: [("a", True, "ok")])
    assert tui.main(["--doctor"]) == 0
    assert "[OK ] a" in capsys.readouterr().out
    monkeypatch.setattr(tui, "doctor", lambda: [("a", False, "ko")])
    assert tui.main(["--doctor"]) == 1


def test_watch_toutes_touches(monkeypatch, capsys):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    import kuro_dashboard.system as _sys
    monkeypatch.setattr(_sys, "proc_detail", lambda pid: {"pid": pid})
    seq = [" ", " ", "+", "-", "c", "m", "1", "2", "3", "4", "5", "h",
           "r", "down", "\n", "\n", "up", "/", "a", "\r", "q"]
    monkeypatch.setattr(tui, "_RawKeys", lambda: _ScriptedKeys(seq))
    assert tui.watch(interval=0.1, top=3) == 0
    assert "GLANCES KURO" in capsys.readouterr().out


def test_watch_compact_auto_tty(monkeypatch, capsys):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui, "term_height", lambda: 20)
    monkeypatch.setattr(tui.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    monkeypatch.setattr(tui, "_RawKeys", lambda: _ScriptedKeys(["q"]))
    assert tui.watch(interval=5, top=3, compact=None) == 0


def test_main_tty_compact_et_interrupt(monkeypatch, capsys):
    monkeypatch.setattr(tui.sys.stdout, "isatty", lambda: True)
    seen = {}
    def _fake_watch(interval=2.0, top=10, compact=None):
        seen["compact"] = compact
        return 0

    monkeypatch.setattr(tui, "watch", _fake_watch)
    assert tui.main(["--compact", "--top", "3"]) == 0
    assert seen["compact"] is True
    monkeypatch.setattr(tui, "watch",
                        lambda **k: (_ for _ in ()).throw(KeyboardInterrupt()))
    assert tui.main([]) == 130


# -- vague 3 : dernieres branches -------------------------------------------------

def test_dotenv_dossier_env(tmp_path, monkeypatch):
    (tmp_path / ".env").mkdir()
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path))
    tui._load_dotenv()  # read_text sur dossier -> except silencieux


def test_ioctl_continue_puis_ok(monkeypatch):
    import struct as _st
    calls = []

    def _ioctl(fd, op, arg):
        calls.append(fd)
        if len(calls) == 1:
            raise OSError("fd mort")
        return _st.pack("HHHH", 30, 100, 0, 0)

    fake_fcntl = type("F", (), {"ioctl": staticmethod(_ioctl)})
    monkeypatch.setitem(sys.modules, "fcntl", fake_fcntl)
    monkeypatch.setitem(sys.modules, "termios",
                        type("T", (), {"TIOCGWINSZ": 1}))
    assert tui._ioctl_size() == (100, 30)


def test_visible_width_char_boom(monkeypatch):
    monkeypatch.setattr(tui, "_char_width",
                        lambda ch: (_ for _ in ()).throw(RuntimeError()))
    assert tui._visible_width("abc") == 3


def test_fit_escape_malforme():
    assert tui._visible_width(tui._fit("\x1b[31", 10)) <= 10
    assert tui._visible_width(tui._fit("\x1b[" + "3" * 20, 10)) <= 10


def test_split_ansi_non_str():
    assert tui._split_ansi(None) == [("", None)]


def test_wrap_flush_puis_geant_et_style():
    lines = tui._wrap("abc " + "d" * 50, 10)
    assert lines[0] == "abc"
    styled = tui._wrap("aa \x1b[32mbb cc dd ee ff", 4)
    assert len(styled) >= 2
    reset = tui._wrap("\x1b[32m" + "word " * 10, 8)
    assert all("\x1b[0m" in line or line.endswith("...") for line in reset)


def test_fmt_petabytes_et_net_malforme():
    assert tui.fmt_bytes(1024 ** 6).endswith("TB")
    assert tui._net_rates({"network": {"io": 5}},
                          {"network": {"io": 5}}, 1.0) == (None, None)


def test_sec_proc_detail_date_casse():
    card = tui.sec_proc_detail({"pid": 1, "name": "x", "created": "bad"})
    assert card[-1] == "  demarre : ?"


def test_sec_kuro_projets_texte():
    assert "projets 0" in tui.sec_kuro(
        _kuro(projects="bad", repos_fs="bad"))[0]


def test_sec_projects_exception(monkeypatch):
    monkeypatch.setattr(tui, "git_project_lines",
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError()))
    assert tui.sec_projects(None) == []


def test_usage_latence_casse(tmp_path, monkeypatch):
    from datetime import date
    usage = tmp_path / "u.jsonl"
    usage.write_text(json.dumps({"day": date.today().isoformat(),
                                 "est_cost_usd": 1.5, "engine": "e",
                                 "latency_s": "bad"}) + "\n",
                     encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    assert tui._usage_stats() == (1, 1.5, 0, 0, 1, 1.5, 0, 0, "e", "?")


def test_rules_dir_home_casse(monkeypatch):
    monkeypatch.delenv("KURO_RULES_DIR", raising=False)
    orig = tui._rules_dir_cached
    monkeypatch.setattr(Path, "exists", lambda self: False)
    monkeypatch.setattr(Path, "home",
                        classmethod(lambda cls: (_ for _ in ()).throw(
                            OSError("home mort"))))
    orig.cache_clear()
    try:
        assert tui._rules_dir_cached() == Path(".")
    finally:
        orig.cache_clear()


def test_render_compact_auto_term_casse(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui, "term_height",
                        lambda: (_ for _ in ()).throw(RuntimeError("tty mort")))
    assert "GLANCES KURO" in tui.render_frame(_payload(), kuro=_kuro())


def test_rules_dir_pas_de_dossiers(monkeypatch):
    # delenv : en CI, KURO_RULES_DIR est renseigne (branche env prioritaire).
    monkeypatch.delenv("KURO_RULES_DIR", raising=False)
    orig = tui._rules_dir_cached
    monkeypatch.setattr(Path, "is_dir", lambda self: False)
    orig.cache_clear()
    try:
        assert tui._rules_dir_cached() == Path.home() / "Documents" / "kuro-rules"
    finally:
        orig.cache_clear()


def test_load_json_absent(tmp_path):
    assert tui._load_json_obj(tmp_path / "nope.json") == {}


def test_pipeline_entrees_filtrees(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "pipeline.local.json").write_text(
        json.dumps({"entries": [{"type": "interview", "date": "x"}]}),
        encoding="utf-8")
    assert tui._marketing_pipeline(root)[0] == 1
    (root / "pipeline.local.json").write_text(
        json.dumps({"entries": ["pas-un-dict"]}), encoding="utf-8")
    assert tui._marketing_pipeline(root)[0] == 0


def test_pipeline_get_casse(tmp_path, monkeypatch):
    class _BadType(dict):
        def get(self, key, *a, **k):
            if key == "type":
                raise RuntimeError("get mort")
            return super().get(key, *a, **k)

    root = tmp_path / "r2"
    root.mkdir()
    monkeypatch.setattr(tui, "_load_json_obj",
                        lambda path: {"entries": [_BadType(
                            type="interview", date="2026-10-05",
                            insight="i", next_step="n")]})
    total, itw, _, _ = tui._marketing_pipeline(root)
    assert (total, itw) == (1, 0)


def test_tracker_dossier_au_lieu_de_fichier(tmp_path):
    root = tmp_path / "r"
    root.mkdir()
    (root / "acquisition_tracker.md").mkdir()
    assert tui._marketing_tracker(root) == (0, "?")


def test_marketing_absent_et_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path / "vide"))
    assert "absentes" in tui.sec_marketing()[0]
    monkeypatch.setattr(tui, "_rules_dir",
                        lambda: (_ for _ in ()).throw(RuntimeError()))
    assert tui.sec_marketing() == ["MARKETING (indisponible)"]


def test_file_age_heures(tmp_path):
    import os as _os
    import time as _t
    f = tmp_path / "f.txt"
    f.write_text("x", encoding="utf-8")
    # Milieu du seau 3h (pas la borne exacte : horloge CI granuleuse/NTP).
    old = _t.time() - 3.5 * 3600
    _os.utime(f, (old, old))
    assert "3h" in tui._file_age_txt(f)


def test_rel_age_minutes():
    from datetime import datetime, timedelta
    stamp = datetime.now().astimezone() - timedelta(minutes=10)
    assert tui._rel_age(stamp.isoformat(timespec="seconds")) == "il y a 10 min"


def test_recent_legs_contenus_durs(tmp_path, monkeypatch):
    usage = tmp_path / "u.jsonl"
    usage.write_text("pas-du-json{\n[1, 2]\n"
                     + json.dumps({"day": {"x": 1},
                                   "legs": [[None, "v"]]}) + "\n"
                     + json.dumps({"day": "2026-10-05", "legs": [5]}) + "\n",
                     encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    legs = tui._recent_legs()
    assert legs.get("None") == "v"
    assert tui._recent_legs(max_age_days="bad") == legs


def test_stdout_mort_partout(monkeypatch):
    class _BoomOut:
        def isatty(self):
            raise RuntimeError("stdout mort")

        def write(self, s):
            pass

        def flush(self):
            pass

    monkeypatch.setattr(tui.sys, "stdout", _BoomOut())
    assert tui._stdout_is_tty() is False
    assert tui._colors_on() is False
    assert "GLANCES KURO" in tui.render_frame(_payload(), kuro=_kuro())


def test_render_compact_pad_mort(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(tui, "term_height",
                        lambda: (_ for _ in ()).throw(RuntimeError("tty mort")))
    frame = tui.render_frame(_payload(), kuro=_kuro(), now=1.0, compact=True)
    assert "1 KURO" in frame


def test_rules_dir_cached_env_direct(monkeypatch, tmp_path):
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path))
    orig = tui._rules_dir_cached
    orig.cache_clear()
    try:
        assert tui._rules_dir_cached() == tmp_path
    finally:
        orig.cache_clear()


def test_rules_dir_cached_cwd_mort(monkeypatch):
    monkeypatch.delenv("KURO_RULES_DIR", raising=False)
    orig = tui._rules_dir_cached
    monkeypatch.setattr(Path, "cwd",
                        classmethod(lambda cls: (_ for _ in ()).throw(
                            OSError("cwd mort"))))
    orig.cache_clear()
    try:
        assert isinstance(tui._rules_dir_cached(), Path)
    finally:
        orig.cache_clear()


def test_rules_dir_cached_resolve_mort(monkeypatch):
    monkeypatch.delenv("KURO_RULES_DIR", raising=False)
    orig = tui._rules_dir_cached
    monkeypatch.setattr(Path, "resolve",
                        lambda self: (_ for _ in ()).throw(
                            OSError("resolve mort")))
    orig.cache_clear()
    try:
        assert isinstance(tui._rules_dir_cached(), Path)
    finally:
        orig.cache_clear()


def test_rules_dir_cached_isdir_mort(monkeypatch):
    monkeypatch.delenv("KURO_RULES_DIR", raising=False)
    orig = tui._rules_dir_cached
    monkeypatch.setattr(Path, "is_dir",
                        lambda self: (_ for _ in ()).throw(
                            OSError("disque mort")))
    orig.cache_clear()
    try:
        assert isinstance(tui._rules_dir_cached(), Path)
    finally:
        orig.cache_clear()


def test_rules_dir_cached_environ_mort(monkeypatch):
    _boom_environ(monkeypatch, "KURO_RULES_DIR")
    orig = tui._rules_dir_cached
    orig.cache_clear()
    try:
        assert tui._rules_dir_cached() == Path(".")
    finally:
        orig.cache_clear()


def test_pipeline_outer_exception(tmp_path, monkeypatch):
    class _BadDict(dict):
        def get(self, *a, **k):
            raise RuntimeError("get mort")

    root = tmp_path / "rp"
    root.mkdir()
    monkeypatch.setattr(tui, "_load_json_obj",
                        lambda path: _BadDict(entries=[]))
    assert tui._marketing_pipeline(root) == (0, 0, "", "")


@pytest.mark.skipif(os.name != "nt",
                        reason="touches Windows : msvcrt et console 1252")
def test_msvcrt_getch_boom(monkeypatch):
    import types as _t
    fake = _t.ModuleType("msvcrt")
    fake.kbhit = lambda: True
    fake.getch = lambda: (_ for _ in ()).throw(RuntimeError("clavier mort"))
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    with tui._RawKeys() as keys:
        assert keys.read() is None


def test_legs_line_exception(monkeypatch):
    _boom_environ(monkeypatch, "OPENROUTER_API_KEY")
    assert tui._legs_line() == []


def test_titled_non_liste():
    assert tui._titled("a", 5, 10) == []


def test_render_compact_avec_detail(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui, "term_height", lambda: 200)
    monkeypatch.setattr(tui.sys.stdout, "isatty", lambda: True)
    frame = tui.render_frame(_payload(), kuro=_kuro(), now=1.0, compact=True,
                             detail={"pid": 7, "name": "x"})
    assert "DETAIL pid 7" in frame


def test_render_compact_auto_term_casse_tty(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(tui, "term_height",
                        lambda: (_ for _ in ()).throw(RuntimeError("tty mort")))
    assert "GLANCES KURO" in tui.render_frame(_payload(), kuro=_kuro())


def test_render_wide_avec_detail(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 160)
    frame = tui.render_frame(_payload(), None, 2.0, kuro=_kuro(), now=1.0,
                             detail={"pid": 9, "name": "z"})
    assert "DETAIL pid 9" in frame


@pytest.mark.skipif(os.name != "nt",
                        reason="touches Windows : msvcrt et console 1252")
def test_msvcrt_fleches(monkeypatch):
    import types as _t

    def _mk(seq):
        fake = _t.ModuleType("msvcrt")
        it = iter(seq)
        fake.kbhit = lambda: True
        fake.getch = lambda: next(it)
        return fake

    monkeypatch.setitem(sys.modules, "msvcrt", _mk([b"\xe0", b"H"]))
    with tui._RawKeys() as keys:
        assert keys.read() == "\x1b[A"
    monkeypatch.setitem(sys.modules, "msvcrt", _mk([b"\x00", b"x"]))
    with tui._RawKeys() as keys:
        assert keys.read() is None
    monkeypatch.setitem(sys.modules, "msvcrt", _mk([b"q"]))
    with tui._RawKeys() as keys:
        assert keys.read() == "q"
    monkeypatch.setitem(sys.modules, "msvcrt", _mk(["pas-des-bytes"]))
    with tui._RawKeys() as keys:
        assert keys.read() is None


def test_read_line_none_puis_valide(capsys):
    assert tui._read_line(_ScriptedKeys(["a", None, None, "\r"])) == "a"


def test_visible_procs_tri_casse():
    procs = {"processes": [{"pid": 1, "cpu": "high"}, {"pid": 2, "cpu": 5.0}]}
    assert len(tui._visible_procs(procs, "cpu", "")) == 2


def test_watch_compact_auto_exception(monkeypatch, capsys):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(tui, "term_height",
                        lambda: (_ for _ in ()).throw(RuntimeError("tty mort")))
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    monkeypatch.setattr(tui, "_RawKeys", lambda: _ScriptedKeys(["q"]))
    assert tui.watch(interval=5, top=3, compact=None) == 0
    assert "GLANCES KURO" in capsys.readouterr().out


def test_watch_detail_erreur_fleche(monkeypatch, capsys):
    """Fiche armee puis "up" : le refresh fleche meurt -> fiche fermee."""
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    import kuro_dashboard.system as _sys
    calls = []

    def _detail(pid):
        calls.append(pid)
        if len(calls) == 1:
            return {"pid": pid, "name": "a"}
        raise RuntimeError("parti")

    monkeypatch.setattr(_sys, "proc_detail", _detail)
    # interval large : toutes les touches dans la meme frame, la fiche
    # reste armee quand "up" la rafraichit (appel 2, boom).
    seq = ["down", "\n", "up", "q"]
    monkeypatch.setattr(tui, "_RawKeys", lambda: _ScriptedKeys(seq))
    assert tui.watch(interval=5, top=3) == 0
    assert len(calls) == 2


def test_watch_fiche_live_morte(monkeypatch, capsys):
    """Fiche armee : le refresh live de la frame suivante meurt."""
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    import kuro_dashboard.system as _sys
    calls = []

    def _detail(pid):
        calls.append(pid)
        if len(calls) == 1:
            return {"pid": pid, "name": "a"}
        raise RuntimeError("parti")

    monkeypatch.setattr(_sys, "proc_detail", _detail)
    # interval petit : 1 touche/frame ; "\n" arme (appel 1), la frame
    # suivante rafraichit (appel 2, boom -> fiche fermee).
    seq = ["down", "\n", "q"]
    monkeypatch.setattr(tui, "_RawKeys", lambda: _ScriptedKeys(seq))
    assert tui.watch(interval=0.1, top=3) == 0
    assert len(calls) == 2


def test_pluriels_et_modeles():
    assert tui._pl(0, "appel") == "appels"
    assert tui._pl(1, "appel") == "appel"
    assert tui._pl(2, "appel") == "appels"
    assert tui._pl("x", "appel") == "appels"
    assert tui._short_model_name("openrouter/nvidia/nemotron:free") == \
        "nemotron:free"
    assert tui._short_model_name("") == ""
    assert tui._short_model_name(None) == ""
    assert tui._unk_txt(0) == ""
    assert tui._unk_txt(1) == " +1 coût inconnu"
    assert tui._unk_txt(3) == " +3 coûts inconnus"


def test_ollama_state_sonde_et_cache(monkeypatch):
    import json as _js
    import urllib.request as _real
    tui._OLLAMA_CACHE.update({"ts": _stale(120), "ok": False, "names": []})

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def read(self):
            return _js.dumps(self._payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    monkeypatch.setattr(_real, "urlopen",
                        lambda url, timeout=2: _Resp(
                            {"models": [{"name": "qwen3:8b"}]}))
    ok, names = tui._ollama_state()
    assert (ok, names) == (True, ["qwen3:8b"])
    # 2e appel : cache, pas de reseau
    monkeypatch.setattr(_real, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(
                            RuntimeError("pas de reseau attendu")))
    assert tui._ollama_state() == (True, ["qwen3:8b"])


def test_short_model_et_unk_robustes():
    class _StrBoom:
        def __str__(self):
            raise RuntimeError("boom")

        def __bool__(self):
            return True

    assert tui._short_model_name(_StrBoom()) == ""
    assert tui._unk_txt("pas-un-nombre") == ""


def test_ollama_cache_illisible(monkeypatch):
    class _BadFloat:
        def __float__(self):
            raise RuntimeError("boom")

    tui._OLLAMA_CACHE.update({"ts": _BadFloat()})
    assert tui._ollama_state() == (False, [])


def test_ollama_state_daemon_mort_et_json_casse(monkeypatch):
    tui._OLLAMA_CACHE.update({"ts": _stale(120), "ok": False, "names": []})
    import urllib.request as _real
    monkeypatch.setattr(_real, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(
                            OSError("daemon mort")))
    assert tui._ollama_state() == (False, [])
    tui._OLLAMA_CACHE.update({"ts": _stale(120), "ok": False, "names": []})

    class _Bad:
        def read(self):
            return b"pas-du-json"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

    monkeypatch.setattr(_real, "urlopen", lambda *a, **k: _Bad())
    assert tui._ollama_state() == (False, [])


def test_usage_couts_inconnus_et_cache(tmp_path, monkeypatch):
    from datetime import date
    usage = tmp_path / "u.jsonl"
    usage.write_text(
        json.dumps({"day": date.today().isoformat(), "engine": "openrouter",
                    "model": "openai/gpt-4o", "est_cost_usd": None,
                    "latency_s": 3.0}) + "\n"
        + json.dumps({"day": date.today().isoformat(), "engine": "cache",
                      "latency_s": 0.0}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    stats = tui._usage_stats()
    (calls_d, cost_d, unk_d, cache_d,
     calls_w, cost_w, unk_w, cache_w, top, lat) = stats
    assert (calls_d, unk_d, cache_d) == (1, 1, 1)
    assert (top, lat) == ("openrouter", "3.0")


def test_sec_brain_modele_inconnu_cache(tmp_path, monkeypatch):
    from datetime import datetime
    now = datetime.now().astimezone().replace(microsecond=0)
    brain = tmp_path / "llm.json"
    brain.write_text(json.dumps(
        {"engine": "openrouter", "model": "openrouter/x/y:free",
         "latency_s": 1.0, "at": now.isoformat(timespec="seconds")}),
        encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_LAST_FILE", brain)
    usage = tmp_path / "u.jsonl"
    usage.write_text(json.dumps({"day": now.date().isoformat(),
                                 "engine": "openrouter",
                                 "model": "openai/gpt-4o",
                                 "est_cost_usd": None,
                                 "latency_s": 1.0}) + "\n",
                     encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    monkeypatch.setattr(tui, "_legs_line", lambda: [])
    rows = tui.sec_brain()
    assert "[y:free]" in rows[0]
    assert "1 appel" in rows[1] and "1 coût inconnu" in rows[1]


def test_latency_pcts(tmp_path, monkeypatch):
    from datetime import date
    usage = tmp_path / "u.jsonl"
    usage.write_text(
        "\n".join(json.dumps({"day": date.today().isoformat(), "engine": "e",
                              "latency_s": v}) for v in (1.0, 2.0, 3.0, 100.0)),
        encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    assert tui._latency_pcts() == {"p50": 3.0, "p95": 100.0}
    usage.write_text(json.dumps({"day": date.today().isoformat(),
                                 "engine": "cache", "latency_s": 0.0}),
                     encoding="utf-8")
    assert tui._latency_pcts() == {}, "cache exclu + <2 valeurs"
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", tmp_path / "nope.jsonl")
    assert tui._latency_pcts() == {}


def test_budgets_affichage(tmp_path, monkeypatch):
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path))
    assert tui._budgets() == {}
    assert tui._budget_txt(1.0, None) == ""
    assert tui._budget_txt(1.0, 0) == ""
    assert tui._budget_txt(1.0, "bad") == ""
    assert tui._budget_txt(1.0, 2.0) == " [$1.0000/$2.00 50%]"
    assert tui._budget_txt(1.7, 2.0).endswith(" !]")
    assert tui._budget_txt(3.0, 2.0).endswith(" !!]")
    (tmp_path / "budgets.local.json").write_text('{"daily_usd": 1.0}',
                                                 encoding="utf-8")
    assert tui._budgets() == {"daily_usd": 1.0}
    (tmp_path / "budgets.local.json").write_text('[1,2]', encoding="utf-8")
    assert tui._budgets() == {}


def test_pricing_versionne(monkeypatch):
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import kuro_llm as _llm
    assert _llm._model_rate("m:x:free", "openrouter") == 0.0
    assert _llm._model_rate("openai/gpt-9", "openrouter") is None
    assert "v" in _llm.pricing_version() and "@" in _llm.pricing_version()
    _llm._PRICING_CACHE.clear()
    monkeypatch.setattr(_llm.Path, "resolve", lambda self: (_ for _ in ()).throw(
        OSError("disque mort")))
    try:
        assert _llm._model_rate("", "deepseek") == 1.0, "repli integre"
    finally:
        _llm._PRICING_CACHE.clear()


def test_sec_brain_cache_seul(tmp_path, monkeypatch):
    from datetime import date
    monkeypatch.setattr(tui, "LLM_LAST_FILE", tmp_path / "nope.json")
    usage = tmp_path / "u.jsonl"
    usage.write_text(json.dumps({"day": date.today().isoformat(),
                                 "engine": "cache", "latency_s": 0.0}) + "\n",
                     encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    monkeypatch.setattr(tui, "_legs_line", lambda: [])
    rows = tui.sec_brain()
    assert any("cache local" in r for r in rows)
    assert any("0 appel" in r for r in rows)


def test_sec_strategy_vide_et_age(tmp_path, monkeypatch):
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path))
    rows = tui.sec_strategy()
    assert any("pas d historique" in r for r in rows)
    hist = [{"date": "2026-09-05", "runway_months": 1.0, "burn": 10.0,
             "mrr": 5.0, "velocity": 1.0, "lead_time": 3.0, "ci_failures": 2,
             "okr_avg_pct": 40.0, "okr_hit": 0, "okr_total": 2,
             "interviews_7d": 0, "pipeline_total": 3, "decisions_open": ["a"]},
            {"date": "2026-10-06", "runway_months": 2.0, "burn": 10.0,
             "mrr": 5.0, "velocity": 2.0, "lead_time": 3.0, "ci_failures": 0,
             "okr_avg_pct": 80.0, "okr_hit": 1, "okr_total": 2,
             "interviews_7d": 2, "pipeline_total": 4, "decisions_open": []}]
    import json as _js
    (tmp_path / "strategy_history.local.json").write_text(_js.dumps(hist),
                                                          encoding="utf-8")
    rows2 = tui.sec_strategy()
    assert any("runway" in r and "+1" in r for r in rows2)
    assert any("0 ouvertes" in r for r in rows2), "le dernier snapshot n'a aucune décision ouverte"
    assert tui._strat_delta(None, 1.0) == "?"
    assert tui._strat_delta("x", 1.0) == "?"
    assert tui._strat_delta(1.0, 1.0) == "="


def test_render_box_strategie_et_touche_6(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    frame = tui.render_frame(_payload(), kuro=_kuro(), now=1.0)
    assert "6 STRAT" in frame
    assert "7 SEO" in frame
    sans = tui.render_frame(_payload(), kuro=_kuro(), now=1.0, hidden=("strat",))
    assert "6 STRAT" not in sans
    sans_seo = tui.render_frame(_payload(), kuro=_kuro(), now=1.0, hidden=("seo",))
    assert "7 SEO" not in sans_seo
    aide = tui.render_frame(_payload(), help=True)
    assert "1-7" in aide


def test_compact_montre_strat_et_seo(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    frame = tui.render_frame(_payload(), kuro=_kuro(), now=1.0, compact=True)
    assert "6 STRAT/SEO" in frame
    assert "runway" in frame or "STRAT" in frame
    sans = tui.render_frame(_payload(), kuro=_kuro(), now=1.0, compact=True,
                            hidden=("strat", "seo"))
    assert "6 STRAT/SEO" not in sans
    rows = frame.splitlines()
    assert len(rows) <= 26


def test_shrink_compact_priorites(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    payload = _payload()
    payload["processes"] = [
        {"pid": i, "name": f"p{i}", "cpu": 1.0, "mem": 1.0} for i in range(5)
    ]
    frame = tui.render_frame(payload, kuro=_kuro(), now=1.0, compact=True)
    rows = frame.splitlines()
    # PROC rogné d'abord, digest gardé, footer intact.
    mid = tui._shrink_compact(rows, len(rows) - 2)
    assert len(mid) <= len(rows) - 2
    assert any(r.startswith("+- 4 ") for r in mid)
    assert any("STRAT/SEO" in r for r in mid)
    assert mid[-1] == rows[-1]
    # Écran minuscule : digest sauté, PROC gardé à 1 ligne, footer intact.
    tiny = tui._shrink_compact(rows, 16)
    assert len(tiny) < len(rows)
    assert tiny[-1] == rows[-1]
    assert any(r.startswith("+- 4 ") for r in tiny)
    assert not any("STRAT/SEO" in r for r in tiny)
    assert tui._shrink_compact(rows, 500) == rows


def test_sec_seo_absent_et_parsing(tmp_path, monkeypatch):
    # Absent (cas PC sans ~/leads) : message honnête, jamais de chiffres inventés.
    monkeypatch.setattr(tui.Path, "home", lambda: tmp_path)
    assert any("pas d audit" in r for r in tui.sec_seo())
    # Présent (cas serveur) : date + P0/P1 + top actions.
    leads = tmp_path / "leads"
    leads.mkdir()
    (leads / "SEO_AUDIT.md").write_text(
        "Date : 2026-10-07\n\n### P0\n1 Fix title\n2 Fix meta\n\n### P1\n1 Add sitemap\n",
        encoding="utf-8")
    rows = tui.sec_seo()
    assert any("P0" in r and "2" in r for r in rows)
    assert any("P1" in r and "1" in r for r in rows)
    assert tui._seo_items("### P0\n1 hello\n### P1\n1 bye", "### P0") == ["hello"]
    assert tui._seo_items("rien", "### P0") == []
    # Format réel du cron serveur (# titre + **Date**: ...).
    (leads / "SEO_AUDIT.md").write_text(
        "# Audit Stratégique Quotidien - SEO\n\n**Date**: 2026-10-08\n\n### P0\n1 Fix title\n",
        encoding="utf-8")
    assert any("2026-10-08" in r for r in tui.sec_seo())


def test_watch_touche_6_cache_box(monkeypatch, capsys):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    monkeypatch.setattr(tui, "_RawKeys", lambda: _ScriptedKeys(["6", "6", "q"]))
    assert tui.watch(interval=0.1, top=3) == 0
    out = capsys.readouterr().out
    frames = out.split("GLANCES KURO")
    assert len(frames) >= 4, "3 frames attendues (visible, cachée, visible)"
    assert "6 STRAT" in frames[1]
    assert "6 STRAT" not in frames[2]
    assert "6 STRAT" in frames[3]


def test_use_saturation_cpu_swap_disque():
    plein = {"host": {"cpu_count": 4},
             "cpu": {"percent": 10.0, "load_avg": [8.0, 1.0, 0.5]},
             "memory": {"percent": 10.0, "swap_sin": 200, "swap_sout": 100}}
    avant = {"memory": {"swap_sin": 0, "swap_sout": 0},
             "disk": {"io": {"read_time": 0, "write_time": 0}},
             "network": {"io": {}}}
    rows = tui.sec_cpu_mem(plein, None, prev=avant, dt=2.0)
    assert any("file d attente" in r for r in rows)
    assert any("pagination swap" in r for r in rows)
    calme = {"host": {"cpu_count": 4},
             "cpu": {"percent": 10.0, "load_avg": [0.5]},
             "memory": {"percent": 10.0}}
    assert not any("file d attente" in r for r in tui.sec_cpu_mem(calme, None))
    assert tui._swap_rates({}, None, 1.0) == (None, None)
    assert tui._swap_rates({"memory": {}}, {"memory": {}}, 1.0) == (None, None)
    assert tui._disk_busy({}, None, 1.0) is None
    occupe = {"disk": {"io": {"read_time": 1900, "write_time": 0}}}
    assert tui._disk_busy(occupe, avant, 2.0) == 95.0
    assert tui._disk_busy({"disk": {}}, {"disk": {}}, 0) is None


def test_net_erreurs_et_etats_processus():
    bruyant = {"disk": {"partitions": []},
               "network": {"io": {"bytes_sent": 0, "bytes_recv": 0,
                                  "errin": 3, "dropout": 2}}}
    assert any("erreurs" in r for r in tui.sec_disk_net(bruyant, None, 0.0))
    payload = {"processes": [{"pid": 1, "name": "z", "cpu": 0.0, "mem": 0.0}],
               "process_states": {"sleeping": 100, "zombie": 2}}
    rows = tui.sec_procs(payload, 60)
    assert any("2 zombie" in r for r in rows)
    sain = {"processes": [],
            "process_states": {"sleeping": 100, "running": 5}}
    assert not any("anormaux" in r for r in tui.sec_procs(sain, 60))


def test_watch_jk_selection(monkeypatch, capsys):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    monkeypatch.setattr(tui, "_RawKeys",
                        lambda: _ScriptedKeys(["j", "k", "q"]))
    assert tui.watch(interval=0.1, top=3) == 0
    out = capsys.readouterr().out
    assert "| > " in out, "la touche j doit sélectionner une ligne (marqueur >)"


def test_watch_entree_erreur_directe(monkeypatch, capsys):
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: _payload())
    monkeypatch.setattr(tui, "collect_kuro_snapshot", lambda: _kuro())
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    monkeypatch.setattr(tui.time, "sleep", lambda s: None)
    import kuro_dashboard.system as _sys
    monkeypatch.setattr(_sys, "proc_detail",
                        lambda pid: (_ for _ in ()).throw(RuntimeError()))
    monkeypatch.setattr(tui, "_RawKeys",
                        lambda: _ScriptedKeys(["down", "\n", "1", "1", "q"]))
    assert tui.watch(interval=0.1, top=3) == 0
