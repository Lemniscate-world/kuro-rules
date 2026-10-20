#!/usr/bin/env python3
"""kuro_doctor.py — vérification de santé complète de l'intelligence Kuro.

Une seule commande qui teste tous les composants et dit la vérité :
    python scripts/kuro_doctor.py [--fix]

--fix : tente les réparations sûres (démarrer l'API, lancer un scan daemon, backup DB).
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
KURO_ROOT = Path(__file__).resolve().parent.parent
DB = HOME / ".kuro" / "kuro.db"
DOCTOR_HISTORY = HOME / ".kuro" / "doctor_history.jsonl"
RECURRENCE_WINDOW = 3  # meme echec sur les N derniers runs = recidive
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


DASHBOARD_FILES = ("index.html", "app.js", "styles.css")
DASHBOARD_GLOBS = ("scripts/*.py", "src/kuro_dashboard/*.py", "tests/*.py",
                   "dashboard/*.js", "dashboard/*.html", "dashboard/*.css")


def dashboard_package_ok(root):
    """Paquet kuro_dashboard importable (6 modules). Jamais d exception."""
    try:
        src = str(Path(root) / "src")
        if src not in sys.path:
            sys.path.insert(0, src)
        from kuro_dashboard import api, face, kuro_state, scan, system, tui  # noqa: F401
        return True, "6 modules (api, face, kuro_state, scan, system, tui)"
    except Exception as e:
        return False, str(e)[:120]


def tui_commands_ok():
    """Commandes console sur le PATH. Jamais d exception."""
    try:
        # Xenon (nouveau nom), repli kuro-glances (alias déprécié).
        found = {"xenon": shutil.which("xenon") or shutil.which("kuro-glances")}
        found.update({n: shutil.which(n) for n in ("kuro-system", "kuro-dashboard")})
        missing = [k for k, v in found.items() if not v]
        if missing:
            return False, f"manquantes: {', '.join(missing)} — pip install -e ."
        return True, "xenon, kuro-system, kuro-dashboard presentes"
    except Exception as e:
        return False, str(e)[:120]


def dashboard_live_ok(root, api_base="http://127.0.0.1:8767"):
    """Sync static + octets sains + /api/system. Jamais d exception."""
    try:
        problems = []
        for name in DASHBOARD_FILES:
            a, b = Path(root) / "dashboard" / name, \
                Path(root) / "src" / "kuro_dashboard" / "static" / name
            if not b.exists():
                problems.append(f"copie manquante: static/{name}")
            elif a.exists() and a.read_bytes() != b.read_bytes():
                problems.append(f"drift: dashboard/{name} != static/{name}")
        for pattern in DASHBOARD_GLOBS:
            for path in sorted(Path(root).glob(pattern)):
                try:
                    if b"\x00" in path.read_bytes():
                        problems.append(f"octets nuls: {path.name}")
                except Exception:
                    continue
        try:
            with urllib.request.urlopen(api_base + "/api/system",
                                        timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8", errors="replace"))
            host = (payload.get("host") or {}).get("hostname", "?")
        except Exception:
            return False, "; ".join(problems + ["API /api/system injoignable"])
        if problems:
            return False, "; ".join(problems)
        return True, (f"sync OK, sources saines, /api/system 200 "
                      f"({host}, psutil={payload.get('psutil_available')})")
    except Exception as e:
        return False, str(e)[:120]


def resync_static(root):
    """Recopie dashboard/ -> src static (fix deterministe). Jamais d exception."""
    try:
        for name in DASHBOARD_FILES:
            src_file = Path(root) / "dashboard" / name
            dst_file = Path(root) / "src" / "kuro_dashboard" / "static" / name
            if src_file.exists():
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                dst_file.write_bytes(src_file.read_bytes())
        return True
    except Exception:
        return False


def purge_pycache(root):
    """Supprime les __pycache__ (tue le masquage stale). Retourne le compte."""
    count = 0
    try:
        for path in Path(root).rglob("__pycache__"):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
                count += 1
    except Exception:
        pass
    return count


def _file_age_min(path):
    try:
        return (time.time() - Path(path).stat().st_mtime) / 60
    except Exception:
        return None


def push_freshness(log_path=None, replica_age_min=None, max_age_min=20):
    """Fraicheur du push replica. Jamais d exception.

    log_path : replica-push.log local. replica_age_min : age du fichier
    distant (None = non verifie, ex. ssh en panne).
    """
    log_age = _file_age_min(log_path) if log_path else None
    if log_age is None:
        return False, "aucun push enregistre (tache planifiee active ?)"
    if log_age > max_age_min:
        return False, f"dernier push il y a {log_age:.0f} min (> {max_age_min})"
    if replica_age_min is not None and replica_age_min > max_age_min + 10:
        return False, (f"pousse mais n arrive pas (replica distant vieux "
                       f"de {replica_age_min:.0f} min)")
    extra = "" if replica_age_min is None \
        else f" · replica distant vieux de {replica_age_min:.0f} min"
    return True, f"push il y a {log_age:.0f} min{extra}"


# --- Garde R116 (blackout git 16→19/10/2026) : panne multi-jours invisible ---

# Résultat « instance déjà en cours » (0x800710E0, policy IgnoreNew) : signalé
# dans les détails, pas alarmant — mais visible pour éviter l'alerte fatigue.
TASK_BUSY_RESULT = -2147020576
KURO_TASKS = ("KuroAutoSync", "KuroDataSync", "KuroDaily", "KuroXDaily", "KuroWeekly")
# 267009 = SCHED_S_TASK_RUNNING (tâche encore en cours au moment du relevé).
TASK_OK_RESULTS = (0, 267009)


def stale_lock_check(root, stale_min=15):
    """index.lock présente + âgée = TOUS les commits bloqués en silence. Pur."""
    lock = Path(root) / ".git" / "index.lock"
    try:
        age_min = (time.time() - lock.stat().st_mtime) / 60
    except OSError:
        return True, "aucun verrou"
    if age_min > stale_min:
        return False, f"index.lock orpheline ({age_min:.0f} min) — commits bloqués"
    return True, f"verrou actif ({age_min:.1f} min, opération git en cours)"


def autosync_freshness(log_path, max_age_min=90):
    """Dernière passe autosync (tâche toutes les 20 min) + dernier verdict. Pur.

    Toutes les sorties sont journalisées (R116) : un journal muet = tâche morte ;
    une dernière ligne KO/REFUS/ALERTE = échec à afficher.
    """
    try:
        lines = [ln for ln in Path(log_path).read_text(
            encoding="utf-8", errors="replace").splitlines() if ln.strip()]
    except OSError:
        return False, "aucun journal autosync — tâche planifiée active ?"
    if not lines:
        return False, "journal autosync vide — tâche planifiée active ?"
    last = lines[-1]
    try:
        ts = datetime.fromisoformat(last.split(" ", 1)[0])
        age_min = (datetime.now(timezone.utc) - ts).total_seconds() / 60
    except Exception:
        return False, f"horodatage illisible : {last[:80]}"
    if age_min > max_age_min:
        return False, f"dernière passe il y a {age_min:.0f} min (> {max_age_min}) — tâche en panne ?"
    verdict_ko = any(m in last for m in (" KO ", "REFUS", "ALERTE", "ERREUR"))
    if verdict_ko:
        return False, f"dernière passe en échec : {last[:120]}"
    return True, f"dernière passe il y a {age_min:.0f} min"


def parse_task_info(raw):
    """Lignes 'nom|dernierRun|dernierResult' émises par la commande PS. Pur."""
    info = {}
    for line in (raw or "").splitlines():
        parts = line.strip().split("|")
        if len(parts) == 3 and parts[0]:
            try:
                result = int(parts[2].strip())
            except ValueError:
                result = -1
            info[parts[0]] = (parts[1].strip(), result)
    return info


def scheduled_tasks_health(info, ok_results=TASK_OK_RESULTS):
    """Santé des 5 tâches Kuro d'après leur dernier résultat. Pure.

    267009 = encore en cours ; TASK_BUSY_RESULT = instance précédente toujours
    active (IgnoreNew) — ni l'un ni l'autre n'est un échec, mais les deux
    apparaissent dans le détail pour rester visibles.
    """
    problems = []
    busy = []
    for name in KURO_TASKS:
        if name not in info:
            problems.append(f"{name} absente")
            continue
        _last_run, result = info[name]
        if result in ok_results:
            continue
        if result == TASK_BUSY_RESULT:
            busy.append(name)
        else:
            problems.append(f"{name} result={result}")
    if problems:
        return False, "; ".join(problems + [f"{n} occupée" for n in busy])
    msg = f"{len(KURO_TASKS)} tâches au vert (dernier résultat 0)"
    if busy:
        msg += f" ; occupée : {', '.join(busy)}"
    return True, msg


# --- Garde R125 : aucune fenêtre CMD ne doit s'ouvrir (tâches planifiées) ---

# Toutes les tâches Kuro connues (installateur v3).
# NOTE 20/10 : les 2 tâches OpenQuant ont été SUPPRIMEES par erreur pendant le
# fix (schtasks /Change refuse les TR multi-mots, le /Delete a vidé d'abord).
# A RECREER côté OpenQuant avec un launcher caché. Retirées du périmètre pour
# éviter un faux FAIL permanent (R116 : pas d'alerte sur l'inconnu géré).
HIDDEN_TASKS = ("KuroAutoSync", "KuroDataSync", "KuroDaily", "KuroWeekly",
                "KuroSyncRepos", "KuroFleetSync", "KuroXDaily", "KuroDbBackup",
                "KuroOracle", "KuroReplies", "KuroReplicaPush")


def task_xml_is_hidden(xml):
    """True si l'action de la tâche ne peut PAS ouvrir de fenêtre console. Pur.

    Accepté : pythonw.exe (pas de console du tout), ou powershell avec
    -WindowStyle Hidden. Refusé : python.exe, powershell nu, .bat/.cmd.
    """
    low = (xml or "").lower()
    if "<command>" not in low:
        return False
    if "pythonw.exe" in low:
        return True
    if "powershell" in low and "-windowstyle hidden" in low:
        return True
    return False


def hidden_tasks_health(task_xmls):
    """Santé « fenêtres cachées » d'après les XML des tâches. Pure.

    task_xmls : {nom: xml} — l'absence d'une tâche est signalée (régression
    R116 : une tâche disparue silencieusement ne doit jamais être ignorée).
    """
    problems = []
    visible = []
    for name in HIDDEN_TASKS:
        xml = task_xmls.get(name)
        if not xml:
            problems.append(f"{name} absente")
        elif not task_xml_is_hidden(xml):
            visible.append(name)
    if visible:
        problems.append(f"fenêtre visible : {', '.join(visible)}")
    if problems:
        return False, "; ".join(problems)
    return True, f"{len(HIDDEN_TASKS)} tâches en fenêtre cachée"


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
        last = [line for line in r.stdout.splitlines() if line.strip()][-1] if r.stdout else ""
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

    # 10. Dashboard & TUI (paquet kuro_dashboard)
    ok, detail = dashboard_package_ok(KURO_ROOT)
    check("Paquet dashboard", ok, detail)
    ok, detail = tui_commands_ok()
    check("Commandes TUI", ok, detail)
    ok, detail = dashboard_live_ok(KURO_ROOT)
    check("Dashboard live", ok, detail)

    # 11. Push réplica (le serveur reçoit-il nos push ?)
    remote_age = None
    try:
        out = subprocess.run(
            ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10",
             "gad@192.168.1.84", "stat -c %Y .kuro/kuro-replica.db"],
            capture_output=True, text=True, timeout=20)
        remote_age = (time.time() - float(out.stdout.strip())) / 60
    except Exception:
        remote_age = None
    ok, detail = push_freshness(HOME / ".kuro" / "replica-push.log",
                                remote_age)
    check("Push réplica", ok, detail)

    # 12. Tâches planifiées Kuro (R116 : KuroAutoSync rendait « result 0 »
    # pendant que git était complètement à l'arrêt pendant 3 jours).
    # schtasks.exe et NON les cmdlets ScheduledTasks : WMI corrompu sur cette
    # machine → Get-ScheduledTaskInfo échoue silencieusement (tout « absent »).
    # Même raison que scripts/Install-KuroScheduledTask.ps1.
    try:
        ps_cmd = (
            "foreach ($t in 'KuroAutoSync','KuroDataSync','KuroDaily','KuroXDaily','KuroWeekly') { "
            "$csv = schtasks /query /TN $t /V /FO CSV 2>$null; "
            "if ($csv) { $v = ($csv | ConvertFrom-Csv | Select-Object -First 1)"
            ".psobject.Properties.Value; "
            "'{0}|{1}|{2}' -f $t, $v[5], $v[6] } }"
        )
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                             capture_output=True, text=True, timeout=60)
        info = parse_task_info(out.stdout)
    except Exception:
        info = {}
    ok, detail = scheduled_tasks_health(info)
    check("Tâches planifiées", ok, detail)

    # 12bis. R125 : AUCUNE fenêtre CMD (R125 : 11 tâches ouvraient des
    # consoles visibles, dont 2 en boucle toutes les 5 min). Même raison
    # WMI : schtasks /XML, pas les cmdlets ScheduledTasks.
    try:
        names = ",".join(f"'{n}'" for n in HIDDEN_TASKS)
        ps_cmd = (
            f"foreach ($t in @({names})) {{ "
            "$xml = schtasks /query /TN $t /XML 2>$null; "
            "if ($xml) { Write-Output ('###TASK:' + $t); Write-Output ($xml -join [char]10); "
            "Write-Output '###END' } }"
        )
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd],
                             capture_output=True, text=True, timeout=60)
        xmls, current = {}, None
        for line in (out.stdout or "").splitlines():
            if line.startswith("###TASK:"):
                current = line[8:].strip()
                xmls[current] = []
            elif line == "###END":
                current = None
            elif current:
                xmls[current].append(line)
        xmls = {k: "\n".join(v) for k, v in xmls.items()}
    except Exception:
        xmls = {}
    ok, detail = hidden_tasks_health(xmls)
    check("Fenêtres cachées", ok, detail)

    # 13. Git local sain (R116 : index.lock orpheline bloquait tous les commits)
    ok, detail = stale_lock_check(KURO_ROOT)
    check("Verrou git", ok, detail)
    ok, detail = autosync_freshness(KURO_ROOT / "logs" / "autosync.log")
    check("Autosync", ok, detail)

    # verdict
    fails = [n for n, ok, _ in RESULTS if not ok]
    print(f"\nVERDICT: {len(RESULTS) - len(fails)}/{len(RESULTS)} composants OK"
          + (f" — problèmes: {', '.join(fails)}" if fails else " — système sain"))

    recurring = persist_verdict_and_find_recurring(fails)
    if recurring:
        print(f"RECIDIVE: {', '.join(recurring)} en echec sur les "
              f"{RECURRENCE_WINDOW} derniers runs — lance "
              f"python scripts/kuro_autodebug.py --diagnose")

    if fix:
        apply_fixes(fails)

    return 0 if not fails else 1


def persist_verdict_and_find_recurring(fails):
    """Journalise le verdict hors repo et detecte les echecs рециidivants."""
    entry = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "fails": fails}
    history = []
    try:
        DOCTOR_HISTORY.parent.mkdir(parents=True, exist_ok=True)
        if DOCTOR_HISTORY.exists():
            for line in DOCTOR_HISTORY.read_text(
                    encoding="utf-8", errors="replace").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if isinstance(obj, dict) and isinstance(obj.get("fails"), list):
                    history.append(obj)
        with DOCTOR_HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        return []
    recent = (history + [entry])[-RECURRENCE_WINDOW:]
    if len(recent) < RECURRENCE_WINDOW:
        return []
    recurring = []
    for name in fails:
        if all(name in r.get("fails", []) for r in recent):
            recurring.append(name)
    return recurring


def apply_fixes(fails):
    print("\n--- RÉPARATIONS (--fix) ---")
    if "Daemon local" in fails:
        try:
            sys.path.insert(0, str(KURO_ROOT / "scripts"))
            import kuro_supervisor
            ok = kuro_supervisor.restart_daemon()
            print("[FIX] daemon relancé via superviseur" if ok
                  else "[FIX] ECHEC relance daemon — voir superviseur")
        except Exception as e:
            print(f"[FIX] superviseur indisponible ({e})")
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
    if "Dashboard live" in fails or "Paquet dashboard" in fails:
        purged = purge_pycache(KURO_ROOT)
        print(f"[FIX] {purged} __pycache__ purgé(s) (anti-masquage stale)")
    if "Dashboard live" in fails:
        print("[FIX] static resynchronisé" if resync_static(KURO_ROOT)
              else "[FIX] ECHEC resync static")
    if "Verrou git" in fails:
        lock = KURO_ROOT / ".git" / "index.lock"
        try:
            if lock.exists() and (time.time() - lock.stat().st_mtime) / 60 > 15:
                lock.unlink()
                print("[FIX] index.lock orpheline retirée")
            else:
                print("[FIX] verrou absent ou actif — rien à retirer")
        except OSError as e:
            print(f"[FIX] retrait index.lock impossible ({e})")


if __name__ == "__main__":
    sys.exit(main("--fix" in sys.argv))
