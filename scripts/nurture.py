#!/usr/bin/env python3
"""nurture.py — mini-CRM local (stdlib, R93). 100% local, jamais commité.

Fichier : nurture.local.json (gitignore). Étapes : lead -> contact -> call
-> client (ou lost). Chaque fiche : handle, canal, intérêt, prochaine étape + date.

Usage :
    python scripts/nurture.py add --handle x --canal reddit --interest "debug NaN"
    python scripts/nurture.py list
    python scripts/nurture.py due
    python scripts/nurture.py advance --handle x --note "call jeudi" --next 2026-10-02
    python scripts/nurture.py lost --handle x --note "pas de fit"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "nurture.local.json"

STAGES = ("lead", "contact", "call", "client", "lost")
NEXT_INDEX = {"lead": "contact", "contact": "call", "call": "client"}


def _load() -> dict:
    if not STORE.exists():
        return {"prospects": {}}
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return {"prospects": {}}
    if not isinstance(data, dict) or not isinstance(data.get("prospects"), dict):
        return {"prospects": {}}
    return data


def _save(data: dict) -> None:
    STORE.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def add(handle: str, canal: str, interest: str) -> dict:
    """Crée une fiche lead. Lève ValueError si doublon ou champ vide."""
    handle = (handle or "").strip()
    if not handle:
        raise ValueError("handle requis")
    data = _load()
    if handle in data["prospects"]:
        raise ValueError(f"doublon : {handle} existe déjà")
    data["prospects"][handle] = {
        "canal": (canal or "").strip(),
        "interest": (interest or "").strip(),
        "stage": "lead",
        "notes": [],
        "next": "",
        "updated": str(date.today()),
    }
    _save(data)
    return data["prospects"][handle]


def advance(handle: str, note: str, next_date: str = "") -> dict:
    """Passe à l'étape suivante (lead->contact->call->client)."""
    data = _load()
    if handle not in data["prospects"]:
        raise KeyError(f"inconnu : {handle}")
    fiche = data["prospects"][handle]
    if fiche["stage"] not in NEXT_INDEX:
        raise ValueError(f"stade final ({fiche['stage']}), utilisez lost si besoin")
    fiche["stage"] = NEXT_INDEX[fiche["stage"]]
    if note.strip():
        fiche["notes"].append(f"{date.today()}: {note.strip()}"[:300])
    fiche["next"] = next_date.strip()
    fiche["updated"] = str(date.today())
    _save(data)
    return fiche


def mark_lost(handle: str, note: str) -> dict:
    data = _load()
    if handle not in data["prospects"]:
        raise KeyError(f"inconnu : {handle}")
    fiche = data["prospects"][handle]
    fiche["stage"] = "lost"
    if note.strip():
        fiche["notes"].append(f"{date.today()}: {note.strip()}"[:300])
    fiche["next"] = ""
    fiche["updated"] = str(date.today())
    _save(data)
    return fiche


def due(today: str = "") -> list[str]:
    """Handles avec next <= aujourd'hui et stade non final."""
    today = today or str(date.today())
    data = _load()
    return sorted(h for h, f in data["prospects"].items()
                  if f.get("next") and f["next"] <= today and f.get("stage") not in ("client", "lost"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Mini-CRM local")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_add = sub.add_parser("add")
    p_add.add_argument("--handle", required=True)
    p_add.add_argument("--canal", default="")
    p_add.add_argument("--interest", default="")
    p_adv = sub.add_parser("advance")
    p_adv.add_argument("--handle", required=True)
    p_adv.add_argument("--note", default="")
    p_adv.add_argument("--next", default="")
    p_lost = sub.add_parser("lost")
    p_lost.add_argument("--handle", required=True)
    p_lost.add_argument("--note", default="")
    sub.add_parser("list")
    sub.add_parser("due")
    args = ap.parse_args()
    try:
        if args.cmd == "add":
            fiche = add(args.handle, args.canal, args.interest)
            print(f"{args.handle} : lead créé ({fiche['canal']})")
        elif args.cmd == "advance":
            fiche = advance(args.handle, args.note, args.next)
            print(f"{args.handle} : -> {fiche['stage']}")
        elif args.cmd == "lost":
            mark_lost(args.handle, args.note)
            print(f"{args.handle} : -> lost")
        elif args.cmd == "list":
            for h, f in sorted(_load()["prospects"].items()):
                print(f"{h} [{f['stage']}] {f['canal']} next={f['next'] or '-'}")
        elif args.cmd == "due":
            for h in due():
                print(h)
    except (ValueError, KeyError) as exc:
        print(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
