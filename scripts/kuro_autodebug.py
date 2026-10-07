#!/usr/bin/env python3
"""kuro_autodebug.py — boucle d'auto-debug de Kuro (niveau 3 : patch verifie).

Etages :
    L1 diagnose (defaut, lecture seule) : collecte les echecs (historique
       doctor + queues de logs), sanitize, interroge le cerveau, affiche
       diagnostic + patch propose. AUCUNE ecriture.
    L2 --apply : redemarrages services (superviseur/doctor) + backup DB.
    L3 --apply --code : applique un unified diff propose par le cerveau sur
       un chemin autorise, backup prealable, pytest cible, rollback si rouge.

Garde-fous (MANDATORY) :
- R111 : finances.local.json n'est JAMAIS lu ; montants et secrets sont
  rediges avant tout envoi au cerveau (distant par defaut via OpenRouter).
- R101 : chemins autorises = scripts/, tests/, dashboard/, src/ du repo kuro-rules.
  Bloques : *.local.json, .env*, *finances*, *secret*, *token*, liste R101,
  tout ce qui sort du repo.
- R93 : ASCII uniquement, pathlib, stdout utf-8 protege.

Codes retour : 0 ok · 1 echec non resolu · 2 bloque par garde-fou ·
               3 cerveau indisponible (diagnostic deterministe seul).
"""

import difflib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
KURO_ROOT = Path(__file__).resolve().parent.parent
DB = HOME / ".kuro" / "kuro.db"
DOCTOR_HISTORY = HOME / ".kuro" / "doctor_history.jsonl"
BACKUP_DIR = HOME / ".kuro" / "autodebug_backups"

sys.path.insert(0, str(KURO_ROOT / "scripts"))

ALLOWED_PREFIXES = ("scripts/", "tests/", "dashboard/", "src/")
BLOCKED_SUBSTRINGS = (
    ".local.json", ".env", "finances", "secret", "token", "passwd",
    "credentials", "private",
)
BLOCKED_BASENAMES = {
    "decision-memo.md", "LAUNCH_POSTS.md", "SESSION_SUMMARY.md",
    "finances.local.json",
}
LOG_TAIL_LINES = 40
LOG_SOURCES = (
    HOME / "AppData" / "Local" / "KuroPulse" / "last-run.log",
    HOME / "Documents" / "kuro" / "daemon.log",
)

SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bmpg-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\$\s?[\d]+(?:[.,][\d]+)?"),
)


def sanitize(text: str) -> str:
    """Redige secrets et montants. Idempotent."""
    if not text:
        return ""
    out = str(text)
    for pat in SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def is_allowed_path(rel: str) -> tuple[bool, str]:
    """Verifie qu'un chemin relatif au repo est patchable."""
    norm = rel.replace("\\", "/").lstrip("./")
    if not norm or norm.startswith(("..", "/", "~")):
        return False, "hors repo"
    if Path(norm).name in BLOCKED_BASENAMES:
        return False, "fichier protege R101"
    lowered = norm.lower()
    if any(b in lowered for b in BLOCKED_SUBSTRINGS):
        return False, "motif bloque (secret/local/finance)"
    if not norm.startswith(ALLOWED_PREFIXES):
        return False, f"prefixe autorise: {', '.join(ALLOWED_PREFIXES)}"
    target = KURO_ROOT / norm
    if not target.exists():
        return False, "cible inexistante"
    try:
        target.resolve().relative_to(KURO_ROOT.resolve())
    except Exception:
        return False, "echappement du repo (lien ?)"
    return True, "ok"


def load_recent_fails(limit: int = 3) -> list[str]:
    if not DOCTOR_HISTORY.exists():
        return []
    fails: list[str] = []
    try:
        lines = DOCTOR_HISTORY.read_text(
            encoding="utf-8", errors="replace").splitlines()
        for line in lines[-limit:]:
            try:
                obj = json.loads(line.strip())
            except Exception:
                continue
            if isinstance(obj, dict):
                for name in obj.get("fails", []):
                    if name not in fails:
                        fails.append(name)
    except Exception:
        pass
    return fails


def collect_log_tails() -> dict[str, str]:
    tails: dict[str, str] = {}
    candidates = list(LOG_SOURCES) + sorted((HOME / ".kuro").glob("*.log"))
    for path in candidates[:6]:
        try:
            if not path.exists():
                continue
            lines = path.read_text(
                encoding="utf-8", errors="replace").splitlines()
            tails[str(path)] = "\n".join(lines[-LOG_TAIL_LINES:])
        except Exception:
            continue
    return tails


def build_prompt(fails: list[str], tails: dict[str, str]) -> str:
    parts = ["Echecs constates par kuro_doctor (recidivants) :"]
    parts += [f"- {sanitize(f)}" for f in fails] or ["- (aucun verdict recent)"]
    parts.append("\nQueues de logs (sanitisees) :")
    if tails:
        for src, tail in tails.items():
            parts.append(f"\n--- {src} ---\n{sanitize(tail)[:2000]}")
    else:
        parts.append("(aucun log accessible)")
    parts.append(
        "\nReponds en 3 sections : 1) CAUSE RACINE probable (1-2 phrases), "
        "2) NIVEAU (L1 restart / L2 data / L3 code), "
        "3) PATCH : unified diff minimal (chemins scripts/, tests/, "
        "dashboard/, src/ uniquement ; packaging/, *.local.json et secrets "
        "interdits) ou 'AUCUN' si L1/L2 suffit.")
    return "\n".join(parts)


def extract_diff(reply: str) -> str | None:
    if not reply:
        return None
    tail = reply.split("PATCH")[-1][:40] if "PATCH" in reply else ""
    if "AUCUN" in tail:
        return None
    m = re.search(r"```diff\n(.*?)```", reply, re.S)
    if m:
        return m.group(1).strip()
    lines = [line for line in reply.splitlines()
             if line.startswith(("--- ", "+++ ", "@@ ", "+", "-"))]
    if len(lines) >= 3 and any(line.startswith("--- ") for line in lines):
        return "\n".join(lines)
    return None


def diff_targets(diff_text: str) -> list[str]:
    targets = []
    for line in diff_text.splitlines():
        if line.startswith("+++ "):
            t = line[4:].strip().split()[0]
            if t.startswith(("b/", "a/")):
                t = t[2:]
            if t != "/dev/null" and t not in targets:
                targets.append(t)
    return targets


def apply_diff_with_rollback(diff_text: str) -> tuple[bool, str, dict]:
    """Applique le diff avec backup + rollback auto si echec d'application.

    Retourne (succes, message, originaux). En cas de tests rouges APRES
    application reussie, l'appelant utilise rollback(originaux).
    """
    targets = diff_targets(diff_text)
    if not targets:
        return False, "aucune cible ---/+++ trouvee dans le diff", {}
    if len(targets) > 3:
        return False, "diff trop large (>3 fichiers) — refuse", {}
    for t in targets:
        ok, why = is_allowed_path(t)
        if not ok:
            return False, f"cible refusee {t} : {why}", {}
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    backups: dict[str, Path] = {}
    originals: dict[str, str] = {}
    try:
        for t in targets:
            p = KURO_ROOT / t.replace("\\", "/").lstrip("./")
            originals[t] = p.read_text(encoding="utf-8", errors="replace")
            bkp = BACKUP_DIR / f"{stamp}_{Path(t).name}.bak"
            bkp.write_text(originals[t], encoding="utf-8")
            backups[t] = bkp
        patched = dict(originals)
        for t in targets:
            ok, msg = apply_unified_to_text(patched[t], diff_text, t)
            if not ok:
                raise RuntimeError(f"patch inapplicable a {t} : {msg}")
            patched[t] = msg  # msg porte le texte patche en cas de succes
        for t in targets:
            (KURO_ROOT / t.replace("\\", "/").lstrip("./")).write_text(
                patched[t], encoding="utf-8")
    except Exception as e:
        rollback(originals)
        return False, f"apply echoue, rollback effectue : {e}", {}
    return True, f"{len(targets)} fichier(s) patches, backups dans {BACKUP_DIR}", originals


def apply_unified_to_text(original: str, diff_text: str,
                          target: str) -> tuple[bool, str]:
    """Applique les hunks du diff visant `target`. Retourne (ok, texte|erreur)."""
    norm_target = target.replace("\\", "/").lstrip("./")
    hunks: list[list[str]] = []
    current: list[str] | None = None
    in_target = False
    for line in diff_text.splitlines():
        if line.startswith("--- "):
            in_target = norm_target in line
            current = None
        elif line.startswith("+++ "):
            if in_target and norm_target in line:
                current = []
                hunks.append(current)
            else:
                in_target = False
                current = None
        elif line.startswith("@@ ") and in_target and current is not None:
            current.append(line)
        elif in_target and current is not None:
            if line and line[0] in (" ", "+", "-"):
                current.append(line)
    if not hunks:
        return False, "aucun hunk pour cette cible"
    src = original.splitlines(keepends=True)
    out: list[str] = []
    pos = 0
    for hunk in hunks:
        header = hunk[0]
        m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", header)
        if not m:
            return False, f"hunk illisible : {header[:60]}"
        start = int(m.group(1)) - 1
        if start < pos:
            return False, "hunks desordonnes"
        out.extend(src[pos:start])
        pos = start
        for hline in hunk[1:]:
            kind, content = hline[0], hline[1:]
            if kind == " ":
                if pos >= len(src) or src[pos].rstrip("\n") != content:
                    rollback_note = (src[pos].rstrip("\n")[:60] if pos < len(src)
                                     else "<fin de fichier>")
                    return False, (f"contexte inattendu ligne {pos + 1} : "
                                   f"attendu {content[:60]!r}, trouve {rollback_note!r}")
                out.append(src[pos])
                pos += 1
            elif kind == "-":
                if pos >= len(src) or src[pos].rstrip("\n") != content:
                    return False, f"suppression impossible ligne {pos + 1}"
                pos += 1
            elif kind == "+":
                out.append(content + "\n")
    out.extend(src[pos:])
    # montre le diff reel obtenu (aide au diagnostic humain)
    _ = list(difflib.unified_diff(
        original.splitlines(), "".join(out).splitlines(), lineterm=""))
    return True, "".join(out)


def rollback(originals: dict[str, str]) -> None:
    for t, content in originals.items():
        try:
            (KURO_ROOT / t.replace("\\", "/").lstrip("./")).write_text(
                content, encoding="utf-8")
        except Exception:
            continue


def run_targeted_tests() -> tuple[bool, str]:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests", "-q", "-x"],
            cwd=str(KURO_ROOT), capture_output=True, text=True, timeout=600)
        tail = "\n".join(r.stdout.splitlines()[-3:]) if r.stdout else ""
        return r.returncode == 0, tail or f"exit={r.returncode}"
    except Exception as e:
        return False, str(e)[:200]


def diagnose(ask_fn=None) -> tuple[int, str]:
    fails = load_recent_fails()
    tails = collect_log_tails()
    prompt = build_prompt(fails, tails)
    if ask_fn is None:
        try:
            sys.path.insert(0, str(KURO_ROOT / "scripts"))
            from kuro_llm import ask as ask_fn  # type: ignore
        except Exception:
            ask_fn = None
    reply = None
    if ask_fn is not None:
        try:
            reply = ask_fn(prompt,
                           system="Tu es le mecanicien du studio lambda-Section. "
                                  "Diagnostic concis, patch minimal.")
        except Exception:
            reply = None
    if not reply:
        fallback = ("cerveau indisponible — diagnostic deterministe : "
                    f"echecs={fails or 'aucun verdict recent'} ; "
                    "pistes : 1) relance via kuro_doctor --fix, "
                    "2) verifie heartbeat daemon, 3) lis les logs ci-dessus.")
        return 3, fallback
    return 0, reply


def main(argv: list[str]) -> int:
    apply = "--apply" in argv
    code = "--code" in argv
    if not apply:
        print("=== KURO AUTODEBUG : diagnose (lecture seule) ===\n")
        rc, out = diagnose()
        print(out)
        d = extract_diff(out)
        if d:
            print("\n--- patch detecte dans la reponse ---")
            print(f"cibles : {', '.join(diff_targets(d))}")
            print("Relance avec --apply --code pour appliquer + tester + rollback.")
        return rc
    # --apply : L1/L2 automatiques
    print("=== KURO AUTODEBUG : apply (L1/L2 automatiques) ===")
    try:
        sys.path.insert(0, str(KURO_ROOT / "scripts"))
        import kuro_doctor
        rc = kuro_doctor.main(fix=True)
        print(f"[autodebug] doctor --fix -> exit={rc}")
    except Exception as e:
        print(f"[autodebug] doctor --fix impossible : {e}")
        return 1
    if not code:
        print("[autodebug] L3 code non demande (ajoute --code). Termine.")
        return 0
    print("\n=== L3 : patch propose par le cerveau ===")
    rc, out = diagnose()
    if rc == 3:
        print(out)
        return 3
    print(out)
    d = extract_diff(out)
    if not d:
        print("[autodebug] aucun diff exploitable — arret sans ecriture.")
        return 1
    ok, msg, originals = apply_diff_with_rollback(d)
    print(f"[autodebug] apply : {msg}")
    if not ok:
        return 2
    passed, tail = run_targeted_tests()
    print(f"[autodebug] pytest : {'VERT' if passed else 'ROUGE'} — {tail}")
    if not passed:
        rollback(originals)
        print("[autodebug] tests rouges — rollback effectue. "
              "Patch rejete, originaux restaures.")
        return 1
    print("[autodebug] patch conserve (tests verts). "
          "Relis le diff avant commit — jamais de commit auto.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
