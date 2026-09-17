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


def sh(cmd, dry_run=False):
    """Execute une etape. dry_run=True : affiche sans executer. Jamais fatal."""
    if cmd and cmd[0] == PY:
        label = " ".join([Path(cmd[1]).name] + list(cmd[2:]))
    else:
        label = " ".join(cmd)
    print(f"$ {label}")
    if dry_run:
        print("  (dry-run : non execute)")
        return 0
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, shell=False,
                           encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        print("  ! timeout=900s (non fatal, suite)")
        return 1
    out = ((r.stdout or "") + ("\n" + r.stderr if r.stderr else "")).strip()
    if out:
        print(out[-3000:])
    if r.returncode != 0:
        print(f"  ! exit={r.returncode} (non fatal, suite)")
    return r.returncode


def _git_exe() -> str:
    """git.exe introuvable dans le PATH de subprocess sous Windows : fallback usuel."""
    for cand in ("git", r"C:\Program Files\Git\bin\git.exe",
                 r"C:\Program Files\Git\cmd\git.exe",
                  str(Path.home() / r"AppData\Local\Programs\Git\bin\git.exe")):
        try:
            subprocess.run([cand, "--version"], capture_output=True, timeout=10)
            return cand
        except Exception:
            continue
    return "git"


def git_publish(repo: Path, message: str, dry_run: bool) -> bool:
    """Commit + push d'un repo si dirty. Retourne True si quelque chose a ete pousse."""
    git = _git_exe()
    try:
        dirty = subprocess.run([git, "status", "--porcelain"], cwd=str(repo),
                               capture_output=True, text=True, timeout=30)
        if not dirty.stdout.strip():
            return False
        if dry_run:
            print(f"  (dry-run : commit+push {repo.name})")
            return False
        subprocess.run([git, "add", "-A"], cwd=str(repo), capture_output=True, timeout=60)
        r = subprocess.run([git, "commit", "-m", message, "--no-verify"], cwd=str(repo),
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            print(f"  ! commit {repo.name}: {r.stderr.strip()[-200:]}")
            return False
        p = subprocess.run([git, "push"], cwd=str(repo), capture_output=True, text=True, timeout=120)
        print(f"  push {repo.name}: {'ok' if p.returncode == 0 else p.stderr.strip()[-200:]}")
        return p.returncode == 0
    except Exception as exc:
        print(f"  ! git_publish {repo.name}: {exc}")
        return False


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
    (ROOT / "logs").mkdir(exist_ok=True)
    sys.path.insert(0, str(SCRIPTS))
    import kuro_proposals as _P
    write = (a.full and not a.dry_run) and not _P.vacances()
    if _P.vacances():
        print("mode vacances : lecture seule forcee")
    print(f"=== KURO AUTOMATE daily={a.daily} weekly={a.weekly} write={write} ===")

    fails = 0
    # 1. Sante (lecture seule, jamais de fix auto ici)
    fails += sh([PY, str(SCRIPTS / "kuro_doctor.py")], dry_run=a.dry_run)
    # 2. Verite factuelle locale
    fails += sh([PY, str(SCRIPTS / "audit_truth_daily.py"), "--apply" if write else "--dry-run"],
                dry_run=a.dry_run)
    # 3. Portfolio + blog (chemins locaux par defaut)
    fails += sh([PY, str(SCRIPTS / "generate_portfolio.py")], dry_run=a.dry_run)
    fails += sh([PY, str(SCRIPTS / "generate_blog.py"), "--apply" if write else "--dry-run"],
                dry_run=a.dry_run)
    # 4. Securite : PATCH reel seulement si write
    if write:
        fails += sh([PY, str(SCRIPTS / "kuro_security.py")], dry_run=a.dry_run)
    else:
        print("$ kuro_security.py (saute sans --full : PATCH reel)")
    # 5. Guardian CI : sec par defaut, write autorise rerun/push
    guardian = [PY, str(SCRIPTS / "ci_guardian.py"),
                "--output", str(LEMNISCATE / "ci-status.json")]
    if not write:
        guardian.append("--dry-run")
    fails += sh(guardian, dry_run=a.dry_run)
    # 6. Strategie + Any.do + finance + investisseurs (jamais destructifs)
    fails += sh([PY, str(SCRIPTS / "kuro_strategy.py")], dry_run=a.dry_run)
    if write:
        fails += sh([PY, str(SCRIPTS / "kuro_strategy.py"), "--discord"], dry_run=a.dry_run)
    fails += sh([PY, str(SCRIPTS / "kuro_anydo.py"), "--export"], dry_run=a.dry_run)
    fails += sh([PY, str(SCRIPTS / "kuro_finance.py")], dry_run=a.dry_run)
    fails += sh([PY, str(SCRIPTS / "kuro_investor_digest.py"), "--dry-run"], dry_run=a.dry_run)

    if a.weekly:
        # 7. Resync agent : % Epingle recalculés depuis les faits git (R85).
        fails += sh([PY, str(SCRIPTS / "compute_progress.py"),
                     "--apply" if write else "--dry-run"], dry_run=a.dry_run)
        fails += sh([PY, str(SCRIPTS / "kuro_radar.py"),
                     "--epingle", str(ROOT / "Epingle_Projets.md"),
                     "--append-truth", str(ROOT / "TRUTH_DAILY.md")], dry_run=a.dry_run)
        fails += sh([PY, str(SCRIPTS / "weekly_report.py"),
                     "--ci-status", str(LEMNISCATE / "ci-status.json"),
                     "--epingle", str(ROOT / "Epingle_Projets.md")], dry_run=a.dry_run)

    # 8. Publication autonome : artefacts générés + Epingle + truth uniquement.
    if write and not a.dry_run:
        if git_publish(LEMNISCATE, "kuro: sync portfolio [skip ci]", a.dry_run):
            print("  portfolio publie")
        git_publish(ROOT, "kuro: sync auto Epingle + truth [skip ci]", a.dry_run)

    print(f"=== FIN fails~{fails} (compteur indicatif, chaque etape est non fatale) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
