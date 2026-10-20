"""Tests doctor dashboard + allowlist autodebug (pur, sans reseau sauf loopback)."""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_autodebug as autodebug  # noqa: E402
import kuro_doctor as doctor  # noqa: E402


def test_allowlist_couvre_src_pas_packaging():
    ok, _ = autodebug.is_allowed_path("src/kuro_dashboard/tui.py")
    assert ok is True
    ok, _ = autodebug.is_allowed_path("dashboard/app.js")
    assert ok is True
    for banned in ("packaging/deb/control", "src/x/../.env", ".env",
                   "finances.local.json"):
        ok, _ = autodebug.is_allowed_path(banned)
        assert ok is False, banned


def _suspend_package():
    """Retire kuro_dashboard* de sys.modules en gardant les originaux."""
    return {m: sys.modules.pop(m) for m in list(sys.modules)
            if m == "kuro_dashboard" or m.startswith("kuro_dashboard.")}


def _restore_package(stashed):
    """Vire les faux modules importes entre-temps, restaure les originaux."""
    for m in list(sys.modules):
        if m == "kuro_dashboard" or m.startswith("kuro_dashboard."):
            del sys.modules[m]
    sys.modules.update(stashed)


def test_package_ok_et_ko(tmp_path, monkeypatch):
    pkg = tmp_path / "src" / "kuro_dashboard"
    pkg.mkdir(parents=True)
    # __init__.py OBLIGATOIRE : sinon paquet namespace, et le vrai paquet
    # (regulier) du repo gagne toujours sur le faux (PEP 420).
    (pkg / "__init__.py").write_text('__version__ = "0.0"\n', encoding="utf-8")
    for mod in ("api", "face", "kuro_state", "scan", "system", "tui"):
        (pkg / f"{mod}.py").write_text("X = 1\n", encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path / "src"))
    stashed = _suspend_package()
    try:
        ok, detail = doctor.dashboard_package_ok(tmp_path)
        assert ok is True and "6 modules" in detail
        (pkg / "tui.py").write_text("def broken(:\n", encoding="utf-8")
        _suspend_package()  # vire les faux modules caches (taille changee)
        ok, _ = doctor.dashboard_package_ok(tmp_path)
        assert ok is False
    finally:
        _restore_package(stashed)


def test_commands_ok():
    ok, detail = doctor.tui_commands_ok()
    assert isinstance(ok, bool) and isinstance(detail, str)


def test_resync_et_purge(tmp_path):
    dash = tmp_path / "dashboard"
    static = tmp_path / "src" / "kuro_dashboard" / "static"
    static.mkdir(parents=True)
    dash = tmp_path / "dashboard"
    dash.mkdir(parents=True, exist_ok=True)
    (dash / "index.html").write_text("<p>v2</p>", encoding="utf-8")
    (static / "index.html").write_text("<p>v1</p>", encoding="utf-8")
    assert doctor.resync_static(tmp_path) is True
    assert (static / "index.html").read_text(encoding="utf-8") == "<p>v2</p>"
    cache = tmp_path / "x" / "__pycache__"
    cache.mkdir(parents=True)
    assert doctor.purge_pycache(tmp_path) >= 1
    assert not cache.exists()


def test_live_offline(tmp_path, monkeypatch):
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "src" / "kuro_dashboard" / "static").mkdir(parents=True)
    monkeypatch.setattr(doctor, "DASHBOARD_FILES", ())
    monkeypatch.setattr(doctor, "DASHBOARD_GLOBS", ())
    ok, detail = doctor.dashboard_live_ok(tmp_path, api_base="http://127.0.0.1:9")
    assert ok is False and "injoignable" in detail


def test_live_null_bytes(tmp_path, monkeypatch):
    (tmp_path / "dashboard").mkdir()
    (tmp_path / "src" / "kuro_dashboard" / "static").mkdir(parents=True)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "x.py").write_bytes(b"a = 1\n\x00\x01\x02")
    monkeypatch.setattr(doctor, "DASHBOARD_FILES", ())
    ok, detail = doctor.dashboard_live_ok(tmp_path, api_base="http://127.0.0.1:9")
    assert ok is False and "octets nuls: x.py" in detail




def test_fetch_api_system_retry(monkeypatch):
    """R125 : un premier timeout (API saturée) ne doit pas donner un FAIL."""
    import urllib.request
    calls = {"n": 0}

    class FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"host": {"hostname": "x"}}'

    def fake_open(url, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise TimeoutError("timed out")
        return FakeResp()

    monkeypatch.setattr(urllib.request, "urlopen", fake_open)
    payload = doctor._fetch_api_system("http://127.0.0.1:9", tries=2)
    assert payload["host"]["hostname"] == "x" and calls["n"] == 2
    # Épuisement des essais → l'exception remonte (le FAIL reste possible)
    calls["n"] = 0
    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda *a, **k: (_ for _ in ()).throw(TimeoutError("x")))
    try:
        doctor._fetch_api_system("http://127.0.0.1:9", tries=2)
        assert False, "aurait dû lever"
    except TimeoutError:
        pass

def test_push_frais(tmp_path):
    log = tmp_path / "replica-push.log"
    log.write_text("[replica-push] replica a jour (04:00:00Z)\n", encoding="utf-8")
    ok, detail = doctor.push_freshness(log, 3.0)
    assert ok is True and "replica distant" in detail


def test_push_douteux_quand_ssh_down(tmp_path):
    """R125 : serveur injoignable → PAS de vert mensonger sur le seul log."""
    log = tmp_path / "replica-push.log"
    log.write_text("[replica-push] replica a jour (04:00:00Z)\n", encoding="utf-8")
    ok, detail = doctor.push_freshness(log, None)
    assert ok is False and "injoignable" in detail and "non verifiee" in detail


def test_push_jamais(tmp_path):
    ok, detail = doctor.push_freshness(tmp_path / "nope.log", None)
    assert ok is False and "aucun push" in detail


def test_push_vieux(tmp_path):
    log = tmp_path / "replica-push.log"
    log.write_text("x\n", encoding="utf-8")
    vieux = time.time() - 2 * 3600
    os.utime(log, (vieux, vieux))
    ok, detail = doctor.push_freshness(log, 1.0)
    assert ok is False and "min" in detail


def test_push_silencieux_malgre_log_frais(tmp_path):
    log = tmp_path / "replica-push.log"
    log.write_text("x\n", encoding="utf-8")
    ok, detail = doctor.push_freshness(log, 99.0)
    assert ok is False and "n arrive pas" in detail


# --- Garde R116 (blackout git 16→19/10/2026) ---


def _make_lock(root, age_min):
    gitdir = Path(root) / ".git"
    gitdir.mkdir(parents=True, exist_ok=True)
    lock = gitdir / "index.lock"
    lock.write_text("", encoding="utf-8")
    vieux = time.time() - age_min * 60
    os.utime(lock, (vieux, vieux))
    return lock


def test_verrou_absent_ou_frais_sain(tmp_path):
    ok, detail = doctor.stale_lock_check(tmp_path)
    assert ok is True and "aucun verrou" in detail
    _make_lock(tmp_path, age_min=1)
    ok, detail = doctor.stale_lock_check(tmp_path)
    assert ok is True and "verrou actif" in detail


def test_verrou_orpheline_signalée(tmp_path):
    """Preuve négative de l'incident : lock >15 min = commits bloqués → FAIL."""
    _make_lock(tmp_path, age_min=45)
    ok, detail = doctor.stale_lock_check(tmp_path)
    assert ok is False and "orpheline" in detail and "commits bloqués" in detail


def test_autosync_frais_et_verdict_ok(tmp_path):
    import datetime as dt
    log = tmp_path / "autosync.log"
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    log.write_text(f"{stamp} autosync: rien à synchroniser\n", encoding="utf-8")
    ok, detail = doctor.autosync_freshness(log)
    assert ok is True and "dernière passe" in detail


def test_autosync_muet_ou_vieux_signalé(tmp_path):
    import datetime as dt
    log = tmp_path / "autosync.log"
    assert doctor.autosync_freshness(tmp_path / "absent.log")[0] is False
    log.write_text("", encoding="utf-8")
    assert doctor.autosync_freshness(log)[0] is False
    vieux = (dt.datetime.now(dt.timezone.utc)
             - dt.timedelta(hours=5)).isoformat(timespec="seconds")
    log.write_text(f"{vieux} autosync: OK x\n", encoding="utf-8")
    ok, detail = doctor.autosync_freshness(log, max_age_min=90)
    assert ok is False and "tâche en panne" in detail


def test_autosync_dernier_verdict_ko_signalé(tmp_path):
    import datetime as dt
    log = tmp_path / "autosync.log"
    stamp = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    log.write_text(f"{stamp} autosync: GARDES KO : ruff KO\n", encoding="utf-8")
    ok, detail = doctor.autosync_freshness(log)
    assert ok is False and "en échec" in detail


def test_parse_task_info_pur():
    raw = ("KuroAutoSync|2026-10-19T09:11:00|0\n"
           "KuroDataSync|2026-10-19T09:00:00|1\n"
           "ligne-malformee\n"
           "KuroXDaily|2026-10-19T08:00:00|abc\n")
    info = doctor.parse_task_info(raw)
    assert info["KuroAutoSync"] == ("2026-10-19T09:11:00", 0)
    assert info["KuroDataSync"] == ("2026-10-19T09:00:00", 1)
    assert info["KuroXDaily"] == ("2026-10-19T08:00:00", -1)


def test_scheduled_tasks_health():
    tout_vert = {n: ("2026-10-19T09:00:00", 0) for n in doctor.KURO_TASKS}
    ok, detail = doctor.scheduled_tasks_health(tout_vert)
    assert ok is True and "au vert" in detail
    en_cours = dict(tout_vert, KuroWeekly=("2026-10-19T07:00:00", 267009))
    assert doctor.scheduled_tasks_health(en_cours)[0] is True
    # 267011 = jamais exécutée (normal après réinscription, installateur v3)
    jamais = dict(tout_vert, KuroXDaily=("N/A", 267011))
    assert doctor.scheduled_tasks_health(jamais)[0] is True
    echec = dict(tout_vert, KuroDataSync=("2026-10-19T07:00:00", 1))
    ok, detail = doctor.scheduled_tasks_health(echec)
    assert ok is False and "KuroDataSync result=1" in detail
    ok, detail = doctor.scheduled_tasks_health({})
    assert ok is False and "absente" in detail


def test_scheduled_tasks_health_instance_occupee():
    """0x800710E0 (IgnoreNew) : pas un échec, mais visible dans le détail."""
    tout_vert = {n: ("2026-10-19T09:00:00", 0) for n in doctor.KURO_TASKS}
    occupee = dict(tout_vert, KuroDataSync=("19/10/2026 10:00:00", doctor.TASK_BUSY_RESULT))
    ok, detail = doctor.scheduled_tasks_health(occupee)
    assert ok is True and "occupée" in detail and "KuroDataSync" in detail


# --- Garde R125 (fenêtres CMD) : incident « consoles partout toutes les 5 min » ---

_XML_PYTHONW = "<Command>C:\\Python314\\pythonw.exe</Command><Arguments>x.py</Arguments>"
_XML_PS_HIDDEN = ("<Command>powershell</Command>"
                  "<Arguments>-NoProfile -WindowStyle Hidden -File x.ps1</Arguments>")
_XML_PYTHON_CONSOLE = "<Command>C:\\Python314\\python.exe</Command><Arguments>x.py</Arguments>"
_XML_PS_VISIBLE = "<Command>powershell</Command><Arguments>-File x.ps1</Arguments>"
_XML_BAT = "<Command>C:\\Users\\u\\scripts\\push.bat</Command>"


def test_task_xml_is_hidden():
    assert doctor.task_xml_is_hidden(_XML_PYTHONW) is True
    assert doctor.task_xml_is_hidden(_XML_PS_HIDDEN) is True
    # L'incident réel : python.exe / powershell nu / .bat → fenêtre visible
    assert doctor.task_xml_is_hidden(_XML_PYTHON_CONSOLE) is False
    assert doctor.task_xml_is_hidden(_XML_PS_VISIBLE) is False
    assert doctor.task_xml_is_hidden(_XML_BAT) is False
    assert doctor.task_xml_is_hidden("") is False
    # Case-insensitive : l'installateur peut écrire -WindowStyle en minuscules
    lower = _XML_PS_HIDDEN.lower()
    assert doctor.task_xml_is_hidden(lower) is True


def test_hidden_tasks_health_tout_vert():
    xmls = {n: _XML_PYTHONW for n in doctor.HIDDEN_TASKS}
    xmls["KuroXDaily"] = _XML_PS_HIDDEN
    ok, detail = doctor.hidden_tasks_health(xmls)
    assert ok is True and "fenêtre cachée" in detail
    # Perimetre v3 : 11 tâches Kuro (KuroReplies ajouté en session) + les 2
    # tâches OpenQuant RECREEES le 20/10 avec launchers caches (voir NOTE).
    assert "KuroReplies" in doctor.HIDDEN_TASKS
    assert "OpenQuantWatchdog" in doctor.HIDDEN_TASKS
    assert "OpenQuantDiscovery" in doctor.HIDDEN_TASKS
    assert len(doctor.HIDDEN_TASKS) == 13


def test_hidden_tasks_health_fenetre_visible_signalee():
    """Preuve négative de l'incident : une seule tâche visible = FAIL nommé."""
    xmls = {n: _XML_PYTHONW for n in doctor.HIDDEN_TASKS}
    xmls["KuroReplicaPush"] = _XML_BAT  # le coupable réel (toutes les 5 min)
    ok, detail = doctor.hidden_tasks_health(xmls)
    assert ok is False and "KuroReplicaPush" in detail and "fenêtre visible" in detail


def test_hidden_tasks_health_absente_signalee():
    """R116 : une tâche disparue silencieusement doit être signalée."""
    xmls = {n: _XML_PYTHONW for n in doctor.HIDDEN_TASKS if n != "KuroDataSync"}
    ok, detail = doctor.hidden_tasks_health(xmls)
    assert ok is False and "KuroDataSync absente" in detail
