#!/usr/bin/env python3
"""kuro_strategy.py — digest stratégique hebdo Kuro : faits frais, décisions humaines.

Fusionne en un rapport unique (10-20 lignes) :
  - Finance   : kuro_finance (burn, runway, MRR) — R111, local
  - Exécution : kuro_metrics (vélocité, lead time, CI)
  - OKR       : strategy.local.json (objectifs chiffrés vs réalité mesurée)
  - Pipeline  : pipeline.local.json (interviews Mom Test, insights, leads)
  - CI        : ci-status.json (santé des repos)

Les "décisions à prendre" sont des règles déterministes (pas d'IA, pas de
spéculation) : chaque suggestion est déclenchée par un fait mesuré.

Données 100% locales (strategy.local.json / pipeline.local.json gitignorés).

Usage:
    python scripts/kuro_strategy.py [--json] [--discord] [--out chemin.md]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT_DIR = Path(__file__).resolve().parent.parent
STRATEGY_FILE = ROOT_DIR / "strategy.local.json"
PIPELINE_FILE = ROOT_DIR / "pipeline.local.json"
CI_FILE = ROOT_DIR / "ci-status.json"


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ---------- collecte ----------

def collect_finance() -> dict:
    try:
        import kuro_finance

        return kuro_finance.compute_from_default(keep_history=False)
    except Exception:
        return {}


def collect_metrics() -> dict:
    try:
        import kuro_metrics

        return kuro_metrics.build_payload()
    except Exception:
        return {}


def collect_ci() -> dict:
    try:
        data = json.loads(CI_FILE.read_text(encoding="utf-8"))
        repos = data.get("repos", []) or []
        total = sum(len(r.get("workflows", []) or []) for r in repos)
        fails = sum(
            1
            for r in repos
            for w in r.get("workflows", []) or []
            if w.get("conclusion") == "failure"
        )
        return {"overall": data.get("overall"), "total": total, "failures": fails}
    except Exception:
        return {}


def collect_pipeline() -> dict:
    data = _load(PIPELINE_FILE)
    entries = [e for e in data.get("entries", []) if isinstance(e, dict)]
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    interviews_7d = 0
    for e in entries:
        if e.get("type") == "interview":
            try:
                if datetime.fromisoformat(str(e.get("date", ""))) >= week_ago:
                    interviews_7d += 1
            except ValueError:
                continue
    last = max(entries, key=lambda e: str(e.get("date", ""))) if entries else None
    next_steps = [e for e in entries if e.get("next_step")][-3:]
    return {
        "total": len(entries),
        "interviews_7d": interviews_7d,
        "last": last,
        "next_steps": next_steps,
    }


# ---------- résolution des métriques OKR ----------

def resolve_metric(key: str, obj: dict, finance: dict, metrics: dict, pipeline: dict) -> float | None:
    if key == "manual":
        try:
            return float(obj.get("current", 0))
        except (TypeError, ValueError):
            return 0.0
    if key == "finance.mrr":
        return float(finance.get("mrr_monthly") or 0)
    if key == "finance.runway":
        v = finance.get("runway_months")
        return None if v is None else float(v)
    if key == "metrics.velocity":
        return float((metrics.get("averages") or {}).get("velocity_per_week") or 0)
    if key == "metrics.lead_time":
        return (metrics.get("averages") or {}).get("lead_time_days")
    if key == "pipeline.interviews_7d":
        return float(pipeline.get("interviews_7d") or 0)
    return None


def okr_progress(objectives: list[dict], finance: dict, metrics: dict, pipeline: dict) -> list[dict]:
    out: list[dict] = []
    for obj in objectives:
        target = float(obj.get("target", 0) or 0)
        current = resolve_metric(str(obj.get("metric", "")), obj, finance, metrics, pipeline)
        pct = None
        if current is not None and target > 0:
            pct = round(min(100.0, current / target * 100.0))
        out.append(
            {
                "key": obj.get("key"),
                "label": obj.get("label"),
                "target": target,
                "current": current,
                "pct": pct,
                "hit": current is not None and current >= target,
            }
        )
    return out


# ---------- règles de décision (déterministes) ----------

def decisions(finance: dict, metrics: dict, ci: dict, okrs: list[dict], pipeline: dict) -> list[str]:
    out: list[str] = []
    runway = finance.get("runway_months")
    if runway is not None and runway < 3:
        out.append(
            "Runway critique (< 3 mois) : priorité absolue revenus — lancer les "
            "interviews R2 vers des clients payants avant toute nouvelle feature"
        )
    if pipeline.get("interviews_7d", 0) == 0:
        out.append("Pipeline vide cette semaine : planifier au moins 1 interview Mom Test (R2)")
    for o in okrs:
        if o["current"] is not None and not o["hit"] and (o["pct"] or 0) < 50:
            out.append(f"OKR '{o['label']}' sous 50% ({o['current']}/{o['target']}) : plan d'action cette semaine")
    avg = (metrics.get("averages") or {}).get("velocity_per_week") or 0
    if avg < 1:
        out.append("Vélocité moyenne < 1 commit/semaine : choisir UN projet focus et livrer")
    if ci and ci.get("failures"):
        out.append(f"CI : {ci['failures']} check(s) en échec — le guardian diagnostique, corrige la cause racine")
    return out


# ---------- rendu ----------

def build_payload() -> dict[str, Any]:
    strategy = _load(STRATEGY_FILE)
    finance = collect_finance()
    metrics = collect_metrics()
    ci = collect_ci()
    pipeline = collect_pipeline()
    okrs = okr_progress(strategy.get("objectives", []) or [], finance, metrics, pipeline)
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "finance": {
            "cash": finance.get("starting_cash"),
            "burn": finance.get("burn_rate_monthly"),
            "mrr": finance.get("mrr_monthly"),
            "runway_label": finance.get("runway_label"),
            "status": finance.get("status"),
        },
        "execution": {
            "velocity": (metrics.get("averages") or {}).get("velocity_per_week"),
            "lead_time": (metrics.get("averages") or {}).get("lead_time_days"),
            "ci": ci,
        },
        "okr": okrs,
        "pipeline": {
            "total": pipeline.get("total", 0),
            "interviews_7d": pipeline.get("interviews_7d", 0),
            "last_insight": (pipeline.get("last") or {}).get("insight"),
            "next_steps": [e.get("next_step") for e in pipeline.get("next_steps", []) if e.get("next_step")],
        },
        "decisions": decisions(finance, metrics, ci, okrs, pipeline),
    }


def render(payload: dict[str, Any]) -> str:
    f, ex = payload["finance"], payload["execution"]
    cur = "USD"
    lines = [
        f"DIGEST STRATÉGIQUE — {payload['generated_at'][:10]}",
        f"  Finance  : caisse {f['cash']} {cur} · burn {f['burn']} · MRR {f['mrr']} · runway {f['runway_label']}",
        f"  Exécution: vélocité {ex['velocity']} c/sem · lead time {ex['lead_time']} j"
        f" · CI {ex['ci'].get('total', 0) - ex['ci'].get('failures', 0)}/{ex['ci'].get('total', 0)} vert",
        "  OKR:",
    ]
    for o in payload["okr"]:
        cur_s = "—" if o["current"] is None else o["current"]
        mark = "✓" if o["hit"] else "✗"
        pct_s = f" ({o['pct']}%)" if o["pct"] is not None else ""
        lines.append(f"    {mark} {o['label']}: {cur_s}/{o['target']}{pct_s}")
    p = payload["pipeline"]
    lines.append(f"  Pipeline : {p['total']} entrée(s) · {p['interviews_7d']} interview(s) 7j")
    if p["last_insight"]:
        lines.append(f"    Dernière insight : {p['last_insight']}")
    for ns in p["next_steps"]:
        lines.append(f"    Prochain pas : {ns}")
    if payload["decisions"]:
        lines.append("  Décisions à prendre :")
        lines += [f"    → {d}" for d in payload["decisions"]]
    else:
        lines.append("  Aucune décision urgente — tout est dans les clous.")
    return "\n".join(lines)


def post_discord(text: str) -> bool:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    if not url:
        return False
    try:
        import urllib.request

        data = json.dumps({"content": f"```\n{text}\n```"}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=30)
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Digest stratégique Kuro")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--discord", action="store_true", help="poster le digest sur Discord si webhook présent")
    parser.add_argument("--out", type=Path, help="écrire le digest dans un fichier")
    args = parser.parse_args()

    payload = build_payload()
    text = render(payload)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else text)
    if args.discord:
        ok = post_discord(text)
        print(f"[{'+' if ok else '!'}] Discord: {'posté' if ok else 'webhook absent ou échec'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
