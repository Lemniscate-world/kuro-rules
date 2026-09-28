#!/usr/bin/env python3
"""kuro_bot.py — bot Discord : pilote Kuro depuis Discord, zéro CLI.

Commandes (préfixe !, salon privé) :
    !finance                 point finance complet (montants + raisonnement)
    !finance full            + détail mois par mois
    !abos                    liste des abonnements + prochains renouvellements
    !abos add <label> <montant> <jour>   ex: !abos add "Vercel Pro" 20 5
    !abos remove <label>     retire un abonnement
    !rappel                  force la vérification des rappels maintenant
    !propositions            liste les propositions en attente (P-...)
    !valide <P-ID>           valide une proposition
    !rejette <P-ID>          rejette une proposition
    !vacances on|off         mode vacances (lecture seule globale)
    !aide                    la liste des commandes

Sécurité (R111) : les réponses finance contiennent les montants — le bot
doit donc être installé sur un serveur/salon PRIVÉ. Garde-fous :
    - ALLOWED_CHANNEL_IDS dans .env (recommandé) : le bot ignore les autres salons
    - ALLOWED_USER_IDS dans .env (recommandé) : le bot ignore les autres utilisateurs
    - jamais d'écriture repo : les commandes ne touchent que les fichiers locaux gitignés

Setup (une seule fois) :
    1. Discord -> Paramètres -> Développeurs -> Applications -> New Application
    2. Onglet Bot -> Reset Token -> copier dans .env : DISCORD_BOT_TOKEN=...
    3. Onglet Bot -> Message Content Intent : ON (obligatoire)
    4. OAuth2 -> URL Generator : scopes=bot, permissions=Send Messages
       -> ouvrir l'URL générée pour inviter le bot sur ton serveur privé
    5. .env : DISCORD_BOT_TOKEN, DISCORD_FINANCE_CHANNEL_ID (id du salon privé)
    6. Lancer : python scripts/kuro_bot.py   (ou via tâche planifiée au démarrage)
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


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


load_dotenv()

FINANCES = ROOT / "finances.local.json"
ALLOWED_CHANNELS = {
    x.strip() for x in os.environ.get("ALLOWED_CHANNEL_IDS", "").split(",") if x.strip()
}
ALLOWED_USERS = {
    x.strip() for x in os.environ.get("ALLOWED_USER_IDS", "").split(",") if x.strip()
}


# ---------- helpers finances (lecture/écriture locale uniquement) ----------

def load_finances() -> dict:
    if not FINANCES.exists():
        return {}
    return json.loads(FINANCES.read_text(encoding="utf-8"))


def save_finances(data: dict) -> None:
    FINANCES.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def fmt(v) -> str:
    try:
        return f"{float(v):.2f}$"
    except (TypeError, ValueError):
        return "—"


# ---------- commandes ----------

def cmd_finance(full: bool) -> str:
    import kuro_finance_report
    entries = kuro_finance_report.load_history()
    if not entries:
        return "Aucun relevé archivé (lance le cycle Kuro une fois)."
    report = kuro_finance_report.build_report(entries, 12)
    detail = None
    if full:
        try:
            from kuro_finance import month_list, load_finances
            detail = month_list(load_finances(FINANCES))
        except Exception:
            detail = None
    return kuro_finance_report.render(report, detail)


def cmd_abos() -> str:
    from kuro_reminders import next_renewal, subscriptions
    subs = subscriptions()
    if not subs:
        return "Aucun abonnement enregistré. `!abos add <label> <montant> <jour>`"
    today = date.today()
    lines = ["**Abonnements du studio :**"]
    total = 0.0
    for s in subs:
        amt = float(s.get("amount", 0))
        total += amt
        renewal = next_renewal(s, today)
        days = (renewal - today).days
        when = "aujourd'hui" if days == 0 else f"dans {days} j"
        lines.append(f"• **{s['label']}** — {fmt(amt)}/mois · renouvellement "
                     f"{renewal.isoformat()} ({when})")
    lines.append(f"**Total : {fmt(total)}/mois**")
    return "\n".join(lines)


def cmd_abos_add(label: str, amount: str, day: str) -> str:
    try:
        amt = float(amount)
        day_i = int(day)
        if not (1 <= day_i <= 31):
            raise ValueError
    except ValueError:
        return "Usage : `!abos add <label> <montant> <jour 1-31>` — ex : `!abos add \"Vercel Pro\" 20 5`"
    data = load_finances()
    subs = data.setdefault("subscriptions", [])
    subs.append({"label": label, "amount": amt, "started": date.today().isoformat(),
                 "renewal_day": day_i, "remind_days_before": 3})
    save_finances(data)
    return f"Abonnement ajouté : **{label}** — {fmt(amt)}/mois, renouvellement le {day_i}, rappel Discord J-3."


def cmd_abos_remove(label: str) -> str:
    data = load_finances()
    subs = data.get("subscriptions", [])
    before = len(subs)
    subs = [s for s in subs if s.get("label", "").lower() != label.lower()]
    data["subscriptions"] = subs
    save_finances(data)
    removed = before - len(subs)
    return (f"Abonnement **{label}** retiré." if removed
            else f"Aucun abonnement nommé **{label}** (`!abos` pour la liste).")


def cmd_rappel() -> str:
    import kuro_reminders
    lines = kuro_reminders.check(force=True, post=True)
    return "Rappels vérifiés :\n" + "\n".join(f"• {l}" for l in lines)


def cmd_propositions() -> str:
    import kuro_proposals as P
    items = P.pending()
    if not items:
        return "Aucune proposition en attente."
    return "\n".join(f"• **{p['id']}** [{p['status']}] {p['title'][:120]}" for p in items[:15])


def cmd_valide(pid: str) -> str:
    import kuro_proposals as P
    return (f"**{pid}** validée." if P.set_status(pid, "valide")
            else f"Proposition **{pid}** inconnue (`!propositions`).")


def cmd_rejette(pid: str) -> str:
    import kuro_proposals as P
    return (f"**{pid}** rejetée." if P.set_status(pid, "rejette")
            else f"Proposition **{pid}** inconnue (`!propositions`).")


def cmd_vacances(arg: str) -> str:
    import kuro_proposals as P
    if arg not in ("on", "off"):
        return f"Vacances : {'ON' if P.vacances() else 'OFF'}. Usage : `!vacances on|off`"
    P.set_vacances(arg == "on")
    return f"Mode vacances : {'ON (lecture seule)' if arg == 'on' else 'OFF'}."


def cmd_velocity(top: int = 10) -> str:
    import cowork_pick
    import kuro_metrics
    try:
        payload = kuro_metrics.build_payload()
    except Exception as exc:
        return f"Velocite indisponible : {exc}"
    ctx = cowork_pick.load_db_context()
    ranking = cowork_pick.build_ranking(payload, ctx)
    return cowork_pick.render_velocity(ranking, top_n=top)


def cmd_pick(exclude: str = "") -> str:
    import cowork_pick
    import kuro_metrics
    try:
        payload = kuro_metrics.build_payload()
    except Exception as exc:
        return f"Pick indisponible : {exc}"
    ctx = cowork_pick.load_db_context()
    excluded = {e.strip() for e in exclude.split(",") if e.strip()}
    ranking = cowork_pick.build_ranking(payload, ctx, excluded)
    if not ranking:
        return "Aucun projet detectable pour le pick."
    return cowork_pick.render_pick(ranking[0], ranking)


def cmd_aide() -> str:
    return """**Kuro — commandes :**
`!finance` — point finance (montants + raisonnement)
`!finance full` — + détail mois par mois
`!abos` — abonnements + prochains renouvellements
`!abos add <label> <montant> <jour>` — ex : `!abos add "Vercel Pro" 20 5`
`!abos remove <label>` — retire un abonnement
`!rappel` — vérifie les rappels maintenant
`!propositions` — propositions en attente
`!valide <P-ID>` / `!rejette <P-ID>` — tranche une proposition
`!velocity [N]` — analyse velocite par projet (locale, 30j)
`!pick [--exclude A,B]` — Oracle : 2e repo par analyses + plan worker
`!vacances on|off` — pause globale (lecture seule)"""


def dispatch(content: str) -> str | None:
    parts = content.strip().split(maxsplit=2)
    if not parts or not parts[0].startswith("!"):
        return None
    cmd = parts[0][1:].lower()
    args = parts[1:]
    if cmd == "finance":
        return cmd_finance(full=len(args) > 0 and args[0].lower() == "full")
    if cmd == "abos":
        if not args:
            return cmd_abos()
        if args[0].lower() == "add" and len(args) >= 3:
            # label quoté supporté : !abos add "Vercel Pro" 20 5
            rest = content.split("add", 1)[1].strip()
            if rest.startswith('"'):
                label, _, rest = rest[1:].partition('"')
                fields = [f for f in rest.strip().split() if f]
            else:
                fields = rest.split()
                label, fields = fields[0], fields[1:]
            return cmd_abos_add(label, fields[0], fields[1]) if len(fields) >= 2 else \
                "Usage : `!abos add <label> <montant> <jour>`"
        if args[0].lower() == "remove" and len(args) >= 2:
            return cmd_abos_remove(args[1])
        return "Usage : `!abos`, `!abos add ...` ou `!abos remove <label>`"
    if cmd in ("rappel", "rappels", "remind"):
        return cmd_rappel()
    if cmd in ("propositions", "props"):
        return cmd_propositions()
    if cmd in ("valide", "valider"):
        return cmd_valide(args[0]) if args else "Usage : `!valide <P-ID>`"
    if cmd in ("rejette", "rejeter"):
        return cmd_rejette(args[0]) if args else "Usage : `!rejette <P-ID>`"
    if cmd == "vacances":
        return cmd_vacances(args[0].lower()) if args else cmd_vacances("")
    if cmd in ("velocity", "velocite", "velo"):
        try:
            top = int(args[0]) if args else 10
        except ValueError:
            top = 10
        return cmd_velocity(top=max(1, min(top, 20)))
    if cmd == "pick":
        rest = " ".join(args)
        excl = ""
        if "--exclude" in rest:
            excl = rest.split("--exclude", 1)[1].strip().lstrip("=").strip()
        elif args:
            excl = args[0] if args[0].startswith("!") is False and "," in args[0] else ""
        return cmd_pick(excl)
    if cmd in ("aide", "help"):
        return cmd_aide()
    return f"Commande `!{cmd}` inconnue. `!aide` pour la liste."


def run_bot() -> int:
    import discord
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        print("DISCORD_BOT_TOKEN absent du .env — voir en-tête du script pour le setup.")
        return 1

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"Kuro bot connecté : {client.user} — en écoute.")

    @client.event
    async def on_message(message):
        if message.author.bot:
            return
        if ALLOWED_CHANNELS and str(message.channel.id) not in ALLOWED_CHANNELS:
            return
        if ALLOWED_USERS and str(message.author.id) not in ALLOWED_USERS:
            return
        reply = dispatch(message.content)
        if reply:
            await message.channel.send(reply[:2000])

    client.run(token)
    return 0


if __name__ == "__main__":
    sys.exit(run_bot())
