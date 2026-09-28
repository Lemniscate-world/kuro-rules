#!/usr/bin/env python3
"""kuro_finance_report.py — rapport financier (avec montants), usage privé.

Lit ~/.kuro/finance_history.jsonl (relevés archivés par kuro_finance.py) et
produit un rapport avec montants, publié sur Discord PRIVÉ (usage interne).

R111 : confirmation explicite du propriétaire (2026-09-18) — les montants,
même à $0, sont autorisés sur le Discord privé. Toujours : aucun montant
dans un repo public, une issue, une PR, X, ou un canal public.

Usage:
    python scripts/kuro_finance_report.py                # rapport texte
    python scripts/kuro_finance_report.py --json         # JSON brut
    python scripts/kuro_finance_report.py --limit 12     # N derniers relevés
    python scripts/kuro_finance_report.py --discord      # poste sur Discord
    python scripts/kuro_finance_report.py --discord --full  # + détail mois par mois
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HISTORY_FILE = Path.home() / ".kuro" / "finance_history.jsonl"


def load_dotenv() -> None:
    """Charge .env local (DISCORD_WEBHOOK_URL) comme kuro_automate.py."""
    import os
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

STATUS_ICONS = {"healthy": "🟢", "warning": "🟡", "critical": "🔴", "idle": "⚪"}


def load_history(path: Path | None = None) -> list[dict]:
    file_path = path or HISTORY_FILE
    if not file_path.exists():
        print(
            f"[!] Aucun historique dans {file_path}.\n"
            "    Lance d'abord: python scripts/kuro_finance.py  (il archive chaque relevé)."
        )
        return []
    entries: list[dict] = []
    for line in file_path.read_text(encoding="utf-8").strip().splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def index_series(values: list[float]) -> list[float]:
    """Indexe une série à 100 sur la première valeur (métrique relative, sans montants)."""
    base = next((v for v in values if v), None)
    if base is None:
        return [0.0] * len(values)
    return [round(v / base * 100, 1) for v in values]


def sparkline(values: list[float], width: int = 40) -> str:
    if not values:
        return "(vide)"
    lo, hi = min(values), max(values)
    blocks = "▁▂▃▄▅▆▇█"
    if hi == lo:
        return "─" * min(len(values), width)
    return "".join(
        blocks[min(int((v - lo) / (hi - lo) * 7), 7)] for v in values
    )[-width:]


def build_report(entries: list[dict], limit: int) -> dict:
    recent = entries[-limit:]
    statuses = [e.get("status", "unknown") for e in recent]
    runway = [e.get("runway_months") for e in recent]
    burn = [e.get("burn_rate_monthly", 0) for e in recent]
    mrr = [e.get("mrr_monthly", 0) for e in recent]
    cash = [e.get("starting_cash", 0) for e in recent]
    net = [e.get("net_burn_monthly", 0) for e in recent]

    runway_known = [r for r in runway if r is not None]
    runway_trend = (
        "infini" if all(r is None for r in runway)
        else ("stable" if len({str(r) for r in runway}) == 1
              else f"{'en amélioration' if runway_known[-1] > runway_known[0] else 'en baisse'}")
    )

    # Raisonnement : diagnostic lisible pour l'humain (ce qui explique le statut)
    last = recent[-1] if recent else {}
    reasoning = explain(last)

    return {
        "snapshots": len(entries),
        "window": len(recent),
        "first_at": recent[0].get("at") if recent else None,
        "last_at": recent[-1].get("at") if recent else None,
        "status_current": statuses[-1] if statuses else "unknown",
        "status_history": statuses,
        "runway_trend": runway_trend,
        "burn_index_100": index_series(burn),
        "mrr_index_100": index_series(mrr),
        # --- Montants (autorises sur Discord privé, confirmation R111 du 2026-09-18) ---
        "cash_current": cash[-1] if cash else 0,
        "burn_current": burn[-1] if burn else 0,
        "mrr_current": mrr[-1] if mrr else 0,
        "net_burn_current": net[-1] if net else 0,
        "runway_current": runway[-1],
        "reasoning": reasoning,
    }


def explain(last: dict) -> list[str]:
    """Raisonnement en langage humain : pourquoi ce statut, que faire."""
    lines = []
    status = last.get("status", "unknown")
    cash = float(last.get("starting_cash", 0) or 0)
    net = float(last.get("net_burn_monthly", 0) or 0)
    mrr = float(last.get("mrr_monthly", 0) or 0)
    if status == "critical":
        if cash <= 0:
            lines.append("Trésorerie studio à 0$ : le runway ne peut pas être calculé. "
                        "Le statut 'critical' est technique (pas de réserve dédiée), "
                        "pas une alerte de survie tant que les dépenses sont couvertes.")
        else:
            lines.append(f"Net burn de {net:.2f}$ par mois avec {cash:.2f}$ en caisse : "
                        "moins de 3 mois de marge.")
    elif status == "idle":
        lines.append("Aucune dépense ni revenu ce mois : studio en veille.")
    elif status == "healthy":
        lines.append("Marge saine : 6 mois ou plus de runway, ou revenus supérieurs aux dépenses.")
    if mrr == 0 and status != "idle":
        lines.append("MRR à 0$ : aucune source de revenus active. "
                    "Priorité : premier client/utilisateur payant sur un produit du studio.")
    if net > 0 and mrr == 0:
        lines.append(f"Coût actuel ~{net:.2f}$/mois : un seul abonnement à 15$/mois "
                    "rend le studio rentable.")
    return lines


def render(report: dict, detail_months: list[dict] | None = None) -> str:
    icon = STATUS_ICONS.get(report["status_current"], "·")
    lines = [
        "═══ Finances Kuro — point studio ═══",
        f"  Statut        : {icon} {report['status_current'].upper()}",
        f"  Trésorerie    : {fmt(report['cash_current'])}",
        f"  Burn brut     : {fmt(report['burn_current'])}/mois",
        f"  MRR           : {fmt(report['mrr_current'])}/mois",
        f"  Net burn      : {fmt(report['net_burn_current'])}/mois",
        f"  Runway        : {fmt_runway(report['runway_current'])} (tendance : {report['runway_trend']})",
        "",
        "**Pourquoi ce statut :**",
    ]
    lines += [f"  • {r}" for r in report["reasoning"]] or ["  • (pas de diagnostic)"]
    if detail_months:
        lines += ["", "**Détail récent :**"]
        for m in detail_months[-6:]:
            lines.append(
                f"  {m.get('month', '?')}  dépenses {fmt(m.get('expenses', 0))}  "
                f"revenus {fmt(m.get('revenues', 0))}  net {fmt(m.get('net', 0))}"
            )
    lines += [
        "",
        f"  Relevés archivés : {report['snapshots']} · fenêtre {report['window']} · "
        f"maj {report['last_at']}",
    ]
    return "\n".join(lines)


def fmt(value) -> str:
    try:
        return f"{float(value):.2f}$"
    except (TypeError, ValueError):
        return "—"


def fmt_runway(value) -> str:
    if value is None:
        return "infini"
    try:
        return f"{float(value):.1f} mois"
    except (TypeError, ValueError):
        return "?"


def main() -> int:
    parser = argparse.ArgumentParser(description="Rapport finance Kuro (Discord privé, montants autorisés)")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--discord", action="store_true",
                        help="poste le rapport (avec montants) sur Discord privé")
    parser.add_argument("--full", action="store_true",
                        help="ajoute le détail mois par mois au message")
    args = parser.parse_args()
    load_dotenv()
    entries = load_history()
    if not entries:
        return 1
    report = build_report(entries, args.limit)

    # Détail mois par mois : relit finances.local.json (les mêmes chiffres que kuro_finance)
    detail = None
    if args.full:
        try:
            fin_path = Path(__file__).resolve().parent.parent / "finances.local.json"
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from kuro_finance import month_list, load_finances
            detail = month_list(load_finances(fin_path))
        except Exception:
            detail = None

    text = render(report, detail)
    print(json.dumps(report, indent=2, ensure_ascii=False) if args.json else text)
    if args.discord:
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from kuro_proposals import post_discord
            ok = post_discord("[KURO] Finances studio — point direct", text.splitlines())
            print("Discord : posté" if ok else "Discord : non posté (webhook absent)")
            return 0 if ok else 1
        except Exception as exc:
            print(f"Discord erreur : {exc}")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
