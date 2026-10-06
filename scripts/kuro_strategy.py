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
DOCS_DIR = ROOT_DIR.parent


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


# ---------- conformite des plans (R12/R13b : le plan d'abord, sinon aveugle) ----------

def plan_compliance(docs_dir: Path | None = None) -> dict[str, Any]:
    """Scanne les repos git : PLAN.md present ? sous-plan *_2ANS.md present ?

    Retourne {total, sans_plan: [...], actifs_sans_cap: [...]}.
    actifs_sans_cap = repos avec PLAN.md mais sans *_2ANS.md ET velocite > 0
    (on ne demande un cap 2 ans qu'a ce qui bouge vraiment).
    """
    root = docs_dir or DOCS_DIR
    sans_plan: list[str] = []
    avec_plan: list[str] = []
    sans_sousplan: list[str] = []
    try:
        children = sorted([c for c in root.iterdir() if c.is_dir()], key=lambda c: c.name.lower())
    except OSError:
        return {"total": 0, "sans_plan": [], "actifs_sans_cap": []}
    for child in children:
        if not (child / ".git").exists():
            continue
        if child.resolve() == ROOT_DIR.resolve():
            continue  # kuro-rules n'est pas un projet livrable
        has_plan = (child / "PLAN.md").exists() or (child / "docs" / "PLAN.md").exists()
        if not has_plan:
            sans_plan.append(child.name)
            continue
        avec_plan.append(child.name)
        has_cap = (len(list(child.glob("PLAN_*_2ANS.md")) + list((child / "docs").glob("PLAN_*_2ANS.md"))
                       if (child / "docs").exists() else list(child.glob("PLAN_*_2ANS.md"))) > 0)
        if not has_cap:
            sans_sousplan.append(child.name)
    # Ne reclamer un cap 2 ans que pour les repos actifs (velocite > 0).
    actifs_sans_cap: list[str] = []
    if sans_sousplan:
        try:
            import kuro_metrics
            payload = kuro_metrics.build_payload()
            vel = {str(p.get("name", "")).lower(): float(p.get("velocity_per_week") or 0)
                   for p in payload.get("projects", [])}
        except Exception:
            vel = {}
        actifs_sans_cap = [n for n in sans_sousplan if vel.get(n.lower(), 0) > 0]
    return {"total": len(sans_plan) + len(avec_plan),
            "sans_plan": sorted(sans_plan, key=str.lower),
            "actifs_sans_cap": sorted(actifs_sans_cap, key=str.lower)}


def campaign(metrics: dict, okrs: list[dict], pipeline: dict, plans: dict | None = None) -> dict[str, str]:
    """Section Campagne (grande strategie) : guerre / bataille / arene + gate necessite.

    Deterministe : chaque ligne derive d'un fait mesure. La bataille qui ne
    prepare rien et dont la necessite n'est pas demontree ne part pas.
    """
    plans = plans or {}
    # Guerre = l'OKR le plus en retard, sinon le premier non atteint.
    guerre = "aucun OKR defini — definir la guerre avant les batailles"
    worst = [o for o in okrs if not o.get("hit") and o.get("current") is not None]
    if worst:
        worst.sort(key=lambda o: (o.get("pct") if o.get("pct") is not None else 101))
        w = worst[0]
        guerre = f"{w['label']} ({w['current']}/{w['target']})"
    # Bataille = repo le plus rapide, avec gate de necessite.
    bataille = "aucune donnee de velocite"
    gate_n = "necessite non demontree — ne pas lancer"
    gate_c = "consequences : +maintenance, +surface CI, -focus ailleurs"
    projects = (metrics.get("projects") or []) if isinstance(metrics, dict) else []
    if projects:
        top = max(projects, key=lambda p: float(p.get("velocity_per_week") or 0))
        bataille = (f"{top.get('name')} ({top.get('velocity_per_week')} c/sem) "
                     f"prepare : livrer vert puis attaquer l'OKR « {guerre} »")
        if int(top.get("ci_failures") or 0) > 0:
            gate_n = f"necessaire : {top.get('ci_failures')} check(s) CI en echec — reparer d'abord"
        elif worst:
            gate_n = f"necessaire : OKR « {w['label']} » sous les 50% — la bataille sert la guerre"
        elif float((metrics.get("averages") or {}).get("velocity_per_week") or 0) < 1:
            gate_n = "necessaire : velocite moyenne < 1 c/sem — debloquer un front unique"
        gate_c = (f"consequences : 2h bornees, 0 breaking change cross-repo (R105), "
                  f"SESSION_SUMMARY prepend (R42) — sinon la bataille coute plus qu'elle ne rapporte")
    # Arene ignoree = ce que le code ne voit pas : signaux dehors ou pivots endormis.
    pivots = metrics.get("pivot_candidates") or [] if isinstance(metrics, dict) else []
    last_insight = (pipeline.get("last") or {}).get("insight") if isinstance(pipeline, dict) else None
    if last_insight:
        arene = f"insight pipeline : {last_insight}"
    elif pivots:
        arene = f"{len(pivots)} candidat(s) pivot endormis — 1 signal Radar a reconvertir avant d'ouvrir un front"
    else:
        arene = "aucun signal dehors — lancer 1 ecoute Radar (R69) avant d'ouvrir un front"
    if (plans.get("sans_plan") or []):
        arene += f" · {len(plans['sans_plan'])} repos sans PLAN.md : pas de bataille sans carte"
    return {"guerre": guerre, "bataille": bataille, "arene": arene,
            "gate_necessite": gate_n, "gate_consequences": gate_c}


# ---------- règles de décision (déterministes) ----------

def keyed_decisions(finance: dict, metrics: dict, ci: dict, okrs: list[dict], pipeline: dict,
                    plans: dict | None = None) -> list[tuple[str, str]]:
    """Mêmes règles que decisions(), avec une clé stable par règle (suivi NEW/OPEN/RESOLVED)."""
    out: list[tuple[str, str]] = []
    runway = finance.get("runway_months")
    if runway is not None and runway < 3:
        out.append((
            "runway",
            "Runway critique (< 3 mois) : priorité absolue revenus — lancer les "
            "interviews R2 vers des clients payants avant toute nouvelle feature",
        ))
    if pipeline.get("interviews_7d", 0) == 0:
        out.append(("pipeline_empty", "Pipeline vide cette semaine : planifier au moins 1 interview Mom Test (R2)"))
    for o in okrs:
        if o["current"] is not None and not o["hit"] and (o["pct"] or 0) < 50:
            out.append((f"okr:{o['key']}",
                        f"OKR '{o['label']}' sous 50% ({o['current']}/{o['target']}) : plan d'action cette semaine"))
    avg = (metrics.get("averages") or {}).get("velocity_per_week") or 0
    if avg < 1:
        out.append(("velocity", "Vélocité moyenne < 1 commit/semaine : choisir UN projet focus et livrer"))
    if ci and ci.get("failures"):
        out.append(("ci", f"CI : {ci['failures']} check(s) en échec — le guardian diagnostique, corrige la cause racine"))
    plans = plans or {}
    sans_plan = plans.get("sans_plan") or []
    if sans_plan:
        top = ", ".join(sans_plan[:5]) + ("…" if len(sans_plan) > 5 else "")
        out.append(("plans", f"Plans : {len(sans_plan)} repos sans PLAN.md ({top}) — ecrire la carte avant le pick, sinon le worker tourne aveugle (R12)"))
    sans_cap = plans.get("actifs_sans_cap") or []
    if sans_cap:
        top = ", ".join(sans_cap[:5]) + ("…" if len(sans_cap) > 5 else "")
        out.append(("caps", f"Caps 2 ans : {len(sans_cap)} repos actifs sans sous-plan ({top}) — 1 sous-plan docs/PLAN_<X>_2ANS.md par front actif (R13b)"))
    return out


def decisions(finance: dict, metrics: dict, ci: dict, okrs: list[dict], pipeline: dict,
              plans: dict | None = None) -> list[str]:
    return [text for _, text in keyed_decisions(finance, metrics, ci, okrs, pipeline, plans)]


DECISIONS_FILE = ROOT_DIR / "strategy_decisions.local.json"  # local, gitigné (R111/R113)
RESOLVED_KEEP_DAYS = 30
RESOLVED_SHOW_DAYS = 7


def _load_store() -> dict:
    try:
        store = json.loads(DECISIONS_FILE.read_text(encoding="utf-8"))
        return store if isinstance(store, dict) else {}
    except Exception:
        return {}


def _save_store(store: dict) -> None:
    try:
        DECISIONS_FILE.write_text(json.dumps(store, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def _days_between(a: str, b: str) -> int:
    from datetime import date as _date
    try:
        return (_date.fromisoformat(a) - _date.fromisoformat(b)).days
    except ValueError:
        return 0


def _mark_opened(store: dict, keyed: list[tuple[str, str]], today: str) -> list[dict]:
    opened: list[dict] = []
    for key, text in keyed:
        prev = store.get(key, {})
        if prev.get("status") == "RESOLVED":
            prev = {}  # reouverte : repart en NEW
        first = prev.get("first_seen", today)
        store[key] = {"first_seen": first, "last_seen": today, "text": text,
                      "status": "OPEN", "resolved_at": None}
        opened.append({"key": key, "text": text,
                       "status": "NEW" if first == today else "OPEN",
                       "age_days": _days_between(today, first), "first_seen": first})
    return opened


def _mark_resolved(store: dict, current: set[str], today: str) -> list[dict]:
    resolved: list[dict] = []
    for key in list(store):
        entry = store[key]
        if key in current or not isinstance(entry, dict):
            continue
        if entry.get("status") != "RESOLVED":
            entry["status"] = "RESOLVED"
            entry["resolved_at"] = today
        gone = _days_between(today, entry.get("resolved_at") or today)
        if gone > RESOLVED_KEEP_DAYS:
            del store[key]
            continue
        if gone <= RESOLVED_SHOW_DAYS:
            resolved.append({"key": key, "text": entry.get("text", key), "status": "RESOLVED",
                             "age_days": _days_between(entry.get("resolved_at") or today,
                                                       entry.get("first_seen", today)),
                             "resolved_at": entry.get("resolved_at")})
    return resolved


def track_decisions(keyed: list[tuple[str, str]]) -> tuple[list[dict], list[dict]]:
    """Persiste l'état des décisions. Retourne (ouvertes, résolues_récentes).

    Statuts : NEW (first_seen == aujourd'hui), OPEN (toujours vraie, age en jours),
    RESOLVED (a disparu -> action appliquée ou condition retombée).
    """
    from datetime import date as _date
    today = _date.today().isoformat()
    store = _load_store()
    opened = _mark_opened(store, keyed, today)
    resolved = _mark_resolved(store, dict(keyed).keys(), today)
    _save_store(store)
    return opened, resolved


# ---------- rendu ----------

def build_payload(track: bool = True) -> dict[str, Any]:
    strategy = _load(STRATEGY_FILE)
    finance = collect_finance()
    metrics = collect_metrics()
    ci = collect_ci()
    pipeline = collect_pipeline()
    okrs = okr_progress(strategy.get("objectives", []) or [], finance, metrics, pipeline)
    plans = plan_compliance()
    keyed = keyed_decisions(finance, metrics, ci, okrs, pipeline, plans)
    opened, resolved = track_decisions(keyed) if track else ([{"key": k, "text": t, "status": "OPEN", "age_days": 0} for k, t in keyed], [])
    camp = campaign(metrics, okrs, pipeline, plans)
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
        "decisions": opened,
        "resolved": resolved,
        "plans": plans,
        "campaign": camp,
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
        lines.append(_fmt_okr(o))
    p = payload["pipeline"]
    lines.append(f"  Pipeline : {p['total']} entrée(s) · {p['interviews_7d']} interview(s) 7j")
    if p["last_insight"]:
        lines.append(f"    Dernière insight : {p['last_insight']}")
    for ns in p["next_steps"]:
        lines.append(f"    Prochain pas : {ns}")
    camp = payload.get("campaign") or {}
    if camp:
        lines.append("  Campagne (grande strategie) :")
        lines.append(f"    Guerre   : {camp.get('guerre')}")
        lines.append(f"    Bataille : {camp.get('bataille')}")
        lines.append(f"    Arene ignoree : {camp.get('arene')}")
        lines.append(f"    Gate : {camp.get('gate_necessite')}")
        lines.append(f"           {camp.get('gate_consequences')}")
    pl = payload.get("plans") or {}
    if pl and (pl.get("sans_plan") or pl.get("actifs_sans_cap")):
        lines.append(f"  Plans : {len(pl.get('sans_plan') or [])} sans PLAN.md · "
                     f"{len(pl.get('actifs_sans_cap') or [])} actifs sans cap 2 ans")
    lines.extend(_fmt_decisions(payload.get("decisions") or []))
    lines.extend(_fmt_resolved(payload.get("resolved") or []))
    return "\n".join(lines)


def _fmt_okr(o: dict) -> str:
    cur_s = "—" if o["current"] is None else o["current"]
    mark = "✓" if o["hit"] else "✗"
    pct_s = f" ({o['pct']}%)" if o["pct"] is not None else ""
    return f"    {mark} {o['label']}: {cur_s}/{o['target']}{pct_s}"


def _fmt_decisions(decisions: list) -> list[str]:
    if not decisions:
        return ["  Aucune décision urgente — tout est dans les clous."]
    lines = ["  Décisions à prendre :"]
    for d in decisions:
        if isinstance(d, dict):
            mark = "[NEW]" if d.get("status") == "NEW" else f"[J{d.get('age_days', 0)}]"
            lines.append(f"    → {mark} {d.get('text')}")
        else:
            lines.append(f"    → {d}")
    return lines


def _fmt_resolved(resolved: list) -> list[str]:
    lines = []
    for r in resolved:
        if isinstance(r, dict):
            when = f" (le {r.get('resolved_at')})" if r.get("resolved_at") else ""
            lines.append(f"    ✓ résolue{when} : {r.get('text')}")
        else:
            lines.append(f"    ✓ résolue : {r}")
    return lines


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
