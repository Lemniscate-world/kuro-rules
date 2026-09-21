#!/usr/bin/env python3
"""cowork_pick.py — Oracle coworking : choisit le 2e repo par analyses, poste sur Discord.

Sources 100 % locales (zero dependance) :
  - scripts/kuro_metrics.py : velocity_per_week, CI, last_commit
  - ~/.kuro/kuro.db : progress_pct, status, alertes ouvertes + types (si dispo)
  - coverage.local.json : trous de couverture du dernier releve (si dispo)
  - cowork_last_pick.local.json : rotation (jamais 2x de suite)

Score (deterministe, explique) :
  score = min(velocity,10)*2 - ci_failures*3 + progress_pct/20 - alerts_open*2 - days_inactive/10
  Velocite plafonnee (rendements decroissants : 40 c/sem ne vaut pas 8x 5 c/sem),
  doublons probables retires, dernier pick exclu (rotation).

Usage :
    python scripts/cowork_pick.py [--json] [--discord] [--top 5] [--exclude RepoA,RepoB]
    python scripts/cowork_pick.py --window-days 30 --min-commits 5
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
KURO_DB = Path.home() / ".kuro" / "kuro.db"
LAST_PICK_FILE = ROOT / "cowork_last_pick.local.json"
COVERAGE_FILE = ROOT / "coverage.local.json"
VELOCITY_CAP = 10.0  # rendements decroissants : au-dela, la vitesse ne decide plus
ROTATION_DAYS = 2  # le pick recent laisse la place aux autres


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


def score_project(velocity: float = 0.0, ci_failures: int = 0,
                   progress_pct: int | None = None,
                   alerts_open: int = 0,
                   days_inactive: int | None = 0) -> float:
    """Score unique, pur, teste. Plus haut = plus de chances de marcher.

    Velocite plafonnee a VELOCITY_CAP : un repo a 40 c/sem ne doit pas
    ecraser a jamais les autres (rotation +nictwem cap).
    """
    try:
        v = min(float(velocity or 0.0), VELOCITY_CAP)
    except (TypeError, ValueError):
        v = 0.0
    try:
        f = int(ci_failures or 0)
    except (TypeError, ValueError):
        f = 0
    p = progress_pct if isinstance(progress_pct, (int, float)) else 0
    try:
        a = int(alerts_open or 0)
    except (TypeError, ValueError):
        a = 0
    d = days_inactive if isinstance(days_inactive, (int, float)) else 0
    return round(v * 2.0 - f * 3.0 + float(p) / 20.0 - a * 2.0 - float(d) / 10.0, 2)


def load_db_context() -> dict[str, dict]:
    """Lit kuro.db si present. Retourne {nom_lower: {progress, status, alerts, alert_types, days_inactive}}."""
    ctx: dict[str, dict] = {}
    if not KURO_DB.exists():
        return ctx
    try:
        conn = sqlite3.connect(f"file:{KURO_DB}?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        now = datetime.now()
        for r in conn.execute(
            "SELECT name, status, progress_pct, last_activity FROM projects"
        ).fetchall():
            name = str(r["name"] or "")
            days = 0
            try:
                last = datetime.strptime(str(r["last_activity"])[:19], "%Y-%m-%d %H:%M:%S")
                days = max(0, (now - last).days)
            except Exception:
                days = 0
            ctx[name.lower()] = {
                "progress": r["progress_pct"],
                "status": r["status"],
                "days_inactive": days,
                "alerts": 0,
                "alert_types": {},
            }
        try:
            for r in conn.execute(
                "SELECT p.name AS name, a.alert_type AS t, COUNT(*) AS n FROM alerts a "
                "LEFT JOIN projects p ON p.id = a.project_id "
                "WHERE a.acknowledged = 0 GROUP BY p.name, a.alert_type"
            ).fetchall():
                if r["name"]:
                    key = str(r["name"]).lower()
                    entry = ctx.setdefault(key, {"progress": None, "status": None,
                                                 "days_inactive": 0, "alerts": 0,
                                                 "alert_types": {}})
                    entry.setdefault("alert_types", {})[str(r["t"] or "?")] = int(r["n"] or 0)
                    entry["alerts"] = sum(entry["alert_types"].values())
        except sqlite3.Error:
            pass
        conn.close()
    except sqlite3.Error:
        return {}
    return ctx


def fmt_alert_types(types: dict) -> str:
    """'missing_summary x2, inactivity x1' — vide si aucune alerte."""
    if not types:
        return ""
    return ", ".join(f"{t} x{n}" for t, n in sorted(types.items()))


def build_ranking(metrics_payload: dict, db_ctx: dict | None = None,
                  exclude: set[str] | None = None) -> list[dict]:
    """Fusionne metrics + db, score, trie decroissant. Pure, testable."""
    db_ctx = db_ctx or {}
    excluded = {e.lower() for e in (exclude or set())}
    ranked: list[dict] = []
    for p in metrics_payload.get("projects", []):
        name = str(p.get("name") or "")
        if not name or name.lower() in excluded:
            continue
        ctx = db_ctx.get(name.lower(), {})
        progress = ctx.get("progress")
        alerts = int(ctx.get("alerts") or 0)
        days = ctx.get("days_inactive", 0)
        # fallback last_commit -> days_inactive si pas de db
        if not db_ctx and p.get("last_commit_at"):
            try:
                last = datetime.fromisoformat(str(p["last_commit_at"]).replace("Z", "+00:00"))
                now = datetime.now(last.tzinfo) if last.tzinfo else datetime.now()
                days = max(0, (now - last).days)
            except ValueError:
                days = 0
        ci_fail = int(p.get("ci_failures") or 0)
        vel = float(p.get("velocity_per_week") or 0.0)
        score = score_project(velocity=vel, ci_failures=ci_fail,
                              progress_pct=progress, alerts_open=alerts,
                              days_inactive=days)
        ranked.append({
            "name": name,
            "velocity": vel,
            "ci_failures": ci_fail,
            "ci_total": int(p.get("ci_checks_total") or 0),
            "progress": progress,
            "alerts": alerts,
            "alert_types": dict(ctx.get("alert_types") or {}),
            "days_inactive": days,
            "status": ctx.get("status"),
            "last_commit": p.get("last_commit_at"),
            "score": score,
        })
    ranked.sort(key=lambda r: r["score"], reverse=True)
    return drop_duplicates(ranked)


def drop_duplicates(ranked: list[dict]) -> list[dict]:
    """Retire les doublons probables : meme velocite ET meme dernier commit
    = quasi-certainement le meme historique git (ex: Metatron-clean copie de Metatron).
    Le survivant porte la note, le double sort du classement."""
    kept: list[dict] = []
    seen: dict[tuple, str] = {}
    for r in ranked:
        key = (r.get("velocity"), r.get("last_commit"))
        if key[0] and key[1] and key in seen:
            r["note"] = f"doublon probable de {seen[key]} — retire du classement"
            continue
        if key[0] and key[1]:
            seen[key] = r["name"]
        kept.append(r)
    return kept


def load_last_pick() -> dict | None:
    """Dernier pick memorise (rotation). None si jamais ou fichier absent."""
    try:
        data = json.loads(LAST_PICK_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("name"):
            return data
    except Exception:
        pass
    return None


def save_last_pick(name: str) -> None:
    try:
        LAST_PICK_FILE.write_text(
            json.dumps({"name": name,
                        "date": datetime.now().astimezone().isoformat(timespec="seconds")},
                       ensure_ascii=False),
            encoding="utf-8")
    except Exception:
        pass


def apply_rotation(ranking: list[dict]) -> tuple[dict, str]:
    """Jamais 2x de suite : si le gagnant est le pick recent (< ROTATION_DAYS j),
    le second prend sa place. Retourne (pick, note_rotation)."""
    if not ranking:
        raise ValueError("ranking vide")
    last = load_last_pick()
    if not last or len(ranking) < 2:
        return ranking[0], ""
    try:
        last_dt = datetime.fromisoformat(str(last.get("date", "")))
        now = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.now()
        fresh = (now - last_dt).days < ROTATION_DAYS
    except ValueError:
        fresh = False
    if fresh and ranking[0]["name"].lower() == str(last.get("name", "")).lower():
        return ranking[1], f"rotation (hier : {last['name']} — laisse la place)"
    return ranking[0], ""


def load_coverage_gaps(name: str, limit: int = 3) -> list[str]:
    """Trous de couverture du dernier releve pour ce repo ('mod.py 0%')."""
    try:
        data = json.loads(COVERAGE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []
    for entry in data.get("repos", []) if isinstance(data, dict) else []:
        if str(entry.get("name", "")).lower() == name.lower():
            gaps = []
            for f in entry.get("untested", [])[:limit]:
                gaps.append(f"{f.get('path')} ({f.get('pct', 0)}%)")
            return gaps
    return []


def suggest_tasks(pick: dict) -> list[str]:
    """3 next steps deterministes selon signaux : CI, alertes typees, couverture, reprise. Pas d'invention LLM."""
    tasks: list[str] = []
    if int(pick.get("ci_failures") or 0) > 0:
        tasks.append(f"Fix CI ({pick['ci_failures']} checks en echec) puis relance suite verte")
    types = fmt_alert_types(pick.get("alert_types") or {})
    if int(pick.get("alerts") or 0) > 0:
        tasks.append(f"Eteindre {pick['alerts']} alerte(s){(' : ' + types) if types else ''}")
    gaps = load_coverage_gaps(str(pick.get("name", "")))
    if gaps:
        tasks.append("Tests a ajouter : " + "; ".join(gaps))
    elif int(pick.get("ci_failures") or 0) == 0:
        tasks.append("Couverture : lancer `python scripts/kuro_coverage.py --repo "
                     f"{pick.get('name')} --run` puis ecrire les tests manquants")
    if int(pick.get("days_inactive") or 0) > 14:
        tasks.append("Reprise : lire SESSION_SUMMARY + relancer 1 demo qui tourne")
    tasks.append("Maj SESSION_SUMMARY (prepend R42, <=150 mots resume)")
    return tasks[:3]


def necessity_gate(pick: dict) -> tuple[str, str]:
    """Gate 'est-ce necessaire ? quelles consequences ?' (deterministe).

    On ne grab pas par astuce : la bataille part seulement si un fait
    l'exige, et son cout est annonce avant.
    """
    name = pick.get("name", "?")
    types = fmt_alert_types(pick.get("alert_types") or {})
    if int(pick.get("ci_failures") or 0) > 0:
        need = (f"Necessaire : {name} a {pick['ci_failures']} check(s) CI en echec — "
                "reparer avant d'attaquer ailleurs")
    elif int(pick.get("alerts") or 0) > 0:
        need = (f"Necessaire : {pick['alerts']} alerte(s) sur {name}"
                f"{(' (' + types + ')') if types else ''} — "
                "eteindre le feu avant d'ouvrir un front")
    elif int(pick.get("days_inactive") or 0) > 30:
        need = (f"Necessaire : {name} endormi depuis {pick['days_inactive']}j — "
                "reprise ou pivot tranche, pas de statut quo")
    elif float(pick.get("velocity") or 0) >= 1:
        need = (f"Utile mais non critique : {name} avance ({pick['velocity']} c/sem) — "
                "la bataille n'est lancee que si elle prepare l'OKR en retard")
    else:
        need = (f"Non demontre : {name} sans signal (vel {pick.get('velocity')}) — "
                "ne pas grab par astuce, verifier le besoin d'abord")
    cost = ("Consequences : 2h bornees, 0 breaking change cross-repo (R105), "
            "SESSION_SUMMARY prepend (R42) — sinon cout superieur au gain")
    return need, cost


def render_pick(best: dict, ranking: list[dict], top_n: int = 5, rotation_note: str = "") -> str:
    """Texte Discord humain, <=1900 chars. Explique le choix par chiffres."""
    lines = ["COWORK PICK — choix Oracle par analyses (100% local)"]
    lines.append("")
    lines.append(f"Top {min(top_n, len(ranking))} :")
    for r in ranking[:top_n]:
        prog = f"{r['progress']}%" if r["progress"] is not None else "n/a"
        types = fmt_alert_types(r.get("alert_types") or {})
        lines.append(
            f"- {r['name']} : score {r['score']} "
            f"(vel {r['velocity']} c/sem plafonnee a {VELOCITY_CAP}, "
            f"CI {r['ci_failures']}/{r['ci_total']} echec, "
            f"prog {prog}, alertes {r['alerts']}{(' (' + types + ')') if types else ''}, "
            f"inactif {r['days_inactive']}j)"
        )
    lines.append("")
    prog = f"{best['progress']}%" if best.get("progress") is not None else "n/a"
    lines.append(
        f"Pick : {best['name']} — score {best['score']} "
        f"(vel {best['velocity']}, prog {prog}, "
        f"CI {best['ci_failures']} echec, {best['alerts']} alertes)"
    )
    if rotation_note:
        lines.append(rotation_note)
    lines.append("Plan worker (borne, 2h) :")
    for i, t in enumerate(suggest_tasks(best), 1):
        lines.append(f"{i}) {t}")
    need, cost = necessity_gate(best)
    lines.append("Gate : " + need)
    lines.append("       " + cost)
    lines.append("Prochain pick demain 08h00 (rotation auto). "
                 "Pour changer : relance avec --exclude <nom>.")
    text = "\n".join(lines)
    return text[:1900]


def render_velocity(ranking: list[dict], top_n: int = 10) -> str:
    """Vue velocite compacte pour !velocity."""
    if not ranking:
        return "Aucun projet detecte (metrics vide)."
    lines = [f"VELOCITE — {len(ranking)} projets (fenetre 30j) :"]
    for r in ranking[:top_n]:
        lines.append(
            f"- {r['name']:<26} {r['velocity']:>5} c/sem  score {r['score']:>6}  "
            f"CI {r['ci_failures']}/{r['ci_total']}  inactif {r['days_inactive']}j"
        )
    avg = round(sum(r["velocity"] for r in ranking) / len(ranking), 2)
    lines.append(f"Moyenne : {avg} c/sem")
    return "\n".join(lines)[:1900]


def post_discord(text: str) -> bool:
    """Poste sur webhook si present, sinon no-op silencieux. Retourne True si poste."""
    load_dotenv()
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        return False
    try:
        payload = {"username": "Kuro Oracle",
                   "content": f"```\n{text[:1900]}\n```"}
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json",
                     "User-Agent": "Kuro/1.0 (cowork-pick)"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15):
            pass
        return True
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Oracle coworking : pick 2e repo par analyses")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--discord", action="store_true", help="poster le pick sur Discord si webhook present")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--exclude", default="", help="repos separes par virgule (ex: kuro-rules,LifeTrack)")
    ap.add_argument("--window-days", type=int, default=30)
    ap.add_argument("--min-commits", type=int, default=5)
    args = ap.parse_args()

    import kuro_metrics

    payload = kuro_metrics.build_payload(window_days=args.window_days,
                                         min_commits=args.min_commits)
    ctx = load_db_context()
    excluded = {e.strip() for e in args.exclude.split(",") if e.strip()}
    ranking = build_ranking(payload, ctx, excluded)
    if not ranking:
        print(json.dumps({"error": "aucun projet"}, ensure_ascii=False))
        return 1
    best, rotation_note = apply_rotation(ranking)
    text = render_pick(best, ranking, top_n=args.top, rotation_note=rotation_note)
    save_last_pick(best["name"])
    if args.json:
        print(json.dumps({"pick": best, "ranking": ranking[:args.top],
                           "text": text}, indent=2, ensure_ascii=False))
    else:
        print(text)
    if args.discord:
        ok = post_discord(text)
        print("Discord : poste" if ok else "DISCORD_WEBHOOK_URL absent - pick non poste")
    return 0


if __name__ == "__main__":
    sys.exit(main())
