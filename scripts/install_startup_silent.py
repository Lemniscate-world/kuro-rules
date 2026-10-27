# install_startup_silent.py — migre le Demarrage vers des lancements SANS fenêtre (R125).
#
# Incident 24/10/2026 : KuroBot.cmd et OpenVikingPilot.bat ouvraient 2 consoles
# cmd visibles à CHAQUE login (PIDs réels 14244 / 22576), pendant que la garde
# R125 du doctor ne couvrait que les tâches planifiées. Deux autres lanceurs
# échouaient en clignotant (MemosPilot : stage effacé de Temp ; horcruxe-lab :
# ligne cd/python collée sur une seule ligne).
#
# Correctif (sans élévation, contrairement à une tâche /SC ONLOGON qui exige
# admin) : chaque service est lancé par un .lnk vers pythonw.exe — qui n'a pas
# de console — qui exécute task_launchers/hidden_launch.py, lequel crée le fils
# avec CREATE_NO_WINDOW (mêmes logs que l'ancien `cmd /c ... >> log`).
#
# Idempotent : relancer ne casse rien. Usage :
#   python scripts/install_startup_silent.py            # installe
#   python scripts/install_startup_silent.py --dry-run  # montre ce qui bougerait
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kuro_doctor as doctor  # noqa: E402  — garde partagée bat_opens_console

ROOT = doctor.KURO_ROOT
PYW = r"C:\Python314\pythonw.exe"          # même interpréteur que KuroDaemon.bat
PY = r"C:\Python314\python.exe"
HELPER = ROOT / "scripts" / "task_launchers" / "hidden_launch.py"
BACKUP = ROOT / "SYNC_BACKUPS" / "startup-launchers"
HOME = doctor.HOME


def startup_links():
    """(nom du .lnk, cible, arguments) pour chaque service à lancer au login.

    Défini en fonction et non en constante : les chemins dépendent du dépôt et
    du profil, donc du contexte d'exécution (tests hermétiques, R123).

    24/10 soir : KuroDaemon et KuroSupervisor migrent du .bat au .lnk. Un .bat
    du Démarrage est exécuté par cmd.exe (ftype batfile = "%1" %*), qui alloue
    une console visible — donc CLIGNOTEMENT à chaque login, même en ne lançant
    que pythonw.exe. Vérifié avant migration : les deux scripts n'utilisent que
    des chemins absolus (HOME / ".kuro"), donc le cwd imposé par hidden_launch
    (log.parent) ne peut rien casser.
    """
    bot_log = ROOT / "logs" / "kuro-bot.log"
    viking_log = HOME / ".openviking" / "server-login.log"
    daemon_log = ROOT / "logs" / "kuro-daemon.log"
    supervisor_log = ROOT / "logs" / "kuro-supervisor.log"
    return (
        ("KuroBot.lnk", PYW,
         f'"{HELPER}" --log "{bot_log}" "{PY}" -u "{ROOT / "scripts" / "kuro_bot.py"}"'),
        ("OpenVikingPilot.lnk", PYW,
         f'"{HELPER}" --log "{viking_log}" "{HOME / ".local" / "bin" / "openviking-server.exe"}"'),
        ("KuroDaemon.lnk", PYW,
         f'"{HELPER}" --log "{daemon_log}" "{PYW}" "{HOME / "Documents" / "kuro" / "daemon.py"}"'),
        ("KuroSupervisor.lnk", PYW,
         f'"{HELPER}" --log "{supervisor_log}" "{PYW}" '
         f'"{ROOT / "scripts" / "kuro_supervisor.py"}" --check --fix'),
    )


# Alias lisible pour le test (le module est aussi importable hors dépôt).
STARTUP_LINKS = startup_links()

_PS_TEMPLATE = """
$sh = New-Object -ComObject WScript.Shell
foreach ($spec in @({specs})) {{
  $p = Join-Path '{startup}' $spec.Link
  $l = $sh.CreateShortcut($p)
  $l.TargetPath = $spec.Target
  $l.Arguments = $spec.Arguments
  $l.WorkingDirectory = '{workdir}'
  $l.WindowStyle = 7
  $l.Save()
  Write-Output ('CREATED ' + $spec.Link)
}}
"""


def create_links(startup, links=STARTUP_LINKS, dry_run=False):
    """Cree/met a jour les .lnk. Retourne la liste des noms traites."""
    if dry_run:
        return [name for name, _, _ in links]
    specs = ";".join(
        "@{Link='" + name + "';Target='" + target + "';Arguments='"
        + args.replace("'", "''") + "'}"
        for name, target, args in links)
    ps1 = _PS_TEMPLATE.format(specs=specs, startup=str(startup), workdir=str(ROOT))
    script = startup / ".mk_startup_links.ps1"
    startup.mkdir(parents=True, exist_ok=True)
    script.write_text(ps1, encoding="utf-8")
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
            capture_output=True, text=True, timeout=60,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if out.returncode != 0:
            raise RuntimeError((out.stderr or out.stdout or "echec powershell")[:300])
        return [line.split(" ", 1)[1] for line in out.stdout.splitlines()
                if line.startswith("CREATED ")]
    finally:
        script.unlink(missing_ok=True)


def cleanup_console_bat(startup, dry_run=False):
    """Deplace en sauvegarde TOUS les .bat/.cmd du Demarrage.

    24/10 soir : la regle precedente ne deplacait que les .bat detectes
    « console » par bat_opens_console, donc KuroDaemon.bat et KuroSupervisor.bat
    (qui ne lancent que pythonw) ETAIENT LAISSES — et clignotaient quand meme,
    parce que c'est cmd.exe (ftype batfile = "%1" %*) qui alloue la fenetre,
    pas le contenu du .bat. Toute entree .bat/.cmd part en sauvegarde.
    """
    moved = []
    BACKUP.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(startup).glob("*")):
        if path.suffix.lower() not in (".bat", ".cmd"):
            continue
        if dry_run:
            moved.append(path.name)
            continue
        target = BACKUP / path.name
        target.unlink(missing_ok=True)
        path.replace(target)
        moved.append(path.name)
    return moved


def main(argv=None):
    ap = argparse.ArgumentParser(description="Demarrage sans fenetre (R125)")
    ap.add_argument("--dry-run", action="store_true",
                    help="montre l'action sans rien modifier")
    a = ap.parse_args(argv)

    startup = doctor.STARTUP_DIR
    if not startup.is_dir():
        print(f"FAIL dossier Demarrage introuvable : {startup}")
        return 1

    print(f"[{'DRY' if a.dry_run else 'OK  '}] Demarrage : {startup}")
    moved = cleanup_console_bat(startup, dry_run=a.dry_run)
    for name in moved:
        print(f"  retire (sauvegarde {BACKUP.name}/) : {name}")
    created = create_links(startup, dry_run=a.dry_run)
    for name in created:
        print(f"  lnk silencieux : {name} -> pythonw + {HELPER.name}")

    ok, detail = doctor.startup_launchers_health(startup)
    print(f"[{'OK  ' if ok else 'FAIL'}] {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
