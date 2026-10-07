#!/usr/bin/env python3
"""kuro_legs_watch.py — alerte quand une jambe LLM tombe DOWN (ou se releve).

Lit kuro_llm.brain_status() (cles + historique + sonde Ollama locale),
compare avec ~/.kuro/legs_state.json, poste sur Discord (DISCORD_WEBHOOK_URL)
uniquement les TRANSITIONS vers/depuis down. Idempotent, zero dependance
hors stdlib, jamais d exception levee.

Usage:
    python scripts/kuro_legs_watch.py [--check]   # --check = dry-run, affiche sans poster
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

STATE_FILE = Path.home() / ".kuro" / "legs_state.json"


def _load_state() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=1, ensure_ascii=False),
                              encoding="utf-8")
    except Exception:
        pass


def current_states() -> dict[str, str]:
    """{jambe: state} via brain_status (jamais d exception)."""
    try:
        import kuro_llm

        return {r.get("leg", "?"): r.get("state", "?")
                for r in kuro_llm.brain_status() if isinstance(r, dict)}
    except Exception:
        return {}


def transitions(old: dict, new: dict) -> list[str]:
    """Messages pour jambes passees a down (ou relevees de down)."""
    msgs = []
    for leg in sorted(set(old) | set(new)):
        before, after = old.get(leg, "?"), new.get(leg, "?")
        if after == "down" and before != "down":
            msgs.append(f"🔴 {leg} DOWN (etait {before})")
        elif before == "down" and after != "down":
            msgs.append(f"🟢 {leg} releve ({before} -> {after})")
    return msgs


def post_discord(text: str) -> bool:
    """Poste via webhook (False si absent/echec). Jamais d exception."""
    import os
    import urllib.request

    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return False
    try:
        req = urllib.request.Request(
            url, data=json.dumps({"content": text[:1800]}).encode(),
            headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30)
        return True
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Surveille les jambes LLM")
    ap.add_argument("--check", action="store_true",
                    help="dry-run : affiche sans poster ni memoriser")
    args = ap.parse_args()
    new = current_states()
    if not new:
        print("jambes illisibles (brain_status vide)")
        return 1
    old = _load_state()
    msgs = transitions(old, new)
    if args.check:
        print(json.dumps({"current": new, "transitions": msgs},
                         indent=2, ensure_ascii=False))
        return 0
    if msgs:
        ok = post_discord("**Kuro jambes**\n" + "\n".join(msgs))
        print(f"[{'!' if ok else '?'}] {'poste' if ok else 'webhook absent/echec'} : "
              + " ; ".join(msgs))
    else:
        print(f"RAS ({len(new)} jambes, aucun changement)")
    _save_state(new)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
