#!/usr/bin/env python3
"""kuro_dashboard.api — API REST locale de l'intelligence Kuro (zero dependance).

Interroge ~/.kuro/kuro.db en lecture seule. Bind 127.0.0.1 uniquement.
Auth optionnelle : $KURO_API_TOKEN (Authorization: Bearer <token>).

Endpoints :
    GET  /api/status                 etat general (counts, heartbeat, moteur LLM)
    GET  /api/system                 snapshot systeme live (CPU/RAM/disques/reseau/GPU/Docker/process)
    GET  /api/projects               liste des projets
    GET  /api/projects/{name}        detail + dernieres sessions
    GET  /api/alerts[?unack=1]       alertes du daemon
    GET  /api/sessions?limit=20      sessions recentes
    GET  /api/memory                 noeuds de memoire
    GET  /api/summary                digest textuel (humain ou prompt LLM)
    GET  /api/finance                burn rate, runway, MRR (R111: 100% local)
    GET  /api/metrics                lead time, velocite, echecs CI, pivots
    GET  /api/strategy               digest strategique (runway, OKR, decisions)
    GET  /api/seo                    audit SEO du cron (~/leads/SEO_AUDIT.md)
    POST /api/ask  {"question":".."} question libre -> cerveau Kuro
    GET  /api/compute/offers         offres Helium (GPU/RAM)
    POST /api/compute/request        demande compute {project, rtype, amount...} -> 201
    GET  /api/compute/requests/{id}  demande + matches courants

Usage:
    kuro-dashboard [--port 8767]
    python -m kuro_dashboard [--port 8767]
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

from .scan import build_payload as scan_build_payload
from .system import get_cached_snapshot

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DB_PATH = Path.home() / ".kuro" / "kuro.db"


def _rules_dir() -> Path:
    """Racine kuro-rules pour les fichiers repo (journal, ci-status)."""
    env = os.environ.get("KURO_RULES_DIR")
    if env:
        return Path(env)
    return Path.home() / "Documents" / "kuro-rules"


def _static_dir() -> Path:
    """Dossier UI : env KURO_STATIC_DIR, sinon ressources du paquet."""
    env = os.environ.get("KURO_STATIC_DIR")
    if env:
        return Path(env)
    try:
        from importlib.resources import files as _res_files

        candidate = Path(str(_res_files("kuro_dashboard") / "static"))
        if (candidate / "index.html").exists():
            return candidate
    except Exception:
        pass
    return Path(__file__).resolve().parent / "static"


STATIC_FILES = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
                "/styles.css": "styles.css"}
# /dashboard-data.json et /api/dashboard servent le payload LIVE (scan 60 s
# cache) : le snapshot statique dashboard/dashboard-data.json n'est qu'un
# repli hors-ligne (gitigne, vite stale). Ne jamais le servir via l'API.


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def rows(conn, sql, params=()):
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def _count(conn: sqlite3.Connection, sql: str) -> int:
    """COUNT tolerant : table absente (fresh install) -> 0, jamais d exception."""
    try:
        return rows(conn, sql)[0]["n"]
    except (sqlite3.Error, IndexError, KeyError):
        return 0


def get_status() -> dict:
    conn = db()
    try:
        try:
            hb = rows(conn, "SELECT * FROM heartbeat ORDER BY timestamp DESC LIMIT 1")
        except sqlite3.Error:
            hb = []
        out = {
            "api_version": "1.1",
            "projects": _count(conn, "SELECT COUNT(*) AS n FROM projects"),
            "sessions": _count(conn, "SELECT COUNT(*) AS n FROM sessions"),
            "alerts_open": _count(conn, "SELECT COUNT(*) AS n FROM alerts WHERE acknowledged = 0"),
            "memory_nodes": _count(conn, "SELECT COUNT(*) AS n FROM memory_nodes"),
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
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_projects() -> list[dict]:
    conn = db()
    try:
        return rows(
            conn,
            """SELECT id, name, section, status, progress_pct, last_activity
               FROM projects ORDER BY progress_pct DESC""",
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_project(name: str) -> dict | None:
    conn = db()
    try:
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
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_alerts(unack_only: bool = False) -> list[dict]:
    conn = db()
    try:
        where = "WHERE a.acknowledged = 0" if unack_only else ""
        return rows(
            conn,
            f"""SELECT a.id, p.name AS project, a.alert_type, a.message, a.severity,
                       a.acknowledged, a.created_at
                FROM alerts a LEFT JOIN projects p ON p.id = a.project_id
                {where} ORDER BY a.created_at DESC LIMIT 100""",  # nosec B608 - where = littéral fixe, jamais d'entrée user
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_sessions(limit: int = 20) -> list[dict]:
    conn = db()
    try:
        return rows(
            conn,
            f"""SELECT p.name AS project, s.session_date, s.editor,
                       s.progress_before, s.progress_after, s.tests_status, s.blockers
                FROM sessions s LEFT JOIN projects p ON p.id = s.project_id
                ORDER BY s.session_date DESC LIMIT {int(limit)}""",  # nosec B608 - limit casté int(), jamais d'entrée brute
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_memory() -> list[dict]:
    conn = db()
    try:
        return rows(
            conn,
            """SELECT n.node_type, n.title, substr(n.summary, 1, 200) AS summary,
                      n.level, p.name AS project, n.created_at
               FROM memory_nodes n LEFT JOIN projects p ON p.id = n.project_id
               ORDER BY n.created_at DESC LIMIT 100""",
        )
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_robot() -> dict:
    """Etat du robot Kuro : journal recent + sante CI + moteur."""
    root = _rules_dir()
    journal = root / "KURO_ACTIONS_LOG.md"
    actions = []
    if journal.exists():
        for line in journal.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("- ") or line.startswith("  - "):
                actions.append(line.strip())
        actions = actions[-20:]
    # source fraiche en priorite : copie commitee dans kuro-rules par le robot
    ci_status = None
    for candidate in (root / "ci-status.json",
                       Path.home() / "Documents" / "Lemniscate-world" / "ci-status.json"):
        try:
            ci_status = json.loads(candidate.read_text(encoding="utf-8"))
            break
        except Exception:
            continue
    st = get_status()
    repos = []
    if isinstance(ci_status, dict):
        for r in ci_status.get("repos", []):
            if r.get("health") == "no_ci":
                continue
            fails = []
            for w in r.get("workflows", []):
                if w.get("conclusion") == "failure":
                    fails.append({"name": w["name"], "url": w.get("url", "")})
            repos.append(
                {
                    "name": r.get("name"),
                    "health": r.get("health"),
                    "checks_ok": len(r.get("workflows", [])) - len(fails),
                    "checks_total": len(r.get("workflows", [])),
                    "failing": fails,
                }
            )
    return {
        "actions_tail": actions,
        "repos": repos,
        "ci_overall": (ci_status or {}).get("overall"),
        "llm_engine": st.get("llm_engine"),
        "alerts_open": st.get("alerts_open"),
        "daemon": st.get("heartbeat"),
    }


def get_finance() -> dict:
    """Finances locales (R111) : fichier gitigne, zero reseau, zero LLM."""
    try:
        import kuro_finance

        return kuro_finance.compute_from_default()
    except Exception as exc:
        return {"status": "unconfigured", "error": str(exc)}


def get_metrics() -> dict:
    try:
        import kuro_metrics

        return kuro_metrics.build_payload()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def get_strategy() -> dict:
    """Digest strategique : finance + execution + OKR + pipeline + decisions."""
    try:
        import kuro_strategy

        return kuro_strategy.build_payload()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _seo_items(text: str, header: str) -> list:
    """Items numérotés sous un header ### (même parsing que Xenon)."""
    out, inside = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("### "):
            inside = stripped == header
            continue
        if inside and stripped and stripped[0].isdigit():
            parts = stripped.split(None, 1)
            out.append(parts[1][:110] if len(parts) > 1 else stripped[:110])
    return out


def _seo_age(path: str) -> str:
    """Âge du fichier d'audit ('' si illisible)."""
    try:
        age_s = _dt_now().timestamp() - os.path.getmtime(path)
    except OSError:
        return ""
    if age_s >= 86400:
        return f"il y a {int(age_s // 86400)}j"
    if age_s >= 3600:
        return f"il y a {int(age_s // 3600)}h"
    return f"il y a {int(age_s // 60)} min"


def get_seo() -> dict:
    """Audit SEO du cron strategy-daily (~/leads/SEO_AUDIT.md).

    Meme parsing que Xenon (tui.sec_seo) : date, comptes P0/P1, top actions.
    Absent (PC sans leads) -> statut explicite, jamais de chiffres inventes.
    """
    try:
        path = os.path.join(os.path.expanduser("~"), "leads", "SEO_AUDIT.md")
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError:
            return {"status": "missing",
                    "detail": "cron strategy-daily : ~/leads/SEO_AUDIT.md absent"}
        date = ""
        for line in text.splitlines()[:12]:
            if line.startswith("Date"):
                date = line[5:].strip()[:40]
                break
        p0 = _seo_items(text, "### P0")
        p1 = _seo_items(text, "### P1")
        return {"status": "ok", "date": date or "?", "age": _seo_age(path),
                "p0_count": len(p0), "p1_count": len(p1), "p0_top": p0[:3]}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def _dt_now():
    """now() centralisé (testable)."""
    return datetime.now().astimezone()


def get_system() -> dict:
    """Snapshot systeme live (Glances Kuro). Ne touche jamais la DB."""
    try:
        return get_cached_snapshot()
    except Exception as exc:
        return {"status": "error", "error": str(exc)}


def build_summary() -> str:
    st = get_status()
    conn = db()
    try:
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
    finally:
        try:
            conn.close()
        except Exception:
            pass
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


def _compute_status(exc: Exception) -> int:
    """Statut HTTP pour un echec compute : 4xx Helium en passthrough, 502 sinon."""
    status = getattr(exc, "status", None)
    if isinstance(status, int) and status in (400, 401, 404, 409, 429):
        return status
    return 502


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
            _db_optional = ("/api/system", "/api/dashboard", "/dashboard-data.json",
                              "/api/seo")
            if path.startswith("/api/") and path not in _db_optional and not DB_PATH.exists():
                self._json(503, {"error": "no-db",
                                 "detail": "kuro.db absente : seuls /api/system et "
                                           "/api/dashboard repondent "
                                           "(relancer avec une base ou monter ~/.kuro)"})
                return
            if path in ("/api/dashboard", "/dashboard-data.json"):
                # Payload live (cache 60 s cote scan) : jamais le fichier
                # statique gitigne. Ne requiert pas la DB (git + fichiers).
                self._json(200, scan_build_payload())
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
            elif path == "/api/system":
                self._json(200, get_system())
            elif path == "/api/robot":
                self._json(200, get_robot())
            elif path == "/api/finance":
                self._json(200, get_finance())
            elif path == "/api/metrics":
                self._json(200, get_metrics())
            elif path == "/api/strategy":
                self._json(200, get_strategy())
            elif path == "/api/seo":
                self._json(200, get_seo())
            elif path == "/api/compute/offers":
                try:
                    from kuro_compute import list_offers
                    self._json(200, {"offers": list_offers()})
                except Exception as exc:
                    self._json(_compute_status(exc), {"error": str(exc)})
            elif path.startswith("/api/compute/requests/"):
                rid = urllib.parse.unquote(path.rsplit("/", 1)[1])
                try:
                    from kuro_compute import get_request_status
                    self._json(200, get_request_status(rid))
                except Exception as exc:
                    self._json(_compute_status(exc), {"error": str(exc)})
            elif path in STATIC_FILES:
                file_path = _static_dir() / STATIC_FILES[path]
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
        path = self.path.rstrip("/")
        if path == "/api/compute/request":
            try:
                length = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
            except Exception:
                self._json(400, {"error": "JSON invalide"})
                return
            try:
                from kuro_compute import create_request
                created = create_request(
                    project=data.get("project", ""),
                    rtype=data.get("rtype", "gpu"),
                    amount=data.get("amount", 16),
                    max_price=data.get("max_price", 1.0),
                    hours=data.get("hours", 2),
                    image=data.get("image", ""),
                    gpus=data.get("gpus", 0),
                    template=data.get("template", ""),
                    min_bench=data.get("min_bench", 0.0),
                )
                self._json(201, created)
            except Exception as exc:
                self._json(_compute_status(exc), {"error": str(exc)})
            return
        if path == "/api/ask":
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
            return
        if path.startswith("/api/alerts/") and path.endswith("/ack"):
            # "/api/alerts/1/ack" -> ['', 'api', 'alerts', '1', 'ack'] (len 5)
            parts = path.split("/")
            if len(parts) != 5 or not parts[3].isdigit():
                self._json(400, {"error": "attendu: POST /api/alerts/{id}/ack"})
                return
            alert_id = int(parts[3])
            conn = None
            try:
                conn = sqlite3.connect(DB_PATH, timeout=5)
                with conn:
                    cur = conn.execute(
                        "UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,)
                    )
                    updated = cur.rowcount
                if updated:
                    self._json(200, {"acknowledged": alert_id})
                else:
                    self._json(404, {"error": f"alerte {alert_id} inconnue"})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            finally:
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass
            return
        if path == "/api/alerts/ack-all":
            conn = None
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
                days = int(body.get("older_than_days", 0) or 0)
                conn = sqlite3.connect(DB_PATH, timeout=5)
                with conn:
                    if days > 0:
                        cur = conn.execute(
                            "UPDATE alerts SET acknowledged = 1 WHERE acknowledged = 0 "
                            "AND created_at < datetime('now', ?)",
                            (f"-{days} days",),
                        )
                    else:
                        cur = conn.execute(
                            "UPDATE alerts SET acknowledged = 1 WHERE acknowledged = 0"
                        )
                    acked = cur.rowcount
                self._json(200, {"acked": acked})
            except Exception as exc:
                self._json(500, {"error": str(exc)})
            finally:
                try:
                    if conn is not None:
                        conn.close()
                except Exception:
                    pass
            return
        self._json(404, {"error": "route inconnue (POST /api/ask, /api/compute/request ou /api/alerts/{id}/ack)"})

    def log_message(self, fmt, *args):  # silence les logs d'acces
        pass


class KuroServer(ThreadingHTTPServer):
    # Refuse le double-bind : sur Windows SO_REUSEADDR autorise deux listeners
    # silencieux sur le meme port -> reponses aleatoires selon l instance.
    allow_reuse_address = False


def main() -> int:
    parser = argparse.ArgumentParser(description="API REST Kuro + dashboard")
    parser.add_argument("--port", type=int, default=8767)
    parser.add_argument("--host", default="127.0.0.1",
                        help="interface d ecoute (0.0.0.0 en Docker uniquement)")
    parser.add_argument("--allow-no-db", action="store_true",
                        help="demarre sans kuro.db (demo/Docker : seul /api/system repond)")
    args = parser.parse_args()

    if not DB_PATH.exists() and not args.allow_no_db:
        print(f"kuro.db introuvable: {DB_PATH}")
        return 1
    if not DB_PATH.exists():
        print(f"kuro.db absente ({DB_PATH}) : mode demo, seul /api/system repond.")

    try:
        server = KuroServer((args.host, args.port), Handler)
    except OSError as exc:
        print(f"port {args.port} deja occupe (instance Kuro API deja active ?): {exc}")
        return 1

    print(f"Kuro API sur http://{args.host}:{args.port} (db: {DB_PATH})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
