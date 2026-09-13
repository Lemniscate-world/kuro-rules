#!/usr/bin/env python3
"""kuro_automate.py — orchestrateur local unique (Windows + CI-safe, zero dependance).

Chaine quotidienne (faits d'abord, publication ensuite) :
  1. doctor (lecture seule)  2. truth audit  3. portfolio+blog
  4. strategy --discord      5. anydo --export  6. finance + investor dry-run
Le lundi (+ --weekly) ajoute : radar + weekly_report + investor post.
Securite + guardian : dry-run par defaut, --full pour push/rerun reels.

Usage:
  python scripts/kuro_automate.py --daily [--full] [--dry-run]
  python scripts/kuro_automate.py --weekly [--full]

Secrets lus depuis l'environnement ou .env local (jamais committe, R76).
Log : logs/kuro-automate-YYYYMMDD.log + append KURO_ACTIONS_LOG.md si --full.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
LEMNISCATE = Path(os.environ.get("LEMNISCATE_DIR", str(Path.home() / "Documents" / "Lemniscate-world")))
PY = sys.executable


def load_dotenv():
    env = ROOT / ".env"
    if not env.exists():
        return
    for line in env.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def sh(cmd, dry=False):
    label = " ".join(cmd[2:]) if cmd[0] == PY else " ".join(cmd)
    print(f"$ {label}")
    if dry and "--dry-run" not in cmd and "dry" not in label:
        print("  (dry-run: saute)")
        return 0
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    out = ((r.stdout or "") + ("\n" + r.stderr if r.stderr else "")).strip()
    if out:
        print(out[-3000:])
    if r.returncode != 0:
        print(f"  ! exit={r.returncode} (non fatal, suite)")
    return r.returncode


def main():
    ap = argparse.ArgumentParser(description="Orchestrateur local Kuro")
    ap.add_argument("--daily", action="store_true", help="chaine quotidienne")
    ap.add_argument("--weekly", action="store_true", help="ajoute radar + rapports hebdo")
    ap.add_argument("--full", action="store_true", help="autorise push/rerun/Discord reels")
    ap.add_argument("--dry-run", action="store_true", help="affiche sans executer les ecritures")
    a = ap.parse_args()
    if not a.daily and not a.weekly:
        a.daily = True

    load_dotenv()
    logdir = ROOT / "logs"
    logdir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d")
    print(f"=== KURO AUTOMATE daily={a.daily} weekly={a.weekly} full={a.full} ===")

    fails = 0
    # 1. Sante (lecture seule, jamais de fix auto ici)
    fails += sh([PY, str(SCRIPTS / "kuro_doctor.py")])
    # 2. Verite factuelle locale
    fails += sh([PY, str(SCRIPTS / "audit_truth_daily.py"), "--dry-run" if not a.full else "--apply"])
    # 3. Portfolio + blog (chemins locaux par defaut)
    fails += sh([PY, str(SCRIPTS / "generate_portfolio.py")])
    fails += sh([PY, str(SCRIPTS / "generate_blog.py"), "--dry-run" if not a.full else "--apply"])
    # 4. Securite : lecture seule sauf --full (PATCH reel sinon)
    if a.full and not a.dry_run:
        fails += sh([PY, str(SCRIPTS / "kuro_security.py")])
    else:
        print("$ kuro_security.py (saute sans --full : PATCH reel)")
    # 5. Guardian CI : sec par defaut, --full autorise rerun/push
    guardian = [PY, str(SCRIPTS / "ci_guardian.py"),
                "--output", str(LEMNISCATE / "ci-status.json")]
    if not a.full:
        guardian.append("--dry-run")
    fails += sh(guardian)
    # 6. Strategie + Any.do + finance + investisseurs (jamais destructifs)
    fails += sh([PY, str(SCRIPTS / "kuro_strategy.py")] + ([] if a.full else []))
    if a.full and not a.dry_run:
        fails += sh([PY, str(SCRIPTS / "kuro_strategy.py"), "--discord"])
    fails += sh([PY, str(SCRIPTS / "kuro_anydo.py"), "--export"])
    fails += sh([PY, str(SCRIPTS / "kuro_finance.py")])
    fails += sh([PY, str(SCRIPTS / "kuro_investor_digest.py"), "--dry-run"])

    if a.weekly:
        fails += sh([PY, str(SCRIPTS / "kuro_radar.py"),
                     "--epingle", str(ROOT / "Epingle_Projets.md"),
                     "--append-truth", str(ROOT / "TRUTH_DAILY.md")])
        fails += sh([PY, str(SCRIPTS / "weekly_report.py"),
                     "--ci-status", str(LEMNISCATE / "ci-status.json"),
                     "--epingle", str(ROOT / "Epingle_Projets.md")])

    print(f"=== FIN fails~{fails} (compteur indicatif, chaque etape est non fatale) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
