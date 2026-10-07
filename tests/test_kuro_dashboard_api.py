"""Tests kuro_dashboard.api — routes HTTP, hermetique, DB sqlite tmp."""

import json
import sqlite3
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import api as kap  # noqa: E402
from kuro_dashboard import scan as sc  # noqa: E402


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "kuro.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE projects (id INTEGER, name TEXT, path TEXT, section TEXT, status TEXT, progress_pct INTEGER, last_activity TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE sessions (project_id INTEGER, session_date TEXT, editor TEXT, progress_before INTEGER, progress_after INTEGER, tests_status TEXT, blockers TEXT, next_steps TEXT)")
    conn.execute("CREATE TABLE alerts (id INTEGER, project_id INTEGER, alert_type TEXT, message TEXT, severity TEXT, acknowledged INTEGER, created_at TEXT)")
    conn.execute("CREATE TABLE memory_nodes (node_type TEXT, title TEXT, summary TEXT, level INTEGER, project_id INTEGER, created_at TEXT)")
    conn.execute("CREATE TABLE heartbeat (timestamp TEXT)")
    conn.execute("INSERT INTO projects VALUES (1, 'Demo', '/tmp/demo', 's', 'actif', 42, '2026-10-04 10:00:00', '2026-10-01')")
    conn.execute("INSERT INTO sessions VALUES (1, '2026-10-04 10:30:00', 'ed', 10, 42, 'ok', '', '')")
    conn.execute("INSERT INTO alerts VALUES (1, 1, 't', 'boom', 'high', 0, '2026-10-04 11:00:00')")
    conn.execute("INSERT INTO heartbeat VALUES ('2026-10-04 11:30:00')")
    conn.commit()
    conn.close()
    return db


@pytest.fixture()
def _api_db(tmp_path, monkeypatch):
    db = _db(tmp_path)
    monkeypatch.setattr(kap, "DB_PATH", db)
    monkeypatch.setattr("kuro_dashboard.kuro_state.DB_PATH", db)
    monkeypatch.setattr(sc, "KURO_DB_FILE", db)
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "KURO_ACTIONS_LOG.md").write_text("- action 1\n- action 2\n", encoding="utf-8")
    (rules / "ci-status.json").write_text(
        json.dumps({"overall": "green", "repos": [
            {"name": "Demo", "health": "green",
             "workflows": [{"name": "CI", "conclusion": "success", "url": ""}]},
            {"name": "Vide", "health": "no_ci", "workflows": []}]}),
        encoding="utf-8")
    monkeypatch.setattr(kap, "_rules_dir", lambda: rules)
    return db


def test_rules_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("KURO_RULES_DIR", str(tmp_path))
    assert kap._rules_dir() == tmp_path
    monkeypatch.delenv("KURO_RULES_DIR")
    assert isinstance(kap._rules_dir(), Path)


def test_static_dir_env(monkeypatch, tmp_path):
    monkeypatch.setenv("KURO_STATIC_DIR", str(tmp_path))
    assert kap._static_dir() == tmp_path


def test_rows_et_count(_api_db):
    conn = kap.db()
    try:
        assert isinstance(kap.rows(conn, "SELECT * FROM projects"), list)
        assert kap._count(conn, "SELECT COUNT(*) AS n FROM projects") == 1
        assert kap._count(conn, "SELECT COUNT(*) AS n FROM nope_table") == 0
    finally:
        conn.close()


def test_get_status_projects_sessions(_api_db):
    st = kap.get_status()
    assert st["projects"] == 1
    assert st["alerts_open"] == 1
    assert st["api_version"] == "1.1"
    projs = kap.get_projects()
    assert projs[0]["name"] == "Demo"
    detail = kap.get_project("demo")
    assert detail["progress_pct"] == 42
    assert kap.get_project("inconnu") is None
    alerts = kap.get_alerts(unack_only=True)
    assert len(alerts) == 1
    assert kap.get_sessions(5)[0]["project"] == "Demo"
    mem = kap.get_memory()
    assert isinstance(mem, list)


def test_build_summary_et_robot(_api_db):
    txt = kap.build_summary()
    assert "Projets: 1" in txt
    robot = kap.get_robot()
    assert robot["ci_overall"] == "green"
    assert len(robot["repos"]) == 1  # no_ci filtre
    assert robot["actions_tail"] == ["- action 1", "- action 2"]


def test_compute_status_et_finance_metrics(monkeypatch):
    class _E(Exception):  # noqa: N818 - faux HTTPError minimal pour le test
        def __init__(self, status):
            self.status = status
    assert kap._compute_status(_E(404)) == 404
    assert kap._compute_status(_E(500)) == 502
    assert kap._compute_status(Exception("x")) == 502
    # finance / metrics / strategy en echec -> dict error, jamais d'exception
    monkeypatch.setitem(sys.modules, "kuro_finance", None)
    assert "status" in kap.get_finance() or isinstance(kap.get_finance(), dict)
    assert isinstance(kap.get_metrics(), dict)
    assert isinstance(kap.get_strategy(), dict)
    sys.modules.pop("kuro_finance", None)


def test_answer_question_sans_llm(monkeypatch, _api_db):
    import types
    fake = types.ModuleType("kuro_llm")
    fake.ask = lambda *a, **k: None
    monkeypatch.setitem(sys.modules, "kuro_llm", fake)
    out = kap.answer_question("ca va ?")
    assert out["answer"] is None and "Projets" in out["context"]


def test_http_routes_live(tmp_path, monkeypatch):
    """Serveur reel sur port ephemere : dashboard live + static + 404."""
    db = _db(tmp_path)
    monkeypatch.setattr(kap, "DB_PATH", db)
    # scan live sans toucher ~/Documents : racines vides
    empty = tmp_path / "empty-docs"
    empty.mkdir()
    (tmp_path / "rules").mkdir(exist_ok=True)
    monkeypatch.setattr(sc, "DOCS_DIR", empty)
    monkeypatch.setattr(sc, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(sc, "DASHBOARD_DIR", tmp_path)
    monkeypatch.setattr(sc, "KNOWLEDGE_DIR", tmp_path / "nope-kb")
    monkeypatch.setattr(sc, "PROJECTS_FILE", tmp_path / "nope-proj.txt")
    monkeypatch.setattr(sc, "EXCLUDE_FILE", tmp_path / "nope-excl.txt")
    monkeypatch.setattr(sc, "AGENTS_FILE", tmp_path / "nope-ag.md")
    monkeypatch.setattr(sc, "SYNC_LOG_FILE", tmp_path / "nope-sync.md")
    monkeypatch.setattr(sc, "KURO_DB_FILE", tmp_path / "nope-kuro.db")
    sc._PAYLOAD_CACHE.update({"ts": 0.0, "payload": None})

    server = kap.KuroServer(("127.0.0.1", 0), kap.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        def _get(p):
            # Windows coupe parfois le loopback (WinError 10053, AV/proxy) :
            # un seul retry sur erreur socket transitoire, les asserts restent stricts.
            last = None
            for _ in range(2):
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=10) as r:
                        return r.status, json.loads(r.read().decode("utf-8"))
                except (TimeoutError, ConnectionError) as exc:
                    last = exc
            raise last
        code, dash = _get("/api/dashboard")
        assert code == 200 and "generatedAt" in dash
        code, dash2 = _get("/dashboard-data.json")
        assert code == 200 and "generatedAt" in dash2
        code, status = _get("/api/status")
        assert code == 200 and status["projects"] == 1
        code, syst = _get("/api/system")
        assert code == 200 and "cpu" in syst
        # statique index.html servi depuis le paquet
        import urllib.request as _u
        with _u.urlopen(f"http://127.0.0.1:{port}/", timeout=10) as r:
            body = r.read().decode("utf-8")
            assert "Kuro" in body
        # route inconnue -> 404 json
        try:
            _get("/api/nope")
            raise AssertionError("aurait du 404")
        except urllib.error.HTTPError as exc:
            assert exc.code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_main_sans_db(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kap, "DB_PATH", tmp_path / "nope.db")
    monkeypatch.setattr(sys, "argv", ["kuro-dashboard"])
    assert kap.main() == 1
    # allow-no-db mais port occupe -> 1 (pas de crash)
    server = kap.KuroServer(("127.0.0.1", 0), kap.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setattr(sys, "argv", ["kuro-dashboard", "--port", str(port)])
        assert kap.main() == 1  # port deja occupe
    finally:
        server.shutdown()
        server.server_close()


def _serve(tmp_path, monkeypatch):
    db = _db(tmp_path)
    monkeypatch.setattr(kap, "DB_PATH", db)
    empty = tmp_path / "empty-docs-post"
    empty.mkdir(exist_ok=True)
    monkeypatch.setattr(sc, "DOCS_DIR", empty)
    monkeypatch.setattr(sc, "ROOT_DIR", tmp_path)
    monkeypatch.setattr(sc, "KURO_DB_FILE", tmp_path / "nope-kuro.db")
    sc._PAYLOAD_CACHE.update({"ts": 0.0, "payload": None})
    server = kap.KuroServer(("127.0.0.1", 0), kap.Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, port, db


def _post(port, path, payload=None, headers=None):
    import urllib.error
    data = json.dumps(payload or {}).encode("utf-8") if payload is not None else b""
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data,
                                 method="POST",
                                 headers={"Content-Type": "application/json",
                                          **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8") or "{}")


def test_post_ask_et_erreurs(tmp_path, monkeypatch):
    import types
    fake = types.ModuleType("kuro_llm")
    fake.ask = lambda *a, **k: "reponse courte"
    monkeypatch.setitem(sys.modules, "kuro_llm", fake)
    server, port, _dbp = _serve(tmp_path, monkeypatch)
    try:
        code, out = _post(port, "/api/ask", {"question": "ca va ?"})
        assert code == 200 and out["answer"] == "reponse courte"
        code, _ = _post(port, "/api/ask", {"question": "   "})
        assert code == 400
        code, _ = _post(port, "/api/ask", None)
        assert code in (400, 500)
    finally:
        server.shutdown()
        server.server_close()
        sys.modules.pop("kuro_llm", None)


def test_post_alerts_ack(tmp_path, monkeypatch):
    server, port, _dbp = _serve(tmp_path, monkeypatch)
    try:
        code, out = _post(port, "/api/alerts/1/ack", {})
        assert code == 200 and out["acknowledged"] == 1
        code, _ = _post(port, "/api/alerts/9999/ack", {})
        assert code == 404
        code, _ = _post(port, "/api/alerts/abc/ack", {})
        assert code == 400
        code, out = _post(port, "/api/alerts/ack-all", {"older_than_days": 0})
        assert code == 200 and "acked" in out
        code, _ = _post(port, "/api/nope", {})
        assert code == 404
    finally:
        server.shutdown()
        server.server_close()


def test_post_compute_sans_backend(tmp_path, monkeypatch):
    server, port, _dbp = _serve(tmp_path, monkeypatch)
    try:
        code, out = _post(port, "/api/compute/request",
                           {"project": "Demo", "rtype": "gpu"})
        # sans backend Helium : 502, jamais 500/crash, message present
        assert code in (201, 502) and ("error" in out or "project" in str(out))
    finally:
        server.shutdown()
        server.server_close()


def test_auth_et_no_db(tmp_path, monkeypatch):
    import urllib.error
    server, port, _dbp = _serve(tmp_path, monkeypatch)
    monkeypatch.setenv("KURO_API_TOKEN", "secret")
    try:
        # sans token -> 401
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=10)
            raise AssertionError("aurait du 401")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
        # avec token -> 200
        req = urllib.request.Request(f"http://127.0.0.1:{port}/api/status",
                                     headers={"Authorization": "Bearer secret"})
        with urllib.request.urlopen(req, timeout=10) as r:
            assert r.status == 200
    finally:
        monkeypatch.delenv("KURO_API_TOKEN", raising=False)
        server.shutdown()
        server.server_close()


def test_get_seo_absent(monkeypatch, tmp_path):
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path))
    assert kap.get_seo()["status"] == "missing"


def test_get_seo_present(monkeypatch, tmp_path):
    leads = tmp_path / "leads"
    leads.mkdir()
    (leads / "SEO_AUDIT.md").write_text(
        "Date : 2026-10-07\n\n### P0\n1 Fix title\n2 Fix meta\n\n### P1\n1 Add sitemap\n",
        encoding="utf-8")
    monkeypatch.setattr("os.path.expanduser", lambda p: str(tmp_path))
    seo = kap.get_seo()
    assert seo["status"] == "ok"
    assert seo["p0_count"] == 2 and seo["p1_count"] == 1
    assert seo["p0_top"][0] == "Fix title"
