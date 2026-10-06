"""Tests kuro_dashboard.tui — rendus purs, jamais de boucle ni de tty."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import projects as _git_projects  # noqa: E402
from kuro_dashboard import tui  # noqa: E402


@pytest.fixture(autouse=True)
def _fast_integrators(monkeypatch):
    """Rendon pur : coupe les integrations lentes (agents OpenClaw, scan git).

    Couvertes par leurs propres tests (agents, projects). Ici on teste le
    rendu, pas les 13 s de CLI ni les 200 appels git.
    """
    monkeypatch.setattr(tui, "agents_lines", lambda: [])
    monkeypatch.setattr(_git_projects, "discover", lambda force=False: [])
    import urllib.request as _url
    monkeypatch.setattr(_url, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(
                            OSError("pas de reseau en test")))
    monkeypatch.setattr(tui, "_OLLAMA_CACHE", {"ts": 0.0, "ok": False,
                                               "names": []})


def test_bar_shapes():
    assert tui.bar(0) == "[" + "-" * 24 + "]"
    assert tui.bar(100) == "[" + "#" * 24 + "]"
    assert tui.bar(50) == "[" + "#" * 12 + "-" * 12 + "]"
    assert tui.bar(None) == "[" + "?" * 24 + "]"
    assert tui.bar(999).count("#") == 24


def test_fmt_bytes_boundaries():
    assert tui.fmt_bytes(None) == "n/a"
    assert tui.fmt_bytes(500) == "500 B"
    assert tui.fmt_bytes(2 * 1024 ** 3) == "2.0 GB"
    assert tui.fmt_bytes(3 * 1024 ** 4) == "3.0 TB"
    assert tui.fmt_rate(None) == "n/a"
    assert tui.fmt_rate(2048).endswith("/s")


def test_render_minimal_never_crashes():
    frame = tui.render_frame({})
    for section in ("GLANCES KURO", "CPU", "MEM", "DISK", "NET", "TOP PROCESSUS"):
        assert section in frame


def test_render_full_payload():
    payload = {
        "generated_at": "t",
        "psutil_available": True,
        "host": {"hostname": "srv1", "system": "Linux", "cpu_count": 4},
        "cpu": {"percent": 42.0, "per_cpu": [10.0, 90.0], "load_avg": [1.0, 0.5, 0.2]},
        "memory": {"percent": 60.0, "used": 6 * 1024 ** 3, "total": 10 * 1024 ** 3,
                   "swap_percent": 5.0},
        "disk": {"partitions": [{"mount": "/", "percent": 70.0,
                                 "used": 70, "total": 100}]},
        "network": {"io": {"bytes_sent": 1000, "bytes_recv": 2000}},
        "sensors": {"temperatures": [{"label": "cpu", "current": 55}]},
        "gpu": [{"index": "0", "name": "RTX", "util_percent": 80, "temp_c": 65}],
        "docker": {"available": True, "count": 3},
        "processes": [{"pid": 1, "name": "init", "cpu": 99.0, "mem": 1.0}],
    }
    prev = {"network": {"io": {"bytes_sent": 0, "bytes_recv": 0}}}
    frame = tui.render_frame(payload, prev, 2.0)
    for token in ("srv1", "RTX", "cpu:55C", "DOCKER 3", "init", "SWAP"):
        assert token in frame


def test_net_rates_requires_two_samples():
    cur = {"network": {"io": {"bytes_sent": 2000, "bytes_recv": 4000}}}
    assert tui._net_rates(cur, None, 2.0) == (None, None)
    prev = {"network": {"io": {"bytes_sent": 0, "bytes_recv": 0}}}
    sent, recv = tui._net_rates(cur, prev, 2.0)
    assert (sent, recv) == (1000.0, 2000.0)


def test_raw_keys_safe_headless():
    with tui._RawKeys() as keys:
        assert keys.read() is None or isinstance(keys.read(), str)


def test_sec_kuro_states():
    assert tui.sec_kuro(None) == ["KURO donnees non chargees"]
    assert "absente" in tui.sec_kuro({"db_present": False})[0]
    base = {"db_present": True, "projects": 3, "sessions": 9, "alerts_open": 2,
            "memory_nodes": 4, "recent_alerts": [
                {"severity": "high", "message": "x", "created_at": "d",
                 "project": "p"}]}
    assert "SAIN" in tui.sec_kuro({**base, "heartbeat_age_min": 1.0})[0]
    assert "STALE" in tui.sec_kuro({**base, "heartbeat_age_min": 10.0})[0]
    assert "MORT" in tui.sec_kuro({**base, "heartbeat_age_min": 99.0})[0]
    assert "JAMAIS" in tui.sec_kuro({**base, "heartbeat_age_min": None})[0]
    assert "[p]" in tui.sec_kuro({**base, "heartbeat_age_min": 1.0})[1]


def test_render_includes_kuro_section():
    assert "KURO" in tui.render_frame({}, kuro={"db_present": False})


def test_render_includes_face_and_mood():
    frame = tui.render_frame({}, kuro={"db_present": False}, now=2.0)
    assert "(^_^)" in frame
    assert "humeur : CONTENT" in frame


def test_sec_kuro_file_age():
    base = {"db_present": True, "heartbeat_age_min": 1.0, "projects": 1,
            "sessions": 0, "alerts_open": 0, "memory_nodes": 0,
            "recent_alerts": [], "file_age_min": 2.0}
    assert "fichier vieux" not in tui.sec_kuro(dict(base))[0]
    vieux = dict(base, file_age_min=99.0)
    assert "99 min" in tui.sec_kuro(vieux)[0]
    sans = dict(base)
    del sans["file_age_min"]
    assert "fichier vieux" not in tui.sec_kuro(sans)[0]


def test_sec_kuro_replica_line():
    base = {"db_present": True, "heartbeat_age_min": 1.0, "projects": 0,
            "sessions": 0, "alerts_open": 0, "memory_nodes": 0,
            "recent_alerts": [], "file_age_min": 1.0, "replica": None}
    assert not any("replica :" in line for line in tui.sec_kuro(dict(base)))
    avec = dict(base, replica={"projects": 63, "file_age_min": 4.0})
    rows = tui.sec_kuro(avec)
    assert any("replica : 63 projets" in line for line in rows)


def test_sec_brain_states(monkeypatch, tmp_path):
    monkeypatch.setattr(tui, "LLM_LAST_FILE", tmp_path / "nope.json")
    assert "inconnu" in tui.sec_brain()[0]
    good = tmp_path / "llm.json"
    good.write_text('{"engine": "ollama-local", "latency_s": 4.2, "at": "d"}',
                    encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_LAST_FILE", good)
    line = tui.sec_brain()[0]
    assert "ollama-local" in line and "4.2s" in line


def test_watch_renders_then_quits_on_q(monkeypatch, capsys):
    payload = {"generated_at": "t", "host": {"hostname": "srv"},
               "processes": []}
    monkeypatch.setattr(tui, "collect_system_snapshot",
                        lambda top_n=10: payload)
    monkeypatch.setattr(tui, "term_width", lambda: 80)

    class FakeKeys:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return "q"

    monkeypatch.setattr(tui, "_RawKeys", FakeKeys)
    monkeypatch.setattr(tui.time, "sleep", lambda seconds: None)
    assert tui.watch(interval=5, top=3) == 0
    assert "GLANCES KURO" in capsys.readouterr().out


def test_paint_levels():
    assert tui._paint("x", "ok", True) == "\x1b[32mx\x1b[0m"
    assert tui._paint("x", "warn", True).startswith("\x1b[33m")
    assert tui._paint("x", "crit", True).startswith("\x1b[31m")
    assert tui._paint("x", "ok", False) == "x"
    assert tui._paint("x", "nope", True) == "x"
    assert (tui._level(10), tui._level(80), tui._level(95),
            tui._level(None)) == ("ok", "warn", "crit", "dim")
    assert tui.bar(50).count("\x1b[") == 0
    assert tui.bar(50, color="ok").startswith("[\x1b[32m")


def test_pas_de_couleurs_sans_tty():
    frame = tui.render_frame({"host": {}, "cpu": {"percent": 95.0},
                              "memory": {}, "disk": {}, "processes": []})
    assert "\x1b[" not in frame


def test_couleurs_forcees(monkeypatch):
    monkeypatch.setattr(tui, "_colors_on", lambda: True)
    frame = tui.render_frame({"host": {}, "cpu": {"percent": 95.0},
                              "memory": {}, "disk": {}, "processes": []},
                             kuro=None, now=2.0)
    assert "\x1b[31m" in frame


def test_tri_processus():
    payload = {"processes": [{"pid": 1, "name": "a", "cpu": 5.0, "mem": 50.0},
                             {"pid": 2, "name": "b", "cpu": 90.0, "mem": 1.0}]}
    cpu_first = tui.sec_procs(payload, 100)[1]
    mem_first = tui.sec_procs(payload, 100, sort="mem")[1]
    assert " 2 " in cpu_first and "(tri CPU)" in tui.sec_procs(payload, 100)[0]
    assert " 1 " in mem_first and "(tri MEM)" in tui.sec_procs(
        payload, 100, sort="mem")[0]


def test_no_color_flag():
    old = tui._COLOR
    try:
        assert tui.main(["--no-color"]) == 0
        assert tui._COLOR is False
    finally:
        tui._COLOR = old


def test_jambes_tout_off(monkeypatch, tmp_path):
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", tmp_path / "nope.jsonl")
    for var in ("OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "OLLAMA_MODEL",
                "KURO_ROUTER"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("KURO_POLLINATIONS", "0")
    frame = tui.render_frame({}, kuro={"db_present": False})
    assert "jambes : openrouter off" in frame
    assert "litellm off" in frame


def test_jambes_down_apres_echec(monkeypatch, tmp_path):
    usage = tmp_path / "llm_usage.jsonl"
    usage.write_text(json.dumps(
        {"legs": [["openrouter", "error"], ["deepseek", "error"]]}) + "\n",
        encoding="utf-8")
    monkeypatch.setattr(tui, "LLM_USAGE_FILE", usage)
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "cle")
    frame = tui.render_frame({}, kuro={"db_present": False})
    assert "openrouter DOWN" in frame
    assert "deepseek DOWN" in frame


def test_force_color(monkeypatch):
    monkeypatch.setenv("KURO_FORCE_COLOR", "1")
    assert tui._colors_on() is True
    frame = tui.render_frame({"host": {}, "cpu": {"percent": 10.0},
                              "memory": {}, "disk": {}, "processes": []})
    assert "\x1b[32m" in frame


def test_visible_width_emoji_cjk():
    assert tui._visible_width("ab") == 2
    assert tui._visible_width("🚨ab") == 4
    assert tui._visible_width("日本") == 4
    assert tui._visible_width("\x1b[32mok\x1b[0m") == 2
    assert tui._visible_width("é") == 1  # e + combining accent


def test_fit_never_exceeds_visible_width():
    assert tui._visible_width(tui._fit("🚨 alerte critique", 10)) <= 10
    assert tui._visible_width(tui._fit("a\tb\rc", 10)) <= 10
    assert "\t" not in tui._fit("a\tb", 10) and "\r" not in tui._fit("a\rb", 10)


def test_frame_visible_width_capped_with_emoji(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    payload = {"host": {"hostname": "srv"}, "cpu": {"percent": 50.0},
               "memory": {}, "disk": {}, "network": {"io": {}},
               "processes": [{"pid": 1, "name": "🚀svc", "cpu": 9.0, "mem": 1.0}]}
    kuro = {"db_present": True, "projects": 0, "sessions": 0,
            "alerts_open": 1, "memory_nodes": 0, "heartbeat_age_min": 1.0,
            "repos_fs": 1,
            "recent_alerts": [{"severity": "high",
                               "message": "🚨 MORT 日本語",
                               "created_at": "t", "project": "p"}]}
    frame = tui.render_frame(payload, kuro=kuro, now=1.0)
    assert frame
    for line in frame.splitlines():
        assert tui._visible_width(line) <= 80


def test_wrap_keeps_sentence_end(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    msg = ("alerte de demonstration avec une phrase tres longue qui doit "
           "se poursuivre sur la ligne suivante FIN-MARQUEUR")
    kuro = {"db_present": True, "projects": 0, "sessions": 0,
            "alerts_open": 1, "memory_nodes": 0, "heartbeat_age_min": 1.0,
            "repos_fs": 1,
            "recent_alerts": [{"severity": "high", "message": msg,
                               "created_at": "t", "project": "p"}]}
    payload = {"host": {"hostname": "srv"}, "cpu": {"percent": 10.0},
               "memory": {}, "disk": {}, "network": {"io": {}},
               "processes": []}
    frame = tui.render_frame(payload, kuro=kuro, now=1.0)
    assert "FIN-MARQUEUR" in frame
    for line in frame.splitlines():
        assert tui._visible_width(line) <= 80


def test_selection_marker_and_detail():
    payload = {"processes": [{"pid": 1, "name": "a", "cpu": 5.0, "mem": 1.0},
                             {"pid": 2, "name": "b", "cpu": 90.0, "mem": 2.0}]}
    rows = tui.sec_procs(payload, 60, sel=0)
    assert rows[1].startswith(">")
    assert rows[2].startswith(" ")
    detail = {"pid": 9, "name": "x", "cmd": "/bin/x --flag", "user": "u",
              "threads": 3, "rss": 1000, "status": "running",
              "created": 1700000000, "cpu_user": 1.5, "cpu_sys": 0.5}
    card = tui.sec_proc_detail(detail)
    assert card[0] == "DETAIL pid 9 (x)"
    assert any("1.5s user" in line for line in card)
    assert tui.sec_proc_detail(None) == []
    frame = tui.render_frame(payload, sel=0, detail=detail)
    assert "DETAIL pid 9" in frame


def test_visible_procs_filters():
    payload = {"processes": [{"pid": 1, "name": "Chrome", "cpu": 5.0},
                             {"pid": 2, "name": "ssh", "cpu": 9.0}]}
    assert [p["pid"] for p in tui._visible_procs(payload, "cpu", "")] == [2, 1]
    assert [p["pid"] for p in tui._visible_procs(payload, "cpu", "chr")] == [1]
    assert tui._visible_procs({}, "cpu", "") == []


def test_compact_fits_small_console(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 80)
    payload = {"host": {"hostname": "srv"}, "cpu": {"percent": 42.0},
               "memory": {"percent": 60.0, "used": 1, "total": 2},
               "disk": {"partitions": [{"mount": "/", "percent": 70.0,
                                         "used": 1, "total": 2}]},
               "network": {"io": {}},
               "processes": [{"pid": i, "name": f"p{i}", "cpu": 1.0,
                              "mem": 1.0} for i in range(10)]}
    frame = tui.render_frame(payload, kuro=None, now=1.0, compact=True)
    rows = frame.splitlines()
    assert len(rows) <= 26
    assert "1 KURO" in frame and "4 TOP PROCESSUS" in frame
    for line in rows:
        assert tui._visible_width(line) <= 80


def test_boxes_numbered_and_toggleable(monkeypatch):
    monkeypatch.setattr(tui, "term_width", lambda: 100)
    payload = {"host": {"hostname": "s"}, "cpu": {"percent": 10.0},
               "memory": {}, "disk": {}, "network": {"io": {}},
               "processes": []}
    full = tui.render_frame(payload, kuro=None, now=1.0)
    assert "1 KURO" in full and "2 CPU" in full and "4 " in full
    sans_net = tui.render_frame(payload, kuro=None, now=1.0, hidden=("net",))
    assert "DISQUES" not in sans_net and "2 CPU" in sans_net
    aide = tui.render_frame(payload, help=True)
    assert "AIDE" in aide and "quitter" in aide


def test_dividers_width_exact():
    assert tui._div("reseau", 20) == "-- reseau ----------"
    assert len(tui._div("x", 10)) == 10
    assert tui._titled("a", [], 20) == []
    assert tui._titled("a", ["b"], 10)[0] == "-- a -----"


def test_effective_counts_prefer_disk_over_empty_db():
    """Contrat kuro_state : DB legacy vide -> affichage des signaux reels."""
    kuro = {"db_present": True, "projects": 0, "sessions": 0,
            "alerts_open": 0, "memory_nodes": 0, "heartbeat_age_min": 1.0,
            "repos_fs": 55, "summaries_fs": 22, "hb_projects_scanned": 0,
            "recent_alerts": []}
    first = tui.sec_kuro(kuro)[0]
    assert "projets 55" in first
    assert "SAIN" in first
