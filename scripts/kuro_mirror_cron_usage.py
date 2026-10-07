#!/usr/bin/env python3
"""kuro_mirror_cron_usage.py — l activite LLM de la gateway OpenClaw vers le journal Xenon.

Constat : sur le serveur, 100 % des appels LLM passent par la gateway
OpenClaw (crons), jamais par kuro_llm.ask(). Resultat : section cerveau
figee sur "inconnu", jambes sans historique. Ce script recopie les runs
REUSSIS recents (48 h) dans ~/.kuro/llm_usage.jsonl, sans depenser un token :
moteur/latence reels, cout null (inconnu, jamais $0 menteur), source marquee.

Idempotent : cle session job_id:lastRunAtMs, runs deja miroites sautes.
Zero dependance (stdlib), jamais d exception levee.

Usage:
    python scripts/kuro_mirror_cron_usage.py [--json] [--hours 48]
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

USAGE_FILE = Path.home() / ".kuro" / "llm_usage.jsonl"
BRAIN_FILE = Path.home() / ".kuro" / "llm_last.json"
MAX_LINES = 2000
DEFAULT_WINDOW_HOURS = 48


def _openclaw_json(*args: str):
    """JSON d openclaw (None si absent/en panne). Jamais d exception."""
    if shutil.which("openclaw") is None:
        return None
    try:
        done = subprocess.run(
            ["openclaw", *args, "--json"], capture_output=True, text=True,
            timeout=60, encoding="utf-8", errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if done.returncode != 0 or not done.stdout.strip():
            return None
        return json.loads(done.stdout)
    except Exception:
        return None


def _leg_and_model(model: str) -> tuple[str, str]:
    """(jambe kuro, modele complet) depuis 'deepseek/x@setup' ou 'openrouter/y'."""
    full = str(model or "").split("@")[0]
    leg = (full.split("/")[0] or "?").split(":")[0] or "?"
    return leg, full


def collect_recent_runs(window_hours: int = DEFAULT_WINDOW_HOURS) -> list[dict]:
    """Runs cron reussis recents : [{session, at, engine, model, latency_s}]."""
    out: list[dict] = []
    try:
        cutoff = (datetime.now(timezone.utc)
                  - timedelta(hours=window_hours)).timestamp() * 1000
    except Exception:
        return out
    agents_raw = _openclaw_json("agents", "list") or []
    models = {}
    try:
        for a in agents_raw if isinstance(agents_raw, list) else []:
            if isinstance(a, dict):
                models[str(a.get("id", "?"))] = str(a.get("model") or "")
    except Exception:
        pass
    cron_raw = _openclaw_json("cron", "list") or {}
    jobs = cron_raw.get("jobs", []) if isinstance(cron_raw, dict) else []
    for job in jobs if isinstance(jobs, list) else []:
        try:
            if not isinstance(job, dict):
                continue
            st = job.get("state", {})
            if not isinstance(st, dict) or st.get("lastRunStatus") != "ok":
                continue
            ts = st.get("lastRunAtMs")
            if not isinstance(ts, (int, float)) or ts < cutoff:
                continue
            dur = st.get("lastDurationMs") or 0
            try:
                latency = round(float(dur) / 1000, 1)
            except Exception:
                latency = 0.0
            model = models.get(str(job.get("agentId", "?")), "")
            leg, full = _leg_and_model(model)
            at = datetime.fromtimestamp(ts / 1000).astimezone()
            out.append({"session": f"{job.get('id', '?')}:{int(ts)}",
                        "name": str(job.get("name", "?"))[:40],
                        "at": at.strftime("%Y-%m-%d %H:%M:%S"),
                        "day": at.strftime("%Y-%m-%d"),
                        "engine": leg, "model": full, "latency_s": latency})
        except Exception:
            continue
    return out


def mirrored_sessions() -> set[str]:
    """Sessions deja dans le journal (champ session). Jamais d exception."""
    found: set[str] = set()
    try:
        if not USAGE_FILE.exists():
            return found
        for line in USAGE_FILE.read_text(encoding="utf-8").splitlines()[-MAX_LINES:]:
            try:
                entry = json.loads(line)
            except Exception:
                continue
            if isinstance(entry, dict) and entry.get("session"):
                found.add(str(entry["session"]))
    except Exception:
        pass
    return found


def _brain_at() -> str:
    """Horodatage du dernier cerveau connu ("" si absent)."""
    try:
        if not BRAIN_FILE.exists():
            return ""
        data = json.loads(BRAIN_FILE.read_text(encoding="utf-8"))
        return str(data.get("at") or "") if isinstance(data, dict) else ""
    except Exception:
        return ""


def mirror(window_hours: int = DEFAULT_WINDOW_HOURS) -> dict:
    """Ajoute les runs manquants au journal + rafraichit le dernier cerveau.

    llm_last.json n est ecrase que si le run miroite est PLUS RECENT
    (jamais de retour en arriere sur un vrai appel kuro_llm).
    Retourne le bilan.
    """
    runs = collect_recent_runs(window_hours)
    known = mirrored_sessions()
    added = 0
    fresh = [r for r in runs if r["session"] not in known]
    try:
        USAGE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if fresh:
            with USAGE_FILE.open("a", encoding="utf-8") as fh:
                for r in fresh:
                    fh.write(json.dumps({
                        "day": r["day"], "at": r["at"], "engine": r["engine"],
                        "model": r["model"], "latency_s": r["latency_s"],
                        "prompt_chars": 0, "resp_chars": 0, "tokens": 0,
                        "tokens_reels": False, "legs": [[r["engine"], "ok"]],
                        "est_cost_usd": None, "source": "openclaw-cron",
                        "session": r["session"]}) + "\n")
                    added += 1
            try:
                lines = USAGE_FILE.read_text(encoding="utf-8").splitlines()
                if len(lines) > MAX_LINES:
                    USAGE_FILE.write_text("\n".join(lines[-MAX_LINES:]) + "\n",
                                          encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass
    try:
        if runs:
            newest = max(runs, key=lambda r: (r["day"], r["at"]))
            if newest["at"] > _brain_at():
                BRAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
                BRAIN_FILE.write_text(json.dumps({
                    "engine": newest["engine"], "model": newest["model"],
                    "latency_s": newest["latency_s"], "at": newest["at"],
                    "via": "openclaw-cron"}), encoding="utf-8")
    except Exception:
        pass
    return {"runs_seen": len(runs), "added": added,
            "names": sorted({r["name"] for r in runs})}


def main() -> int:
    ap = argparse.ArgumentParser(description="Miroir activite cron OpenClaw -> journal LLM")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--hours", type=int, default=DEFAULT_WINDOW_HOURS)
    args = ap.parse_args()
    report = mirror(window_hours=args.hours)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"miroir : {report['added']} ajoutes / {report['runs_seen']} runs "
              f"({', '.join(report['names']) or 'aucun'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
