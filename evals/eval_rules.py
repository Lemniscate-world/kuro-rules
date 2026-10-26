"""Evalueur fige des regles kuro-rules (HarnessPro WS2 : evaluateur label-free).

Principe (papier HarnessPro, arXiv:2610.26770) : la boucle d'evolution des
regles est jugee par un evaluateur FIXE, determine et executable, que
l'evolution ne peut pas modifier. Cet evalueur mesure la conformite du
"harness de regles" (l'index AGENTS.md + rules/ + artefacts de session) :

- aucune donnee reseau, aucun LLM : filet deterministe (R115 gate 1) ;
- verrouille par hash : `--freeze` scelle l'evaluateur + la baseline h0 ;
  toute modification ulterieure est refusee tant qu'un re-freeze explicite
  n'a pas ete fait (l'evolution ne peut pas tricher sur son examinateur).

Usage :
  python evals/eval_rules.py            # eval + verification du verrou
  python evals/eval_rules.py --freeze   # (re)sceller evaluateur + baseline

Sortie : evals/rules_eval_report.json ; verrou : evals/frozen_eval.lock.json.
Exit 0 = OK, 1 = checks en echec, 2 = evaluateur modifie depuis le freeze.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from kuro_paths import confine_arg  # noqa: E402

DEFAULT_REPORT = ROOT / "evals" / "rules_eval_report.json"
LOCK_PATH = ROOT / "evals" / "frozen_eval.lock.json"

# Regles mandatory (COMPLIANCE_CHECKLIST section 🔴🔴) — spec figee de l'eval.
MANDATORY_RULES = [
    "R1", "R4", "R7", "R8", "R11", "R36", "R41", "R42", "R67",
    "R74", "R76", "R79", "R82", "R89", "R94", "R99", "R100",
]

REDIRECTOR_RE = re.compile(r"^-\s+\*\*(rule_[A-Za-z0-9_]+)\*\*", flags=re.M)
VIOLATED_RE = re.compile(r"\|\s*R[\d.]+\s*\|\s*[^|\n]*VIOLATED", flags=re.M)
MOJIBAKE_PATTERNS = ["Ã©", "Ã¨", "Ã ", "â€™", "â€œ", "�"]
VALID_TRIGGERS = {"always", "auto", "manual"}
VALID_STATUS = {"active", "draft", "deprecated"}
VALID_SCOPES = {"company", "team", "service"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_utf8_rules(root: Path) -> tuple[bool, str]:
    """R41 : tous les fichiers rules/*.md sont UTF-8 stricts, sans U+FFFD."""
    bad = []
    for p in sorted((root / "rules").glob("rule_*.md")):
        try:
            text = p.read_bytes().decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            bad.append(f"{p.name}: {exc}")
            continue
        if "�" in text:
            bad.append(f"{p.name}: caracteres U+FFFD presents")
    return (not bad, "; ".join(bad) if bad else "UTF-8 strict OK")


def check_no_mojibake(root: Path) -> tuple[bool, str]:
    """R41 : pas de mojibake (encodage casse) dans rules/*.md."""
    hits = []
    for p in sorted((root / "rules").glob("rule_*.md")):
        text = _read(p)
        for pat in MOJIBAKE_PATTERNS:
            if pat in text:
                hits.append(f"{p.name}: {pat!r}")
    return (not hits, "; ".join(hits) if hits else "aucun mojibake")


def check_index_in_sync(root: Path) -> tuple[bool, str]:
    """R11/R74 : l'index AGENTS.md reflete exactement rules/rule_*.md."""
    agents = root / "AGENTS.md"
    if not agents.exists():
        return (False, "AGENTS.md absent")
    indexed = set(REDIRECTOR_RE.findall(_read(agents)))
    ondisk = {p.stem for p in (root / "rules").glob("rule_*.md")}
    missing = sorted(ondisk - indexed)
    stale = sorted(indexed - ondisk)
    if missing or stale:
        parts = []
        if missing:
            parts.append(f"absents de l'index: {missing}")
        if stale:
            parts.append(f"entrees orphelines: {stale}")
        return (False, " ; ".join(parts))
    return (True, f"{len(ondisk)} regles indexees")


def check_checklist_no_violated(root: Path) -> tuple[bool, str]:
    """R100 : aucune regle mandatory en statut VIOLATED dans la checklist."""
    path = root / "rules" / "COMPLIANCE_CHECKLIST.md"
    if not path.exists():
        return (False, "COMPLIANCE_CHECKLIST.md absent")
    found = VIOLATED_RE.findall(_read(path))
    if found:
        return (False, f"{len(found)} violation(s) declaree(s)")
    return (True, "aucune violation declaree")


def check_checklist_mandatory_listed(root: Path) -> tuple[bool, str]:
    """R100 : les regles mandatory de la spec sont toutes presentes."""
    path = root / "rules" / "COMPLIANCE_CHECKLIST.md"
    if not path.exists():
        return (False, "COMPLIANCE_CHECKLIST.md absent")
    text = _read(path)
    present = set(re.findall(r"^\|\s*(R[\d.]+)\s*\|", text, flags=re.M))
    missing = [r for r in MANDATORY_RULES if r not in present]
    if missing:
        return (False, f"mandatory absentes: {missing}")
    return (True, f"{len(MANDATORY_RULES)} mandatory listees")


def check_session_summary_exists(root: Path) -> tuple[bool, str]:
    """R4 : SESSION_SUMMARY.md existe et n'est pas vide."""
    path = root / "SESSION_SUMMARY.md"
    if not path.exists():
        return (False, "SESSION_SUMMARY.md absent")
    if len(_read(path).strip()) < 50:
        return (False, "SESSION_SUMMARY.md quasi vide")
    return (True, "present")


def check_compact_summary_r79(root: Path) -> tuple[bool, str]:
    """R79 : le dernier Resume Compact (R79) reste <= 150 mots.

    Accepte les deux formats d entree historiques : "Resume compact /
    Compact Summary" (sessions 2026-10+) et "Resume Compact (R79)".
    """
    path = root / "SESSION_SUMMARY.md"
    if not path.exists():
        return (False, "SESSION_SUMMARY.md absent")
    text = _read(path)
    lowered = text.lower()
    # SESSION_SUMMARY est en ordre decroissant : la session la plus recente
    # est EN HAUT, donc la premiere occurrence (find), pas la derniere.
    candidates = [i for i in (lowered.find("resume compact"),
                              lowered.find("r\u00e9sum\u00e9 compact"))
                  if i != -1]
    idx = min(candidates) if candidates else -1
    if idx == -1:
        return (False, "aucun bloc Resume Compact trouve")
    tail = text[idx:]
    # coupe au prochain heading de niveau 1-3 apres la premiere ligne
    stop = re.search(r"\n#{1,3} ", tail)
    body = tail[: stop.start()] if stop else tail
    # la ligne de titre + le separateur " / Compact Summary" ne comptent pas
    body = "\n".join(body.splitlines()[1:])
    words = len(body.split())
    if words > 150:
        return (False, f"dernier compact = {words} mots (>150)")
    return (True, f"dernier compact = {words} mots")


def check_gitignore_sensitive(root: Path) -> tuple[bool, str]:
    """R76 : .gitignore couvre les patterns sensibles (.env, *.local.json)."""
    path = root / ".gitignore"
    if not path.exists():
        return (False, ".gitignore absent")
    text = _read(path)
    required = [".env", "*.local.json"]
    missing = [pat for pat in required
               if not re.search(re.escape(pat).replace(r"\*", ".*"), text, re.M)]
    if missing:
        return (False, f"patterns absents: {missing}")
    return (True, "patterns sensibles couverts")


def check_metadata_valid(root: Path) -> tuple[bool, str]:
    """_metadata.yaml : structure et valeurs enumerees valides."""
    path = root / "rules" / "_metadata.yaml"
    if not path.exists():
        return (False, "_metadata.yaml absent")
    try:
        import yaml
    except ImportError:  # pragma: no cover
        return (False, "pyyaml indisponible")
    try:
        data = yaml.safe_load(_read(path)) or {}
    except yaml.YAMLError as exc:
        return (False, f"YAML invalide: {exc}")
    if "defaults" not in data or "overrides" not in data:
        return (False, "cles defaults/overrides manquantes")
    bad = []
    for name, ov in (data.get("overrides") or {}).items():
        if not isinstance(ov, dict):
            bad.append(f"{name}: override non-dict")
            continue
        if "trigger" in ov and ov["trigger"] not in VALID_TRIGGERS:
            bad.append(f"{name}: trigger={ov['trigger']}")
        if "status" in ov and ov["status"] not in VALID_STATUS:
            bad.append(f"{name}: status={ov['status']}")
        if "scope" in ov and ov["scope"] not in VALID_SCOPES:
            bad.append(f"{name}: scope={ov['scope']}")
    if bad:
        return (False, "; ".join(bad))
    return (True, f"{len(data.get('overrides') or {})} overrides valides")


def check_rule_files_hygiene(root: Path) -> tuple[bool, str]:
    """Chaque rules/rule_*.md : >= 3 lignes et au moins un heading."""
    bad = []
    for p in sorted((root / "rules").glob("rule_*.md")):
        text = _read(p)
        if len(text.splitlines()) < 3 or not re.search(r"^#+\s", text, re.M):
            bad.append(p.name)
    if bad:
        return (False, f"fichiers trop maigres: {bad}")
    return (True, "tous les fichiers de regles ont un heading")


CHECKS = [
    ("utf8_rules", check_utf8_rules),
    ("no_mojibake_rules", check_no_mojibake),
    ("index_in_sync", check_index_in_sync),
    ("checklist_no_violated", check_checklist_no_violated),
    ("checklist_mandatory_listed", check_checklist_mandatory_listed),
    ("session_summary_exists", check_session_summary_exists),
    ("compact_summary_r79", check_compact_summary_r79),
    ("gitignore_sensitive", check_gitignore_sensitive),
    ("metadata_valid", check_metadata_valid),
    ("rule_files_hygiene", check_rule_files_hygiene),
]


def eval_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def evaluate(root: Path = ROOT) -> dict:
    """Execute tous les checks et resume le score (le "PR(h)" du harness)."""
    results = []
    for check_id, fn in CHECKS:
        try:
            ok, detail = fn(root)
        except Exception as exc:  # un check qui plante = echec, pas de crash
            ok, detail = False, f"exception: {exc!r}"
        results.append({"id": check_id, "ok": bool(ok), "detail": detail})
    passed = sum(1 for r in results if r["ok"])
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass_rate": passed / len(results) if results else 0.0,
        "checks": results,
    }


def load_lock() -> dict | None:
    if not LOCK_PATH.exists():
        return None
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Eval figee des regles kuro-rules")
    parser.add_argument("--freeze", action="store_true",
                        help="(re)sceller l'evaluateur + la baseline h0")
    parser.add_argument("--report", default=str(DEFAULT_REPORT),
                        help="fichier rapport JSON")
    args = parser.parse_args(argv)

    lock = load_lock()
    current_hash = eval_sha256()

    if not args.freeze and lock is not None:
        if lock.get("eval_sha256") != current_hash:
            print("[eval-rules] REFUSE : l'evaluateur fige a ete modifie")
            print(f"  freeze: {lock.get('eval_sha256', '?')[:16]}...")
            print(f"  actuel: {current_hash[:16]}...")
            print("  L'evolution ne peut pas toucher son examinateur.")
            print("  Re-freeze explicite requis : eval_rules.py --freeze")
            return 2

    summary = evaluate(ROOT)
    report = confine_arg(args.report, [ROOT, Path(tempfile.gettempdir()).resolve()])
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    for r in summary["checks"]:
        status = "OK  " if r["ok"] else "FAIL"
        print(f"[eval-rules] {status} {r['id']:32} {r['detail']}")

    print(f"[eval-rules] {summary['passed']}/{summary['total']} checks OK"
          f" (pass_rate={summary['pass_rate']:.0%})")

    if args.freeze:
        baseline = {
            "total": summary["total"],
            "passed": summary["passed"],
            "pass_rate": summary["pass_rate"],
            "checks": [{"id": c["id"], "ok": c["ok"]} for c in summary["checks"]],
        }
        LOCK_PATH.write_text(json.dumps({
            "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "eval_sha256": current_hash,
            "baseline": baseline,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[eval-rules] verrou scelle : {LOCK_PATH}"
              f" (baseline h0 = {summary['passed']}/{summary['total']})")
        return 0

    if lock and lock.get("baseline"):
        base_rate = lock["baseline"].get("pass_rate", 0.0)
        delta = summary["pass_rate"] - base_rate
        sign = "+" if delta >= 0 else ""
        print(f"[eval-rules] baseline h0 = {base_rate:.0%}"
              f" ; actuel = {summary['pass_rate']:.0%} ({sign}{delta:.0%})")
        floor = base_rate
        if summary["pass_rate"] < floor:
            print("[eval-rules] PLAFOND DE PERF VIOLÉ : le harness actuel"
                  " est en dessous de la baseline h0")
            return 1

    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
