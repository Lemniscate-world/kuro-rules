#!/usr/bin/env python3
"""agents.py — agents OpenClaw + leurs taches (crons), lecture seule.

Source : CLI `openclaw` (JSON natif : `agents list --json`,
`cron list --json`). Absent ou en panne -> mention honnete, jamais
d exception. Cache 60 s (un appel CLI coute ~1 s, pas a chaque frame).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Any

AGENTS_TTL_SECONDS = 60
_AGENTS_CACHE: dict[str, Any] = {"ts": 0.0, "lines": []}


# NOTE: ne PAS descendre sous 10 s (R116) : la gateway locale met
# ~7 s a repondre (resolution modeles), un timeout plus court rend
# toute la section AGENTS faussement "indisponible" en permanence.
OPENCLAW_TIMEOUT_SECONDS = 12


def _openclaw_json(*args: str) -> Any | None:
    exe = shutil.which("openclaw")
    if not exe:
        return None
    try:
        done = subprocess.run([exe, *args, "--json"], capture_output=True,
                              text=True, timeout=OPENCLAW_TIMEOUT_SECONDS,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if done.returncode != 0:
            return None
        # La gateway OpenClaw flappe : `agents list` rend parfois [] avec
        # exit 0 mais "gateway connect failed / unauthorized" sur stderr.
        # Sans ce garde, le TUI affichait "agents : aucun" une frame sur deux.
        err = (done.stderr or "").strip().lower()
        if err and ("gateway" in err or "unauthorized" in err
                   or "failed" in err):
            return None
        return json.loads(done.stdout or "null")
    except Exception:
        return None


def _rel(ms: Any, now_ms: float) -> str:
    """'dans 10 min' / 'il y a 12 min' / 'jamais' depuis epoch-ms."""
    try:
        target = float(ms)
    except (TypeError, ValueError):
        return "jamais"
    delta_min = (target - now_ms) / 60000
    if abs(delta_min) < 1:
        return "maintenant"
    if delta_min > 0:
        when, unit = (delta_min, "min") if delta_min < 120 else (
            (delta_min / 60, "h") if delta_min < 2880 else (delta_min / 1440, "j"))
        return f"dans {when:.0f} {unit}"
    ago = -delta_min
    when, unit = (ago, "min") if ago < 120 else (
        (ago / 60, "h") if ago < 2880 else (ago / 1440, "j"))
    return f"il y a {when:.0f} {unit}"


def _short_model(model: Any) -> str:
    if not model:
        return "?"
    try:
        return str(model).split("@")[0].split("/")[-1] or "?"
    except Exception:
        return "?"


def _is_problem(job: dict) -> bool:
    if job.get("enabled") is False:
        return True
    status = str(job.get("state", {}).get("lastRunStatus", "")
                 or job.get("state", {}).get("lastStatus", "") or "ok")
    return not status.lower().startswith("ok") and status.lower() != "idle"


def collect_agents() -> dict[str, Any]:
    """{"present", "agents", "crons", "agents_ok", "crons_ok"} (jamais d exception).

    Les deux appels CLI partent en parallele (la 1re frame bloquait jusqu'a
    16 s en serie quand la gateway OpenClaw rame). agents_ok/crons_ok
    distinguent "liste vide" de "appel echoue" : afficher "aucun" sur un
    timeout mentait une frame sur deux.
    """
    if shutil.which("openclaw") is None:
        return {"present": False, "agents": [], "crons": [],
                "agents_ok": False, "crons_ok": False}
    try:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_agents = pool.submit(_openclaw_json, "agents", "list")
            fut_cron = pool.submit(_openclaw_json, "cron", "list")
            agents_raw = fut_agents.result()
            cron_raw = fut_cron.result()
        agents_ok = agents_raw is not None
        crons_ok = cron_raw is not None
        if not agents_ok:
            agents_raw = []
        if not crons_ok:
            cron_raw = {}
        if not isinstance(agents_raw, list):
            agents_raw = []
            agents_ok = False
        if not isinstance(cron_raw, dict):
            cron_raw = {}
            crons_ok = False
        jobs = cron_raw.get("jobs", [])
        if not isinstance(jobs, list):
            jobs = []
            crons_ok = False
    except Exception:
        return {"present": False, "agents": [], "crons": [],
                "agents_ok": False, "crons_ok": False}
    now_ms = time.time() * 1000
    agents = []
    for agent in agents_raw if isinstance(agents_raw, list) else []:
        if not isinstance(agent, dict):
            continue
        agents.append({"id": str(agent.get("id", "?")),
                       "name": str(agent.get("identityName")
                                   or agent.get("name", "?")),
                       "model": _short_model(agent.get("model"))})
    rows = []
    for job in jobs if isinstance(jobs, list) else []:
        if not isinstance(job, dict):
            continue
        state = job.get("state", {}) if isinstance(job.get("state"), dict) else {}
        rows.append({"name": str(job.get("name") or job.get("id", "?"))[:40],
                     "agent": str(job.get("agentId", "?")),
                     "next": _rel(state.get("nextRunAtMs"), now_ms),
                     "last": _rel(state.get("lastRunAtMs"), now_ms),
                     "status": str(state.get("lastRunStatus")
                                   or state.get("lastStatus") or "?")[:24],
                     "bad": _is_problem(job)})
    rows.sort(key=lambda r: (not r["bad"], r["name"]))
    return {"present": True, "agents": agents, "crons": rows[:8],
            "agents_ok": agents_ok, "crons_ok": crons_ok}


def agents_lines() -> list[str]:
    """Lignes TUI (cache 60 s)."""
    now = time.monotonic()
    cached = _AGENTS_CACHE.get("lines") or []
    if cached and now - float(_AGENTS_CACHE.get("ts", 0.0)) < AGENTS_TTL_SECONDS:
        return list(cached)
    data = collect_agents()
    if not data["present"]:
        lines = ["agents : openclaw indisponible ici (voir serveur)"]
    else:
        agents = data["agents"]
        if not data.get("agents_ok", True):
            head = "agents : (liste indisponible, gateway OpenClaw injoignable)"
        else:
            head = "agents : " + (", ".join(
                f"{a['id']} ({a['name']}, {a['model']})" for a in agents) or "aucun")
        lines = [head, "taches :"]
        for row in data["crons"]:
            mark = "!" if row["bad"] else " "
            lines.append(f" {mark} {row['name'][:34]:<34} "
                         f"{row['next']:<14} {row['status']}")
        if not data["crons"]:
            lines.append("  (taches indisponibles, gateway injoignable)"
                         if not data.get("crons_ok", True) else "  aucune tache")
    _AGENTS_CACHE["ts"] = time.monotonic()
    _AGENTS_CACHE["lines"] = lines
    return list(lines)
