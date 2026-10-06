#!/usr/bin/env python3
"""kuro_supervisor.py — superviseur du daemon Kuro (niveau 1 : restart).

Verifie le heartbeat du daemon dans ~/.kuro/kuro.db et relance le daemon
s'il est stale. Journal persistant hors repo (~/.kuro/supervisor_history.jsonl)
pour detecter les morts repetees et eviter les boucles de restart.

Usage:
    python scripts/kuro_supervisor.py --check        # one-shot (cron / login)
    python scripts/kuro_supervisor.py --check --fix  # + relance si mort

Regles :
- R101 : rien n'est ecrit dans le repo, tout l'etat vit dans ~/.kuro/.
- R93 : sortie ASCII uniquement, chemins via pathlib, pas de /tmp hardcode.
- Cooldown 30 min + max 5 restarts/jour, puis escalade (code retour 2).

Codes retour : 0 sain · 1 relance effectuee · 2 intervention humaine requise.
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
KURO_ROOT = Path(__file__).resolve().parent.parent
DB = HOME / ".kuro" / "kuro.db"
HISTORY = HOME / ".kuro" / "supervisor_history.jsonl"
DAEMON_PY = HOME / "Documents" / "kuro" / "daemon.py"

STALE_MINUTES = 15
COOLDOWN_MINUTES = 30
MAX_RESTARTS_PER_DAY = 5


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def heartbeat_age_minutes(db_path: Path = DB) -> float | None:
    """Age du dernier heartbeat en minutes. None si illisible/absent."""
    if not db_path.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=5)
        row = conn.execute(
            "SELECT timestamp FROM heartbeat ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except Exception:
        return None
    if not row or not row[0]:
        return None
    try:
        ts = datetime.strptime(str(row[0])[:19], "%Y-%m-%d %H:%M:%S")
        # heartbeat ecrit en heure locale par le daemon (datetime('now'))
        age = (datetime.now() - ts).total_seconds() / 60
        return age if age >= 0 else 0.0
    except Exception:
        return None


def load_history(path: Path = HISTORY) -> list[dict]:
    if not path.exists():
        return []
    out = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except Exception:
        pass
    return out


def append_history(event: dict, path: Path = HISTORY) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        event = {"ts": now_utc().isoformat(timespec="seconds"), **event}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def restarts_today(history: list[dict]) -> int:
    today = now_utc().date().isoformat()
    return sum(
        1 for h in history
        if h.get("action") == "restart" and str(h.get("ts", ""))[:10] == today
    )


def minutes_since_last_restart(history: list[dict]) -> float | None:
    latest = None
    for h in history:
        if h.get("action") == "restart" and h.get("ts"):
            try:
                ts = datetime.fromisoformat(str(h["ts"]).replace("Z", "+00:00"))
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if latest is None or ts > latest:
                    latest = ts
            except Exception:
                continue
    if latest is None:
        return None
    return (now_utc() - latest).total_seconds() / 60


def decide(age: float | None, history: list[dict]) -> tuple[str, str]:
    """Decide l'action. Retourne (action, motif).

    actions : healthy | restart | cooldown | escalate | no_db
    """
    if age is None:
        return "no_db", "heartbeat illisible — daemon jamais demarre ou DB absente"
    if age <= STALE_MINUTES:
        return "healthy", f"heartbeat il y a {age:.0f} min"
    since = minutes_since_last_restart(history)
    if since is not None and since < COOLDOWN_MINUTES:
        return "cooldown", f"restart recent il y a {since:.0f} min — attente"
    if restarts_today(history) >= MAX_RESTARTS_PER_DAY:
        return "escalate", (
            f"{MAX_RESTARTS_PER_DAY} restarts aujourd'hui — daemon en boucle, "
            "intervention humaine requise"
        )
    return "restart", f"heartbeat stale depuis {age:.0f} min — relance"


def restart_daemon(daemon_py: Path = DAEMON_PY) -> bool:
    """Relance le daemon en arriere-plan. True si le process a demarre."""
    if not daemon_py.exists():
        return False
    try:
        if os.name == "nt":
            pythonw = Path(sys.executable).with_name("pythonw.exe")
            exe = str(pythonw) if pythonw.exists() else sys.executable
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
            subprocess.Popen([exe, str(daemon_py)], creationflags=flags,
                             close_fds=False)
        else:
            subprocess.Popen([sys.executable, str(daemon_py)],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL,
                             start_new_session=True,
                             close_fds=True)
        return True
    except Exception:
        return False


def main(check: bool = False, fix: bool = False) -> int:
    _ = check  # one-shot dans tous les cas ; kept pour CLI explicite
    age = heartbeat_age_minutes()
    history = load_history()
    action, reason = decide(age, history)
    print(f"[supervisor] action={action} — {reason}")

    if action == "healthy":
        append_history({"action": "check", "result": "healthy",
                        "heartbeat_age_min": round(age or 0, 1)})
        return 0
    if action in ("cooldown", "no_db", "escalate"):
        append_history({"action": "check", "result": action, "reason": reason})
        print("[supervisor] aucune relance (voir motif). "
              "Lance avec --fix pour forcer hors cooldown." if action == "cooldown"
              else "[supervisor] intervention humaine requise.")
        if action == "escalate":
            return 2
        return 2 if action == "no_db" else 0
    # action == restart
    if not fix:
        print("[supervisor] relance non effectuee — ajoute --fix pour relancer.")
        append_history({"action": "check", "result": "restart_pending",
                        "reason": reason})
        return 1
    ok = restart_daemon()
    append_history({"action": "restart", "result": "ok" if ok else "failed",
                    "reason": reason})
    print("[supervisor] daemon relance." if ok
          else "[supervisor] ECHEC de relance — verifie Documents/kuro/daemon.py.")
    return 1 if ok else 2


if __name__ == "__main__":
    args = set(sys.argv[1:])
    sys.exit(main(check="--check" in args or True, fix="--fix" in args))
