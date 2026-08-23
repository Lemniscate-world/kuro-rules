#!/usr/bin/env python3
"""kuro_finance.py — module finance LOCAL de Kuro (R111).

Lit finances.local.json (gitigné, jamais commité) et calcule :
  - Burn Rate mensuel (moyenne des dépenses sur la fenêtre analysée)
  - MRR (moyenne des revenus mensuels)
  - Net burn (burn - MRR)
  - Runway en mois (trésorerie / net burn)
  - Unit economics optionnels : CAC, LTV, ratio LTV:CAC (clé "acquisition")

Chaque relevé est archivé dans ~/.kuro/finance_history.jsonl (local uniquement,
R111) pour alimenter la tendance d'un appel à l'autre.

Zéro réseau, zéro appel LLM, zéro export : les données financières ne
quittent JAMAIS cette machine (R111).

Usage:
    python scripts/kuro_finance.py [--file finances.local.json] [--window 6] [--json]
        [--no-history]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_FILE = ROOT_DIR / "finances.local.json"
WINDOW_MONTHS = 6
HISTORY_FILE = Path.home() / ".kuro" / "finance_history.jsonl"
HISTORY_MAX_LINES = 400

NO_DECIMAL_CURRENCIES = {"XOF", "FCFA", "XAF"}


class FinanceError(Exception):
    pass


def load_finances(path: Path) -> dict:
    if not path.exists():
        raise FinanceError(
            f"{path} introuvable. Copiez finances.local.example.json vers "
            f"finances.local.json puis remplissez vos chiffres (fichier gitigné, R111)."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FinanceError(f"JSON invalide dans {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise FinanceError(f"{path} doit contenir un objet JSON racine.")
    return data


def month_list(data: dict) -> list[dict]:
    months = data.get("months")
    if not isinstance(months, list):
        raise FinanceError("Clé 'months' absente ou invalide (liste attendue).")
    parsed: list[dict] = []
    for entry in months:
        if not isinstance(entry, dict) or "month" not in entry:
            raise FinanceError(f"Mois invalide (objet avec 'month' requis): {entry!r}")
        expenses = sum(float(x["amount"]) for x in entry.get("expenses", []) if isinstance(x, dict))
        revenues = sum(float(x["amount"]) for x in entry.get("revenues", []) if isinstance(x, dict))
        parsed.append(
            {
                "month": str(entry["month"]),
                "expenses": round(expenses, 2),
                "revenues": round(revenues, 2),
                "net": round(revenues - expenses, 2),
            }
        )
    parsed.sort(key=lambda m: m["month"])
    return parsed


def compute(data: dict, window: int = WINDOW_MONTHS, source_file: Path | None = None) -> dict:
    currency = str(data.get("currency", "USD")).upper()
    starting_cash = float(data.get("starting_cash", 0))
    months = month_list(data)
    if not months:
        raise FinanceError("Aucun mois renseigné dans le fichier finances.")

    analyzed = months[-window:]
    n = len(analyzed)
    burn_rate = round(sum(m["expenses"] for m in analyzed) / n, 2)
    mrr = round(sum(m["revenues"] for m in analyzed) / n, 2)
    net_burn = round(burn_rate - mrr, 2)

    if net_burn <= 0:
        runway_months = None
        runway_label = "infini" if net_burn < 0 or starting_cash >= 0 else "0"
    elif starting_cash <= 0:
        runway_months = 0.0
        runway_label = "0 (trésorerie vide)"
    else:
        runway_months = round(starting_cash / net_burn, 1)
        runway_label = f"{runway_months} mois"

    if net_burn <= 0 and starting_cash >= 0 and burn_rate == 0:
        status = "idle"
    elif runway_months is None or runway_months >= 6:
        status = "healthy"
    elif runway_months < 3:
        status = "critical"
    else:
        status = "warning"

    return {
        "source_file": str(source_file or DEFAULT_FILE),
        "currency": currency,
        "starting_cash": starting_cash,
        "months_analyzed": n,
        "burn_rate_monthly": burn_rate,
        "mrr_monthly": mrr,
        "net_burn_monthly": net_burn,
        "runway_months": runway_months,
        "runway_label": runway_label,
        "status": status,
        "unit_economics": unit_economics(data),
        "monthly": analyzed,
        "computed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def unit_economics(data: dict) -> dict:
    """CAC / LTV / ratio LTV:CAC — section optionnelle 'acquisition' (R111 : local)."""
    acq = data.get("acquisition")
    if not isinstance(acq, dict):
        return {"configured": False, "cac": None, "ltv": None, "ltv_cac_ratio": None, "status": "idle"}
    spend = float(acq.get("monthly_marketing_spend", 0) or 0)
    customers = float(acq.get("new_customers_per_month", 0) or 0)
    arpu = float(acq.get("arpu_monthly", 0) or 0)
    margin = float(acq.get("gross_margin_pct", 100) or 100) / 100.0
    lifetime = float(acq.get("avg_customer_lifetime_months", 12) or 12)
    cac = round(spend / customers, 2) if customers > 0 and spend > 0 else None
    ltv = round(arpu * margin * lifetime, 2) if arpu > 0 and lifetime > 0 else None
    ratio = round(ltv / cac, 2) if cac and ltv else None
    if ratio is None:
        status = "incomplete"
    elif ratio >= 3:
        status = "healthy"
    elif ratio >= 1:
        status = "warning"
    else:
        status = "critical"
    return {"configured": True, "cac": cac, "ltv": ltv, "ltv_cac_ratio": ratio, "status": status}


def read_last_snapshot(path: Path | None = None) -> dict | None:
    file_path = path or HISTORY_FILE
    try:
        lines = file_path.read_text(encoding="utf-8").strip().splitlines()
        return json.loads(lines[-1]) if lines else None
    except Exception:
        return None


def build_trend(previous: dict, current: dict) -> dict:
    def delta(field: str):
        try:
            prev_val, cur_val = previous.get(field), current.get(field)
            if prev_val is None or cur_val is None:
                return None
            return round(float(cur_val) - float(prev_val), 2)
        except (TypeError, ValueError):
            return None

    return {
        "previous_at": previous.get("at"),
        "runway_delta_months": delta("runway_months"),
        "burn_delta": delta("burn_rate_monthly"),
    }


def append_history(payload: dict, path: Path | None = None) -> bool:
    file_path = path or HISTORY_FILE
    entry = {
        "at": payload["computed_at"],
        "starting_cash": payload["starting_cash"],
        "burn_rate_monthly": payload["burn_rate_monthly"],
        "mrr_monthly": payload["mrr_monthly"],
        "net_burn_monthly": payload["net_burn_monthly"],
        "runway_months": payload["runway_months"],
        "status": payload["status"],
    }
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        trim_history(file_path)
        return True
    except Exception:
        return False


def trim_history(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        if len(lines) > HISTORY_MAX_LINES:
            path.write_text("\n".join(lines[-HISTORY_MAX_LINES:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def compute_from_default(
    window: int = WINDOW_MONTHS,
    path: Path | None = None,
    keep_history: bool = True,
) -> dict:
    file_path = path or DEFAULT_FILE
    payload = compute(load_finances(file_path), window=window, source_file=file_path)
    previous = read_last_snapshot()
    if previous:
        payload["trend"] = build_trend(previous, payload)
    if keep_history:
        append_history(payload)
    return payload


def fmt_amount(value: float, currency: str) -> str:
    symbol = {"USD": "$", "EUR": "€"}.get(currency, "")
    code = currency if currency in ("XOF", "FCFA") else ""
    if currency in NO_DECIMAL_CURRENCIES:
        body = f"{value:,.0f}".replace(",", " ")
        return f"{body} {code}".strip()
    text = f"{value:,.2f}".replace(",", " ")
    return f"{symbol}{text}" if symbol else f"{text} {code}".strip()


def render(payload: dict) -> str:
    cur = payload["currency"]
    lines = [
        f"Finances Kuro ({payload['source_file']})",
        f"  Trésorerie   : {fmt_amount(payload['starting_cash'], cur)}",
        f"  Burn mensuel : {fmt_amount(payload['burn_rate_monthly'], cur)}"
        f"  (fenêtre {payload['months_analyzed']} mois)",
        f"  MRR          : {fmt_amount(payload['mrr_monthly'], cur)}",
        f"  Net burn     : {fmt_amount(payload['net_burn_monthly'], cur)}",
        f"  Runway       : {payload['runway_label']}",
        f"  Statut       : {payload['status'].upper()}",
    ]
    ue = payload.get("unit_economics") or {}
    if ue.get("configured"):
        cac_s = fmt_amount(ue["cac"], cur) if ue["cac"] is not None else "—"
        ltv_s = fmt_amount(ue["ltv"], cur) if ue["ltv"] is not None else "—"
        ratio_s = f"{ue['ltv_cac_ratio']:.2f}" if ue["ltv_cac_ratio"] is not None else "—"
        lines += [
            f"  CAC          : {cac_s}",
            f"  LTV          : {ltv_s}",
            f"  LTV/CAC      : {ratio_s} ({ue['status']})",
        ]
    trend = payload.get("trend")
    if trend and trend.get("runway_delta_months") is not None:
        d = trend["runway_delta_months"]
        arrow = "▲" if d > 0 else ("▼" if d < 0 else "=")
        lines.append(f"  Tendance     : runway {arrow} {abs(d)} mois depuis le relevé précédent")
    lines.append("  Détail:")
    for m in payload["monthly"]:
        lines.append(
            f"    {m['month']}  dépenses {fmt_amount(m['expenses'], cur):>12}"
            f"  revenus {fmt_amount(m['revenues'], cur):>12}"
            f"  net {fmt_amount(m['net'], cur):>12}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Finances locales Kuro (R111)")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--window", type=int, default=WINDOW_MONTHS)
    parser.add_argument("--no-history", action="store_true", help="ne pas archiver le relevé")
    parser.add_argument("--json", action="store_true", help="sortie JSON brute")
    args = parser.parse_args()
    try:
        payload = compute_from_default(
            window=args.window, path=args.file, keep_history=not args.no_history
        )
    except FinanceError as exc:
        print(f"[!] {exc}")
        return 1
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else render(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
