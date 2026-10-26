"""Genere les packs de regles lite / medium / heavy (HarnessPro WS3).

Principe (papier HarnessPro) : au lieu d'un seul harness, on livre un menu
de variantes optimisees pour differents budgets. Ici le "cout" d'un pack =
tokens estimes (somme des fichiers de regles inclus / 4), la "perf" =
couverture des regles mandatory (poids 2) et optionnelles (poids 1).

Membership : rules/_metadata.yaml, cle `packs` par regle (defaut
[medium, heavy] ; les regles mandatory passent en [lite, medium, heavy]).
Invariant verifie a la generation : lite ⊆ medium ⊆ heavy.

Sortie deterministicte (LF, UTF-8, tri par nom) :
  packs/AGENTS_lite.md, packs/AGENTS_medium.md, packs/AGENTS_heavy.md

Usage :
  python scripts/gen_rule_packs.py --dry-run   # preview (defaut)
  python scripts/gen_rule_packs.py --check     # CI : exit 1 si drift
  python scripts/gen_rule_packs.py --apply     # ecrire packs/
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

RULES_DIR = ROOT / "rules"
PACKS_DIR = ROOT / "packs"
PACK_NAMES = ("lite", "medium", "heavy")

FIRST_HEADING_RE = re.compile(r"^#+\s*(.+?)\s*$")


def load_metadata() -> dict:
    try:
        import yaml
    except ImportError:  # pragma: no cover
        raise SystemExit("pyyaml requis : pip install pyyaml")
    return yaml.safe_load((RULES_DIR / "_metadata.yaml").read_text(encoding="utf-8"))


def rule_packs(meta: dict) -> dict[str, list[str]]:
    """Membership {rule_name: [packs]} avec fallback defaults.

    Defaut : [medium, heavy]. Les regles a trigger manual (situationnelles,
    ex. marketing) ne descendent que en [heavy] — medium reste un vrai
    operating point distinct du heavy (principe HarnessPro : 3 points
    differents, pas 2 copies).
    """
    defaults = (meta.get("defaults") or {}).get("packs") or ["medium", "heavy"]
    membership = {}
    for p in sorted(RULES_DIR.glob("rule_*.md")):
        ov = (meta.get("overrides") or {}).get(p.stem) or {}
        packs = ov.get("packs")
        if not packs:
            if ov.get("trigger") == "manual":
                packs = ["heavy"]
            else:
                packs = defaults
        bad = [x for x in packs if x not in PACK_NAMES]
        if bad:
            raise SystemExit(f"{p.stem}: packs invalides {bad}")
        membership[p.stem] = list(packs)
    return membership


def validate_nesting(membership: dict[str, list[str]]) -> None:
    """Invariant HarnessPro : lite ⊆ medium ⊆ heavy."""
    for name, packs in membership.items():
        if "lite" in packs and "medium" not in packs:
            raise SystemExit(f"{name}: lite sans medium (violation inclusion)")
        if "medium" in packs and "heavy" not in packs:
            raise SystemExit(f"{name}: medium sans heavy (violation inclusion)")


def rule_title(path: Path) -> str:
    m = FIRST_HEADING_RE.search(path.read_text(encoding="utf-8"))
    return m.group(1) if m else path.stem


def estimate_tokens(paths: list[Path]) -> int:
    """Estimation tokens = caracteres / 4 (convention kuro : memory_tree)."""
    total = sum(len(p.read_text(encoding="utf-8")) for p in paths)
    return total // 4


def mandatory_ids() -> set[str]:
    """Regles mandatory depuis la COMPLIANCE_CHECKLIST (section 🔴🔴)."""
    text = (RULES_DIR / "COMPLIANCE_CHECKLIST.md").read_text(encoding="utf-8")
    mandatory_section = text.split("OPTIONNELLES")[0]
    return set(re.findall(r"^\|\s*(R[\d.]+)\s*\|", mandatory_section, flags=re.M))


def pack_rules(membership: dict[str, list[str]], pack: str) -> list[Path]:
    return [RULES_DIR / f"{name}.md"
            for name, packs in membership.items() if pack in packs]


def render_pack(pack: str, paths: list[Path], membership: dict) -> str:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    tokens = estimate_tokens(paths)
    mand = mandatory_ids()
    lines = [
        f"# AGENTS_{pack}.md -- Kuro Rules Redirector (pack {pack})",
        "",
        f"Pack {pack.upper()} - version {version} - genere par"
        " scripts/gen_rule_packs.py - NE PAS EDITER A LA MAIN.",
        "",
        "Pack de regles servant le sous-ensemble adapte au budget de la"
        " session (HarnessPro lite/medium/heavy) :",
        "- lite : regles MANDATORY uniquement (sessions courtes)",
        "- medium : mandatory + regles situationnelles (defaut)",
        "- heavy : toutes les regles (releases, launches, compliance totale)",
        "",
        f"Cout estime : ~{tokens} tokens de regles"
        f" ; couverture mandatory : {sum(1 for p in paths if any(r in p.stem for r in mand))}",
        "",
        "## Rule Index",
        "",
    ]
    for p in paths:
        lines.append(f"- **{p.stem}**: {rule_title(p)}")
    lines.append("")
    return "\n".join(lines)


def build_all() -> dict[str, str]:
    meta = load_metadata()
    membership = rule_packs(meta)
    validate_nesting(membership)
    return {pack: render_pack(pack, pack_rules(membership, pack), membership)
            for pack in PACK_NAMES}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Generateur des packs lite/medium/heavy")
    parser.add_argument("--apply", action="store_true", help="ecrire packs/")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 si drift (CI)")
    parser.add_argument("--dry-run", action="store_true", help="preview (defaut)")
    args = parser.parse_args(argv)

    outputs = build_all()
    drift = []
    for pack, content in outputs.items():
        target = PACKS_DIR / f"AGENTS_{pack}.md"
        current = target.read_text(encoding="utf-8") if target.exists() else None
        if current != content:
            drift.append(pack)
        tokens = estimate_tokens(pack_rules(rule_packs(load_metadata()), pack))
        print(f"[packs] {pack:6} {len(content.splitlines()):3} lignes"
              f" ~{tokens} tokens {'(drift)' if current != content else '(a jour)'}")

    if args.check:
        if drift:
            print(f"[packs] DRIFT : {drift} — lancer --apply")
            return 1
        print("[packs] packs a jour")
        return 0

    if args.apply:
        PACKS_DIR.mkdir(exist_ok=True)
        for pack, content in outputs.items():
            (PACKS_DIR / f"AGENTS_{pack}.md").write_text(content, encoding="utf-8",
                                                         newline="\n")
        print(f"[packs] ecrits : {sorted(drift) or 'rien a changer'}")
        return 0

    for pack, content in outputs.items():
        print(f"--- packs/AGENTS_{pack}.md ---")
        print("\n".join(content.splitlines()[:14]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
