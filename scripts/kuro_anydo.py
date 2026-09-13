#!/usr/bin/env python3
"""kuro_anydo.py — bridge Kuro <-> Any.do MCP (https://mcp.any.do/sse).

Any.do MCP sait faire (doc officielle) : taches perso (create/update/archive/delete),
reminders uniques/recurrents, boards workspace, events calendrier, listes courses.
Endpoint protege par OAuth2, setup desktop : Claude Settings > Connectors > Add custom
connector avec https://mcp.any.do/sse, ou ChatGPT Settings > Plugins > + MCP server.

Ce script ne parle pas encore SSE tout seul (OAuth manuel requis). Il fait le lien
deterministe cote Kuro :
  --export : convertit pipeline.local.json next_steps + kuro_strategy decisions
             en tasks_anydo.json importable / copiable dans Claude avec le connecteur.
  --push   : experimental, exige ANYDO_TOKEN (bearer OAuth). POST tasks une par une.
             Sans token : affiche la marche a suivre, ne casse jamais.

Usage:
  python scripts/kuro_anydo.py --export [--out tasks_anydo.json]
  ANYDO_TOKEN=xxx python scripts/kuro_anydo.py --push --dry-run
"""
import argparse
import json
import sys
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


def collect_tasks() -> list[dict]:
    tasks = []
    pipe = load_json(PIPELINE)
    for e in (pipe.get("entries", []) or [])[-10:]:
        ns = (e.get("next_step") or "").strip() if isinstance(e, dict) else ""
        if ns:
            tasks.append({
                "title": ns[:120],
                "source": "pipeline.next_step",
                "date": e.get("date", ""),
                "due": "",
            })
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import kuro_strategy
        payload = kuro_strategy.build_payload()
        for d in payload.get("decisions", [])[:8]:
            tasks.append({"title": d[:120], "source": "strategy.decision", "date": "", "due": ""})
    except Exception:
        pass
    # dedup sur titre
    seen, out = set(), []
    for t in tasks:
        if t["title"] not in seen:
            seen.add(t["title"])
            out.append(t)
    return out


def cmd_export(out: Path):
    tasks = collect_tasks()
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
    ok = 0
    for t in tasks[:20]:
        try:
            req = urllib.request.Request(
                MCP_URL,
                data=json.dumps({"title": t["title"]}).encode(),
                method="POST",
                headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=20):
                ok += 1
        except Exception as e:
            print(f"Echec push '{t['title'][:40]}' : {e}")
            break
    print(f"Poussees : {ok}/{len(tasks)}")
    return 0


def main():
    ap = argparse.ArgumentParser(description="Bridge Kuro <-> Any.do MCP")
    ap.add_argument("--export", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "tasks_anydo.json")
    a = ap.parse_args()
    if a.push:
        return cmd_push(a.dry_run)
    return cmd_export(a.out)


if __name__ == "__main__":
    raise SystemExit(main())
