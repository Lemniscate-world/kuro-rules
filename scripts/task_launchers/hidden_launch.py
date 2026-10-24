# hidden_launch.py — lance une commande SANS aucune fenetre console (R125).
#
# Usage : appelé par un raccourci .lnk du dossier Demarrage dont la cible est
# pythonw.exe (pas de console du tout) :
#   pythonw.exe hidden_launch.py --log <fichier> <commande> [args...]
# CREATE_NO_WINDOW empeche le FILS d'en ouvrir une, et les sorties sont
# redirigees vers --log (meme contrat de logs que l'ancien `cmd /c ... >> log`).
# Detache : le service survit a la mort de ce lanceur, aucun fenetre, aucun
# elevateur requis (contrairement a une tache planifiee /SC ONLOGON).
import argparse
import subprocess  # nosec B404 : lanceur interne, liste d'arguments sans shell
import sys
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Lancement cache d'un service (R125)")
    ap.add_argument("--log", required=True, help="fichier de sortie (append)")
    ap.add_argument("cmd", nargs=argparse.REMAINDER,
                    help="commande et arguments a executer (apres -- si besoin)")
    a = ap.parse_args()

    cmd = [c for c in a.cmd if c != "--"]
    if not cmd:
        ap.error("aucune commande a lancer (usage : hidden_launch.py --log <f> <cmd> [args...])")

    log = Path(a.log).expanduser()
    log.parent.mkdir(parents=True, exist_ok=True)

    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    with open(log, "a", encoding="utf-8", errors="replace") as fh:
        fh.write(f"[{sys.argv[0]}] lancement : {' '.join(cmd)}\n")
        # Detache : ni wait() ni PIPE, le fils herite du handle de fichier.
        subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT,  # noqa: S603
                         cwd=str(log.parent), creationflags=flags)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
