#!/usr/bin/env python3
"""kuro_proposals.py — pilotage Discord : propositions numerotees, budgets, vacances.

Instances :
  P-YYYYMMDD-NN : propose -> valide -> applique | rejette. Persiste en local
  (proposals.local.json, gitignore, donnees privees). Dedoublonne par (source, titre).
Budgets quotidiens (UTC) : autofix_push=3, merge=1, revert_pr=1, comment=20.
Vacances : fichier vacances.flag ou KURO_VACANCES=1 -> tout passe en lecture seule.
Discord : francais relu (DeepSeek si dispo, sinon gabarits), zero emoji (R9 :
remplace les symboles qui rendent en emoji sur mobile).

Usage:
  python scripts/kuro_proposals.py --pending
  python scripts/kuro_proposals.py --weekly [--discord]
  python scripts/kuro_proposals.py --vacances on|off|statut
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
STORE = ROOT / "proposals.local.json"
VACANCES_FLAG = ROOT / "vacances.flag"
BUDGETS = {"autofix_push": 3, "merge": 1, "revert_pr": 1, "comment": 20, "review_fix": 2}
ASCII_MAP = {"✓": "OK", "✗": "KO", "→": "->", "·": "-", "—": "-", "–": "-"}


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")


def _load(path: Path | None = None) -> dict:
    try:
        data = json.loads((path or STORE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(store: dict, path: Path | None = None) -> None:
    try:
        (path or STORE).write_text(json.dumps(store, indent=1, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def add(source: str, title: str, detail: str = "", links: list | None = None,
        path: Path | None = None) -> str:
    """Cree une proposition (ou retourne l'ID existante si meme source+titre ouverte)."""
    store = _load(path)
    items = store.setdefault("items", {})
    for pid, p in items.items():
        if isinstance(p, dict) and p.get("source") == source and p.get("title") == title \
                and p.get("status") in ("propose", "valide"):
            return pid
    day = _today()
    n = sum(1 for pid in items if pid.startswith(f"P-{day}-")) + 1
    pid = f"P-{day}-{n:02d}"
    items[pid] = {"source": source, "title": title[:160], "detail": detail[:800],
                  "links": links or [], "status": "propose", "created": day, "updated": day}
    _save(store, path)
    return pid


def set_status(pid: str, status: str, path: Path | None = None) -> bool:
    if status not in ("propose", "valide", "applique", "rejette"):
        return False
    store = _load(path)
    item = store.get("items", {}).get(pid)
    if not isinstance(item, dict):
        return False
    item["status"] = status
    item["updated"] = _today()
    _save(store, path)
    return True


def pending(path: Path | None = None) -> list:
    store = _load(path)
    items = store.get("items", {})
    return [{"id": pid, **p} for pid, p in sorted(items.items())
            if isinstance(p, dict) and p.get("status") in ("propose", "valide")]


def seen(key: str, path: Path | None = None) -> bool:
    return key in _load(path).get("seen", {})


def mark_seen(key: str, path: Path | None = None) -> None:
    store = _load(path)
    seen_map = store.setdefault("seen", {})
    seen_map[key] = _today()
    while len(seen_map) > 500:
        seen_map.pop(next(iter(seen_map)))
    _save(store, path)


def budget_left(kind: str, path: Path | None = None) -> int:
    store = _load(path)
    usage = store.setdefault("usage", {})
    day = _today()
    if usage.get("day") != day:
        usage["day"] = day
        usage["used"] = {}
    return BUDGETS.get(kind, 0) - usage.get("used", {}).get(kind, 0)


def budget_use(kind: str, path: Path | None = None) -> bool:
    store = _load(path)
    if budget_left(kind, path) <= 0:
        return False
    usage = store.setdefault("usage", {})
    if usage.get("day") != _today():
        usage["day"] = _today()
        usage["used"] = {}
    used = usage.setdefault("used", {})
    used[kind] = used.get(kind, 0) + 1
    _save(store, path)
    return True


def vacances(path: Path | None = None) -> bool:
    if os.environ.get("KURO_VACANCES") == "1":
        return True
    return (path or VACANCES_FLAG).exists()


def set_vacances(on: bool) -> None:
    if on:
        try:
            VACANCES_FLAG.write_text(_today() + "\n", encoding="utf-8")
        except Exception:
            pass
    elif VACANCES_FLAG.exists():
        try:
            VACANCES_FLAG.unlink()
        except Exception:
            pass


def clean_fr(text: str) -> str:
    """Version Discord : ASCII sur, sans symboles a rendu emoji, sans mojibake."""
    for src, dst in ASCII_MAP.items():
        text = text.replace(src, dst)
    text = text.replace("�", "?")
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def polish_fr(text: str) -> str:
    """Relecture francais via LLM si dispo, sinon gabarit nettoye."""
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        from kuro_llm import ask
        out = ask("Reformule en francais correct, concis, sans emoji, sans changer "
                  "les faits, chiffres, noms et liens :\n" + text[:1500],
                  system="Tu es correcteur. Reponds uniquement le texte reformule.")
        if out:
            return clean_fr(out)
    except Exception:
        pass
    return clean_fr(text)


def post_discord(title: str, lines: list[str], color: int = 3447003) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url or not lines:
        return False
    payload = {"username": "Kuro", "embeds": [{
        "title": clean_fr(title)[:200],
        "description": clean_fr("\n".join(lines))[:1900],
        "color": color}]}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                     headers={"Content-Type": "application/json",
                                              "User-Agent": "Kuro/1.0"})
        urllib.request.urlopen(req, timeout=15)
        return True
    except Exception as e:
        print(f"Discord erreur : {e}")
        return False


def weekly_summary(path: Path | None = None) -> str:
    store = _load(path)
    items = [p for p in store.get("items", {}).values() if isinstance(p, dict)]
    by_status: dict[str, int] = {}
    for p in items:
        by_status[p.get("status", "?")] = by_status.get(p.get("status", "?"), 0) + 1
    lines = [f"Pilotage hebdo : {by_status.get('applique', 0)} appliquee(s), "
             f"{by_status.get('valide', 0)} validee(s) en attente, "
             f"{by_status.get('propose', 0)} proposee(s), "
             f"{by_status.get('rejette', 0)} rejetee(s)."]
    for p in pending(path)[:10]:
        lines.append(f"- {p['id']} [{p['status']}] {p['title'][:100]}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Pilotage Kuro : propositions, budgets, vacances")
    ap.add_argument("--pending", action="store_true")
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--discord", action="store_true")
    ap.add_argument("--vacances", choices=["on", "off", "statut"])
    a = ap.parse_args()
    if a.vacances:
        if a.vacances == "statut":
            print("vacances :", "ON" if vacances() else "OFF")
        else:
            set_vacances(a.vacances == "on")
            print("vacances :", a.vacances.upper())
        return 0
    if a.weekly:
        text = weekly_summary()
        print(text)
        if a.discord and not post_discord("Pilotage hebdo", [polish_fr(text)]):
            print("post Discord impossible (webhook absent ou rejete)")
            return 1
        return 0
    items = pending()
    if not items:
        print("Aucune proposition en attente.")
        return 0
    for p in items:
        print(f"{p['id']} [{p['status']}] {p['title']}")
        if p.get("detail"):
            print(f"    {p['detail'][:160]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
