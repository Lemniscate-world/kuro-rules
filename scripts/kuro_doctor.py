#!/usr/bin/env python3
"""kuro_doctor.py — vérification de santé complète de l'intelligence Kuro.

Une seule commande qui teste tous les composants et dit la vérité :
    python scripts/kuro_doctor.py [--fix]

--fix : tente les réparations sûres (démarrer l'API, lancer un scan daemon, backup DB).
"""

import json
import os
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
KURO_ROOT = Path(__file__).resolve().parent.parent
DB = HOME / ".kuro" / "kuro.db"
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    mark = "OK  " if ok else "FAIL"
    print(f"[{mark}] {name:<22} {detail}")


def age_minutes(ts_text):
    try:
        dt = datetime.strptime(str(ts_text)[:19], "%Y-%m-%d %H:%M:%S")
        return (datetime.now() - dt).total_seconds() / 60
    except Exception:
        return None


def main(fix=False):
    print("=== KURO DOCTOR ===\n")

    # 1. Daemon local
    hb_age = proj_n = alert_n = None
    if DB.exists():
        try:
            conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
            row = conn.execute(
                "SELECT timestamp, projects_scanned, alerts_active FROM heartbeat "
                "ORDER BY timestamp DESC LIMIT 1").fetchone()
            conn.close()
            if row:
                hb_age = age_minutes(row[0])
                proj_n, alert_n = row[1], row[2]
        except Exception:
            pass
    daemon_ok = hb_age is not None and hb_age < 120
    check("Daemon local", daemon_ok,
          f"heartbeat il y a {hb_age:.0f} min · {proj_n} projets · {alert_n} alertes"
          if hb_age is not None else "aucun heartbeat — daemon non démarré")

    # 2. API locale
    api_ok, engine, repos_n = False, None, 0
    try:
        data = json.loads(urllib.request.urlopen(
            "http://127.0.0.1:8767/api/robot?ts=" + str(os.getpid()), timeout=5).read())
        engine = data.get("llm_engine")
        repos_n = len(data.get("repos") or [])
        api_ok = True
    except Exception:
        pass
    check("API locale 8767", api_ok,
          f"cerveau: {engine or 'n/a'} · {repos_n} repos suivis" if api_ok
          else "injoignable — lance .\\run-api.ps1 ou utilise --fix")

    # 3. App desktop
    exe = HOME / "AppData" / "Local" / "KuroPulse" / "KuroPulse.exe"
    installed = exe.exists()
    running = False
    try:
        # tasklist/WMI sont corrompus sur cette machine -> passer par PowerShell
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "if (Get-Process KuroPulse -ErrorAction SilentlyContinue) { 'RUNNING' } else { 'NO' }"],
            capture_output=True, text=True, timeout=60)
        running = "RUNNING" in out.stdout
    except Exception:
        pass
    log_err = "ERREUR FATALE" in (exe.parent / "last-run.log").read_text(encoding="utf-8",
               errors="replace") if (exe.parent / "last-run.log").exists() else True
    app_ok = installed and running and not log_err
    check("App KuroPulse", app_ok,
          "installée et en marche" if app_ok else
          f"installée={installed} en_marche={running}")

    # 4. Robot distant
    try:
        gh = subprocess.run(
            ["gh", "run", "list", "--repo", "Lemniscate-world/kuro-rules",
             "--workflow", "kuro.yml", "--limit", "1", "--json", "conclusion"],
            capture_output=True, text=True, timeout=30)
        concl = json.loads(gh.stdout)[0].get("conclusion")
    except Exception as e:
        concl = f"erreur gh ({e})"
    robot_ok = concl == "success"
    check("Robot distant", robot_ok, f"dernier run kuro.yml: {concl}")

    # 5. Secrets
    try:
        secrets = subprocess.run(
            ["gh", "secret", "list", "--repo", "Lemniscate-world/kuro-rules"],
            capture_output=True, text=True, timeout=30).stdout
        needed = ["PORTFOLIO_SYNC_TOKEN", "OPENROUTER_API_KEY", "DISCORD_WEBHOOK_URL"]
        missing = [s for s in needed if s not in secrets]
    except Exception:
        missing = ["vérification impossible"]
    check("Secrets GitHub", not missing,
          "les 3 posés" if not missing else f"manquants: {', '.join(missing)}")

    # 6. Cerveau LLM
    sys.path.insert(0, str(KURO_ROOT / "scripts"))
    try:
        from kuro_llm import available
        engine_name = available()
    except Exception:
        engine_name = None
    check("Cerveau LLM", engine_name is not None,
          f"moteur: {engine_name}" if engine_name else "aucun moteur — mode déterministe")

    # 7. Tests
    try:
        r = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                           cwd=str(KURO_ROOT), capture_output=True, text=True, timeout=180)
        last = [l for l in r.stdout.splitlines() if l.strip()][-1] if r.stdout else ""
        tests_ok = r.returncode == 0
    except Exception as e:
        last, tests_ok = str(e), False
    check("Tests", tests_ok, last[:60])

    # 8. Backup DB
    bdir = KURO_ROOT / "SYNC_BACKUPS" / "kuro-db"
    backups = sorted(bdir.glob("kuro-*.db")) if bdir.exists() else []
    latest = backups[-1] if backups else None
    backup_ok = latest is not None and \
        (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() < 48 * 3600
    check("Backup DB", backup_ok,
          latest.name if latest else "aucun — lance scripts/kuro_db_backup.ps1")

    # 9. Auto-start login
    startup = HOME / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
    entries = {
        "KuroDaemon": (startup / "KuroDaemon.bat").exists(),
        "KuroPulse": (startup / "KuroPulse.lnk").exists(),
    }
    check("Auto-start login", all(entries.values()),
          ", ".join(k for k, v in entries.items() if v) or "aucun")

    # verdict
    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\nVERDICT: {len(RESULTS) - len(fails)}/{len(RESULTS)} composants OK"
          + (f" — problèmes: {', '.join(fails)}" if fails else " — système sain"))

    if fix:
        apply_fixes(fails)

    return 0 if not fails else 1


def apply_fixes(fails):
    print("\n--- RÉPARATIONS (--fix) ---")
    if "API locale 8767" in fails:
        subprocess.Popen(["pythonw", str(KURO_ROOT / "scripts" / "kuro_api.py"),
                          "--port", "8767"], creationflags=0x08000000)
        print("[FIX] API relancée en arrière-plan")
    if "Backup DB" in fails:
        subprocess.run(["powershell", "-ExecutionPolicy", "Bypass",
                        "-File", str(KURO_ROOT / "scripts" / "kuro_db_backup.ps1")])
        print("[FIX] backup exécuté")
    if "Robot distant" in fails:
        os.system("gh workflow run kuro.yml --repo Lemniscate-world/kuro-rules")
        print("[FIX] cycle robot déclenché")


if __name__ == "__main__":
    sys.exit(main("--fix" in sys.argv))
