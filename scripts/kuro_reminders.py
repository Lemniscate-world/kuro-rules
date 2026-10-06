#!/usr/bin/env python3
"""kuro_reminders.py — rappels d'abonnements sur Discord privé.

Lit la clé "subscriptions" de finances.local.json (gitigné, R111) et poste
un rappel Discord quand un renouvellement approche (défaut : 3 jours avant,
puis le jour même). Un seul rappel par abonnement et par jour (état local
~/.kuro/reminders_state.json).

Champs d'un abonnement :
    label             nom affiché
    amount            montant mensuel
    started           AAAA-MM-JJ du premier paiement
    renewal_day       jour du mois du renouvellement (1-28 conseillé)
    remind_days_before  (optionnel, défaut 3)

Usage:
    python scripts/kuro_reminders.py            # vérifie et poste si besoin
    python scripts/kuro_reminders.py --force    # poste même si pas l'échéance
    python scripts/kuro_reminders.py --list     # affiche sans poster
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
FINANCES = ROOT / "finances.local.json"
STATE_FILE = Path.home() / ".kuro" / "reminders_state.json"
DEFAULT_REMIND_DAYS = 3


def load_dotenv() -> None:
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def next_renewal(sub: dict, today: date) -> date:
    day = int(sub.get("renewal_day", 28))
    # évite les jours inexistants (31 dans un mois à 30 jours etc.)
    for candidate_day in (day, day - 1, day - 2, 28):
        try:
            candidate = today.replace(day=candidate_day)
            break
        except ValueError:
            continue
    else:
        candidate = today
    if candidate < today:
        # déjà passé ce mois-ci -> mois suivant
        month = candidate.month + 1
        year = candidate.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        try:
            candidate = candidate.replace(year=year, month=month)
        except ValueError:
            candidate = candidate.replace(year=year, month=month, day=28)
    return candidate


def subscriptions() -> list[dict]:
    if not FINANCES.exists():
        return []
    data = json.loads(FINANCES.read_text(encoding="utf-8"))
    subs = data.get("subscriptions")
    return [s for s in subs if isinstance(s, dict) and s.get("label")] if isinstance(subs, list) else []


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=1), encoding="utf-8")
    except Exception:
        pass


def post_discord(title: str, description: str) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return False
    body = {"username": "Kuro", "embeds": [
        {"title": title[:250], "description": description[:1900], "color": 0xFFA500}]}
    try:
        req = urllib.request.Request(
            url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "User-Agent": "Kuro/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        print(f"Discord erreur : {exc}")
        return False


def check(force: bool, post: bool) -> list[str]:
    today = date.today()
    state = load_state()
    lines = []
    for sub in subscriptions():
        label = sub["label"]
        amount = float(sub.get("amount", 0))
        renewal = next_renewal(sub, today)
        days_left = (renewal - today).days
        remind_before = int(sub.get("remind_days_before", DEFAULT_REMIND_DAYS))
        key = f"{label}:{today.isoformat()}"
        due = force or days_left <= remind_before
        if due and not state.get("sent", {}).get(key):
            msg = (f"**{label}** — {amount:.2f}$ se renouvelle le {renewal.isoformat()} "
                   f"({'aujourd''hui' if days_left == 0 else f'dans {days_left} jour(s)'})")
            lines.append(msg)
            if post:
                ok = post_discord("[KURO] Rappel abonnement", msg)
                if ok:
                    state.setdefault("sent", {})[key] = True
                    lines[-1] += "  (posté sur Discord)"
    save_state(state)
    if not lines:
        lines.append("Aucun renouvellement proche.")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Rappels d'abonnements Kuro")
    ap.add_argument("--force", action="store_true", help="poste même si pas l'échéance")
    ap.add_argument("--list", action="store_true", help="affiche sans poster")
    a = ap.parse_args()
    load_dotenv()
    for line in check(force=a.force, post=not a.list):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
