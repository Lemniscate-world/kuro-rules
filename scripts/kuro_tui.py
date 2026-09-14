#!/usr/bin/env python3
"""kuro_tui.py — TUI Kuro stdlib uniquement (Windows compatible, zero dependance).

Menu texte : doctor / strategie / radar / securite / finance / investisseurs.
Chaque choix appelle le script correspondant en subprocess, affiche sortie.
Usage: python scripts/kuro_tui.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

ITEMS = [
    ("1", "Doctor (sante systeme)", [PY, str(ROOT / "kuro_doctor.py")]),
    ("2", "Strategie (digest + decisions)", [PY, str(ROOT / "kuro_strategy.py")]),
    ("3", "Radar (veille hebdo)", [PY, str(ROOT / "kuro_radar.py"), "--epingle", str(ROOT.parent / "Epingle_Projets.md")]),
    ("4", "Securite (durcissement, retry inclus)", [PY, str(ROOT / "kuro_security.py")]),
    ("5", "Finance (burn/MRR/runway)", [PY, str(ROOT / "kuro_finance.py")]),
    ("6", "Investisseurs (dry-run)", [PY, str(ROOT / "kuro_investor_digest.py"), "--dry-run"]),
    ("7", "Any.do export (pipeline -> taches)", [PY, str(ROOT / "kuro_anydo.py"), "--export"]),
    ("8", "Any.do pull (notes -> projets + propositions)", [PY, str(ROOT / "kuro_anydo.py"), "--pull"]),
    ("q", "Quitter", None),
]


def run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300, shell=False)
        out = (r.stdout or "") + ("\n" + r.stderr if r.stderr else "")
        print(out[-6000:] or "(vide)")
    except Exception as e:
        print(f"Echec: {e}")


def main():
    while True:
        print("\n=== KURO ===")
        for key, label, _ in ITEMS:
            print(f" {key}. {label}")
        try:
            choice = input("> ").strip().lower()
        except EOFError:
            break
        except KeyboardInterrupt:
            return 130
        for key, label, cmd in ITEMS:
            if choice == key:
                if cmd is None:
                    return 0
                print(f"\n--- {label} ---")
                run(cmd)
                break
        else:
            print("Choix inconnu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
