#!/usr/bin/env python3
"""kuro_api.py — API REST locale de l'intelligence Kuro (zéro dépendance).

Interroge ~/.kuro/kuro.db en lecture seule. Bind 127.0.0.1 uniquement.
Auth optionnelle : $KURO_API_TOKEN (Authorization: Bearer <token>).

Endpoints :
    GET  /api/status                 état général (counts, heartbeat, moteur LLM)
    GET  /api/projects               liste des projets
    GET  /api/projects/{name}        détail + dernières sessions
    GET  /api/alerts[?unack=1]       alertes du daemon
    GET  /api/sessions?limit=20      sessions récentes
    GET  /api/memory                 nœuds de mémoire
    GET  /api/summary                digest textuel (humain ou prompt LLM)
    POST /api/ask  {"question":".."} question libre -> cerveau Kuro

Usage:
    python scripts/kuro_api.py [--port 8767]
"""

import argparse
import json
import os
import sqlite3
import sys
import urllib.parse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path.home() / ".kuro" / "kuro.db"
DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"
STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
                "/styles.css": "styles.css", "/dashboard-data.json": "dashboard-data.json"}
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(DASHBOARD_DIR))


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_status() -> dict:
    conn = db()
    hb = rows(conn, "SELECT * FROM heartbeat ORDER BY timestamp DESC LIMIT 1")
    out = {
        "projects": rows(conn, "SELECT COUNT(*) AS n FROM projects")[0]["n"],
        "sessions": rows(conn, "SELECT COUNT(*) AS n FROM sessions")[0]["n"],
        "alerts_open": rows(conn, "SELECT COUNT(*) AS n FROM alerts WHERE acknowledged = 0")[0]["n"],
        "memory_nodes": rows(conn, "SELECT COUNT(*) AS n FROM memory_nodes")[0]["n"],
        "heartbeat": hb[0] if hb else None,
        "llm_engine": None,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    try:
        from kuro_llm import available

        out["llm_engine"] = available()
    except Exception:
        pass
    return out


def get_projects() -> list[dict]:
    conn = db()
    return rows(
        conn,
        """SELECT id, name, section, status, progress_pct, last_activity
           FROM projects ORDER BY progress_pct DESC""",
    )


def get_project(name: str) -> dict | None:
    conn = db()
    proj = rows(
        conn,
        """SELECT id, name, path, section, status, progress_pct, last_activity, created_at
           FROM projects WHERE lower(name) = lower(?)""",
        (name,),
    )
    if not proj:
        return None
    p = proj[0]
    p["sessions"] = rows(
        conn,
        """SELECT session_date, editor, progress_before, progress_after,
                  tests_status, blockers, next_steps
           FROM sessions WHERE project_id = ? ORDER BY session_date DESC LIMIT 10""",
        (p["id"],),
    )
    p["alerts"] = rows(
        conn,
        """SELECT alert_type, message, severity, acknowledged, created_at
           FROM alerts WHERE project_id = ? ORDER BY created_at DESC LIMIT 10""",
        (p["id"],),
    )
    del p["id"]
    return p


def get_alerts(unack_only: bool = False) -> list[dict]:
    conn = db()
    where = "WHERE a.acknowledged = 0" if unack_only else ""
    return rows(
        conn,
        f"""SELECT a.id, p.name AS project, a.alert_type, a.message, a.severity,
                   a.acknowledged, a.created_at
            FROM alerts a LEFT JOIN projects p ON p.id = a.project_id
            {where} ORDER BY a.created_at DESC LIMIT 100""",
    )


def get_sessions(limit: int = 20) -> list[dict]:
    conn = db()
    return rows(
        conn,
        f"""SELECT p.name AS project, s.session_date, s.editor,
                   s.progress_before, s.progress_after, s.tests_status, s.blockers
            FROM sessions s LEFT JOIN projects p ON p.id = s.project_id
            ORDER BY s.session_date DESC LIMIT {int(limit)}""",
    )


def get_memory() -> list[dict]:
    conn = db()
    return rows(
        conn,
        """SELECT n.node_type, n.title, substr(n.summary, 1, 200) AS summary,
                  n.level, p.name AS project, n.created_at
           FROM memory_nodes n LEFT JOIN projects p ON p.id = n.project_id
           ORDER BY n.created_at DESC LIMIT 100""",
    )


def build_summary() -> str:
    st = get_status()
    conn = db()
    stale = rows(
        conn,
        """SELECT name, status, progress_pct, last_activity FROM projects
           WHERE last_activity < datetime('now', '-14 days')
           ORDER BY last_activity ASC LIMIT 8""",
    )
    top_alerts = rows(
        conn,
        """SELECT message, severity FROM alerts
           WHERE acknowledged = 0 ORDER BY created_at DESC LIMIT 5""",
    )
    lines = [
        f"Projets: {st['projects']} · Sessions: {st['sessions']} · "
        f"Alertes ouvertes: {st['alerts_open']} · Nœuds mémoire: {st['memory_nodes']}",
        "",
        "Stagnation >14j:",
    ]
    lines += [
        f"- {r['name']} ({r['progress_pct']}%, {r['status']}, dernier: {str(r['last_activity'])[:10]})"
        for r in stale
    ] or ["- aucun"]
    lines += ["", "Alertes ouvertes:"]
    lines += [f"- [{r['severity']}] {r['message'][:120]}" for r in top_alerts] or ["- aucune"]
    return "\n".join(lines)


def answer_question(question: str) -> dict:
    from kuro_llm import ask

    context = build_summary()
    answer = ask(
        f"Contexte de l'entreprise lambda-Section:\n{context}\n\nQuestion: {question}",
        system="Tu es le chef de projet IA de lambda-Section. Réponds court et factuel, en français.",
    )
    if answer is None:
        return {"answer": None, "engine": None, "context": context}
    return {"answer": answer, "engine": "auto", "context": context}


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload) -> None:
        body = json.dumps(payload, indent=2, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _auth_ok(self) -> bool:
        token = os.environ.get("KURO_API_TOKEN")
        if not token:
            return True
        header = self.headers.get("Authorization", "")
        return header == f"Bearer {token}"

    def do_GET(self) -> None:  # noqa: N802
        if not self._auth_ok():
            self._json(401, {"error": "unauthorized"})
            return
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        path = parsed.path.rstrip("/") or "/"
        try:
            if path == "/api/dashboard":
                import generate_dashboard

                self._json(200, generate_dashboard.build_payload())
            elif path == "/api/status":
                self._json(200, get_status())
            elif path == "/api/projects":
                self._json(200, {"projects": get_projects()})
            elif path.startswith("/api/projects/"):
                name = urllib.parse.unquote(path.rsplit("/", 1)[1])
                proj = get_project(name)
                self._json(404, {"error": "projet inconnu"}) if proj is None else self._json(200, proj)
            elif path == "/api/alerts":
                self._json(200, {"alerts": get_alerts(unack_only=qs.get("unack") == ["1"])})
            elif path == "/api/sessions":
                limit = int(qs.get("limit", ["20"])[0])
                self._json(200, {"sessions": get_sessions(limit)})
            elif path == "/api/memory":
                self._json(200, {"memory": get_memory()})
            elif path == "/api/summary":
                self._json(200, {"summary": build_summary()})
            elif path in STATIC_FILES:
                file_path = DASHBOARD_DIR / STATIC_FILES[path]
                if not file_path.exists():
                    self._json(404, {"error": "fichier introuvable"})
                    return
                ctype = "text/html" if file_path.suffix == ".html" else (
                    "application/javascript" if file_path.suffix == ".js" else (
                        "text/css" if file_path.suffix == ".css" else "application/json"
                    )
                )
                body = file_path.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", f"{ctype}; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                self._json(404, {"error": "route inconnue"})
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def do_POST(self) -> None:  # noqa: N802
        if not self._auth_ok():
            self._json(401, {"error": "unauthorized"})
            return
        if self.path.rstrip("/") != "/api/ask":
            self._json(404, {"error": "route inconnue (POST /api/ask seulement)"})
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            question = (data.get("question") or "").strip()
            if not question:
                self._json(400, {"error": "question vide"})
                return
            self._json(200, answer_question(question))
        except Exception as exc:
            self._json(500, {"error": str(exc)})

    def log_message(self, fmt, *args):  # silence les logs d'accès
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="API REST Kuro")
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()

    if not DB_PATH.exists():
        print(f"kuro.db introuvable: {DB_PATH}")
        return 1

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Kuro API sur http://127.0.0.1:{args.port} (db: {DB_PATH})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
