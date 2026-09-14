#!/usr/bin/env python3
"""kuro_anydo.py — bridge Kuro <-> Any.do MCP (https://mcp.any.do/sse).

Any.do MCP sait faire (doc officielle) : taches perso (create/update/archive/delete),
reminders uniques/recurrents, boards workspace, events calendrier, listes courses.
Endpoint protege par OAuth2, setup desktop : Claude Settings > Connectors > Add custom
connector avec https://mcp.any.do/sse, ou ChatGPT Settings > Plugins > + MCP server.

Deux sens :
  --export : Kuro -> fichier (pipeline next_steps + decisions strategie -> tasks_anydo.json).
  --pull   : Any.do -> Kuro (lit taches/listes via MCP SSE, rattache chaque note au
             projet Epingle le plus proche, propose actions + signale les orphelines).
  --push   : experimental, exige ANYDO_TOKEN (bearer OAuth). Sans token : guide, jamais fatal.

Usage:
  python scripts/kuro_anydo.py --export [--out tasks_anydo.json]
  ANYDO_TOKEN=xxx python scripts/kuro_anydo.py --pull [--out-pull pull_anydo.json]
"""
import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
PIPELINE = ROOT / "pipeline.local.json"
STRATEGY = ROOT / "strategy.local.json"
MCP_URL = "https://mcp.any.do/sse"


def load_json(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _pipeline_tasks() -> list[dict]:
    tasks = []
    pipe = load_json(PIPELINE)
    for e in (pipe.get("entries", []) or [])[-10:]:
        if not isinstance(e, dict):
            continue
        ns = (e.get("next_step") or "").strip()
        if ns:
            tasks.append({"title": ns[:120], "source": "pipeline.next_step",
                          "date": e.get("date", ""), "due": ""})
    return tasks


def _strategy_tasks() -> list[dict]:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import kuro_strategy
        payload = kuro_strategy.build_payload()
    except Exception:
        return []
    out = []
    for d in payload.get("decisions", [])[:8]:
        if isinstance(d, dict):
            mark = "NEW" if d.get("status") == "NEW" else f"J{d.get('age_days', 0)}"
            out.append({"title": d.get("text", "")[:120], "source": "strategy.decision",
                        "date": "", "due": "", "status": d.get("status"),
                        "age_days": d.get("age_days", 0), "tag": mark})
        else:
            out.append({"title": d[:120], "source": "strategy.decision", "date": "", "due": ""})
    return out


def collect_tasks() -> list[dict]:
    seen, out = set(), []
    for t in _pipeline_tasks() + _strategy_tasks():
        if t["title"] not in seen:
            seen.add(t["title"])
            out.append(t)
    return out


def _confined_out(p: Path, default_name: str) -> Path:
    """Confine les sorties JSON sous ROOT (iliaques CLI --out malveillants refuses)."""
    try:
        resolved = Path(p).expanduser().resolve()
        if resolved.parent == ROOT.resolve():
            return resolved
    except Exception:
        pass
    return ROOT / default_name


def cmd_export(out: Path):
    tasks = collect_tasks()
    out = _confined_out(out, "tasks_anydo.json")
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mcp_endpoint": MCP_URL,
        "usage": "Connecter Claude (Settings > Connectors > https://mcp.any.do/sse) puis coller les titres, ex: '@Any.do ajoute [titre] avec rappel lundi 10h'",
        "tasks": tasks,
    }
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Export {len(tasks)} taches -> {out}")
    for t in tasks[:10]:
        print(f" - [{t['source']}] {t['title']}")


STOPWORDS = {
    "les", "des", "une", "pour", "avec", "dans", "sur", "est", "the", "and",
    "for", "with", "that", "this", "from", "into", "your", "aux",
    "faire", "plus", "tout", "tous", "comme", "par", "pas", "sont",
}

_SSE_DATA = "data:"
_MCP_HOST = "mcp.any.do"


def _tok(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", text.lower())) - STOPWORDS


def _allow_endpoint(raw: str) -> str | None:
    """N'accepte que https://mcp.any.do (le flux SSE distant pilote l'URL)."""
    target = urllib.parse.urlparse(urllib.parse.urljoin(MCP_URL, raw.strip()))
    if target.scheme == "https" and target.hostname == _MCP_HOST:
        return target.geturl()
    print(f"MCP endpoint refuse (hote inattendu) : {target.hostname or '?'}")
    return None


def mcp_sse_endpoint(token: str, timeout: int = 20) -> str | None:
    """GET /sse, lit le premier evenement 'endpoint' -> URL POST JSON-RPC."""
    req = urllib.request.Request(
        MCP_URL,
        headers={"Authorization": f"Bearer {token}", "Accept": "text/event-stream",
                 "User-Agent": "Kuro/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            event = None
            for i, raw in enumerate(resp):
                if i > 200:
                    break
                line = raw.decode("utf-8", errors="replace").strip()
                if line.startswith("event:"):
                    event = line[6:].strip()
                elif line.startswith(_SSE_DATA) and event == "endpoint":
                    return _allow_endpoint(line[len(_SSE_DATA):])
                elif line.startswith(_SSE_DATA) and event is None and line[len(_SSE_DATA):].strip().startswith("/"):
                    return _allow_endpoint(line[len(_SSE_DATA):])
    except Exception as e:
        print(f"MCP SSE inaccessible : {e}")
    return None


def mcp_rpc(url: str, token: str, method: str, params: dict | None = None,
            rid: int = 1, notify: bool = False) -> dict | None:
    """POST JSON-RPC, accepte reponse JSON ou flux SSE. notify=True : sans id, reponse ignoree."""
    body: dict = {"jsonrpc": "2.0", "method": method}
    if not notify:
        body["id"] = rid
    if params is not None:
        body["params"] = params
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json",
                 "Accept": "application/json, text/event-stream", "User-Agent": "Kuro/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"MCP {method} echec : {e}")
        return None
    if notify:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        pass
    for line in raw.splitlines():  # reponse SSE : cherche data: {json}
        line = line.strip()
        if line.startswith(_SSE_DATA):
            try:
                obj = json.loads(line[len(_SSE_DATA):].strip())
                if isinstance(obj, dict) and ("result" in obj or "error" in obj):
                    return obj
            except Exception:
                continue
    return None


def _mcp_tools(url: str, token: str) -> list[dict]:
    """Handshake MCP (initialize + notifications/initialized) puis tools/list."""
    init = mcp_rpc(url, token, "initialize", {"protocolVersion": "2024-11-05",
                  "capabilities": {}, "clientInfo": {"name": "Kuro", "version": "1.0"}}, rid=1)
    if not init or "error" in init:
        print(f"MCP initialize refuse : {(init or {}).get('error', 'sans reponse')}")
        return []
    mcp_rpc(url, token, "notifications/initialized", notify=True)
    tools_resp = mcp_rpc(url, token, "tools/list", {}, rid=2) or {}
    return ((tools_resp.get("result") or {}).get("tools")) or []


def _mcp_read_tasks(url: str, token: str, tools: list[dict]) -> list[dict]:
    """Appelle le premier outil de lecture de taches plausible."""
    tasks: list[dict] = []
    for t in tools:
        name = (t.get("name") or "").lower()
        if "task" in name and any(k in name for k in ("list", "get", "all", "search", "query")):
            r = mcp_rpc(url, token, "tools/call", {"name": t.get("name"), "arguments": {}}, rid=3) or {}
            for c in ((r.get("result") or {}).get("content")) or []:
                txt = c.get("text", "") if isinstance(c, dict) else ""
                tasks.extend(_parse_task_items(txt))
            break
    return tasks


def _parse_task_items(txt: str) -> list[dict]:
    try:
        val = json.loads(txt)
    except Exception:
        return [{"title": txt.strip()[:200]}] if txt.strip() else []
    items = val if isinstance(val, list) else val.get("tasks", val.get("items", []))
    if not isinstance(items, list):
        return []
    return [it for it in items if isinstance(it, dict)]


def mcp_fetch_tasks(token: str) -> tuple[list[dict], list[dict]]:
    """Handshake MCP + tools/list + appel du premier outil de lecture plausible."""
    url = mcp_sse_endpoint(token)
    if not url:
        return [], []
    tools = _mcp_tools(url, token)
    print(f"MCP : {len(tools)} outil(s) exposes")
    for t in tools:
        print(f" - {t.get('name')} : {(t.get('description') or '')[:90]}")
    return _mcp_read_tasks(url, token, tools), tools


def _mcp_create_tool(tools: list[dict]) -> str | None:
    for t in tools:
        name = (t.get("name") or "").lower()
        if "task" in name and any(k in name for k in ("create", "add", "new")):
            return t.get("name")
    return None


def _load_projects() -> list[dict] | None:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from generate_portfolio import parse_epingle
        secs = parse_epingle(ROOT / "Epingle_Projets.md")
    except Exception:
        return None
    return [{"name": p["name"], "status": p["status"], "pct": p["pct"],
             "toks": _tok(f"{p['name']} {p['desc']}")}
            for s in secs for p in s["projects"]
            if not p["status"].lower().startswith("archive")]


def _score_task(ctx: str, sig: set[str], projects: list[dict]) -> dict | None:
    scored = []
    lowered = ctx.lower()
    for pr in projects:
        overlap = sig & pr["toks"]
        if pr["name"].lower() in lowered:
            scored.append((10, pr))
        elif len(overlap) >= 2:
            scored.append((len(overlap), pr))
    if not scored:
        return None
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def match_projects(tasks: list[dict]) -> dict:
    """Rattache chaque note Any.do au(x) projet(s) Epingle + propositions."""
    projects = _load_projects()
    if projects is None:
        return {"error": "Epingle illisible (parse_epingle indisponible)"}
    attached, orphans = [], []
    hit_count: dict[str, int] = {}
    for t in tasks:
        title = str(t.get("title") or t.get("name") or "")
        ctx = f"{t.get('list') or t.get('board') or ''} {title}"
        best = _score_task(ctx, _tok(ctx), projects)
        if best:
            hit_count[best["name"]] = hit_count.get(best["name"], 0) + 1
            attached.append({"task": title[:120], "list": str(t.get("list") or t.get("board") or ""),
                             "project": best["name"], "status": best["status"],
                             "proposal": f"Suivre dans {best['name']} ({best['status']}) — "
                                         f"ajouter au pipeline si insight actionnable."})
        else:
            orphans.append({"task": title[:120], "list": str(t.get("list") or t.get("board") or ""),
                            "proposal": "Orpheline : classer (Mom Test ? idee produit ?) ou archiver."})
    uncovered = [p["name"] for p in projects
                 if p["name"] not in hit_count and "actif" in p["status"].lower()][:10]
    return {"attached": attached, "orphans": orphans,
            "uncovered_active": uncovered, "tasks_seen": len(tasks)}


def cmd_pull(out: Path):
    import os
    token = os.environ.get("ANYDO_TOKEN", "")
    if not token:
        print("ANYDO_TOKEN absent — lecture impossible.")
        print(f"1. Connecte Claude : Settings > Connectors > Add custom > {MCP_URL}")
        print("2. Obtiens un bearer OAuth Any.do, puis : ANYDO_TOKEN=xxx python scripts/kuro_anydo.py --pull")
        print("3. Sans connexion : --export reste utilisable (sens Kuro -> Any.do).")
        return 0
    tasks, tools = mcp_fetch_tasks(token)
    if not tasks:
        print("Aucune tache lue (outil de lecture non trouve ou liste vide).")
        print("Outils decouverts ci-dessus — adapte le filtre dans mcp_fetch_tasks().")
        return 1
    report = match_projects(tasks)
    if report.get("error"):
        print(report["error"])
        return 1
    out = _confined_out(out, "pull_anydo.json")
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    report["tools"] = [t.get("name") for t in tools]
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Lues : {report['tasks_seen']} tache(s) -> {out}")
    print(f"Rattachees : {len(report['attached'])} · Orphelines : {len(report['orphans'])}")
    for a in report["attached"][:10]:
        print(f" - [{a['project']}] {a['task']}")
    for o in report["orphans"][:10]:
        print(f" - [?] {o['task']} -> {o['proposal']}")
    if report["uncovered_active"]:
        print("Actifs sans note : " + ", ".join(report["uncovered_active"]))
    return 0


def cmd_push(dry_run: bool):
    import os
    token = os.environ.get("ANYDO_TOKEN", "")
    tasks = collect_tasks()
    if not token:
        print("ANYDO_TOKEN absent.")
        print(f"1. Connecte le connecteur MCP dans Claude/ChatGPT : {MCP_URL}")
        print("2. Ou obtiens un bearer OAuth puis relance avec ANYDO_TOKEN=xxx --push")
        print(f"3. En attendant, utilise --export ({len(tasks)} taches pretes).")
        return 0
    if dry_run:
        print(f"Dry-run : {len(tasks)} taches seraient poussees vers Any.do MCP.")
        return 0
    url = mcp_sse_endpoint(token)
    if not url:
        return 1
    tool = _mcp_create_tool(_mcp_tools(url, token))
    if not tool:
        print("Aucun outil de creation de tache expose — push impossible.")
        return 1
    ok, rid = 0, 10
    for t in tasks[:20]:
        rid += 1
        r = mcp_rpc(url, token, "tools/call",
                    {"name": tool, "arguments": {"title": t["title"]}}, rid=rid) or {}
        if "error" in r:
            print(f"Echec push '{t['title'][:40]}' : {r['error']}")
            break
        ok += 1
    print(f"Poussees : {ok}/{len(tasks)}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(description="Bridge Kuro <-> Any.do MCP")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "tasks_anydo.json")
    ap.add_argument("--out-pull", type=Path, default=ROOT / "pull_anydo.json")
    a = ap.parse_args()
    if a.pull:
        return cmd_pull(a.out_pull)
    if a.push:
        return cmd_push(a.dry_run)
    return cmd_export(a.out)


if __name__ == "__main__":
    raise SystemExit(main())
