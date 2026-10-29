"""Tests du generateur de packs lite/medium/heavy (scripts/gen_rule_packs.py).

Utilise le vrai depot (lecture seule, deterministe, hors reseau) : ce qui
se mesure c'est l'invariant HarnessPro lite ⊆ medium ⊆ heavy et la
determinisme de la generation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import gen_rule_packs  # noqa: E402


def test_membership_valid_and_nested():
    membership = gen_rule_packs.rule_packs(gen_rule_packs.load_metadata())
    gen_rule_packs.validate_nesting(membership)  # leve si violation
    assert membership
    for name, packs in membership.items():
        if "lite" in packs:
            assert "medium" in packs and "heavy" in packs, name


def test_mandatory_rules_in_lite():
    """Les fichiers portant les regles mandatory sont dans le pack lite."""
    membership = gen_rule_packs.rule_packs(gen_rule_packs.load_metadata())
    lite = [n for n, packs in membership.items() if "lite" in packs]
    # echantillon representatif des mandatory (R1, R100, R94, R89)
    for expected in ("rule_01_foundation", "rule_100_session_compliance",
                     "rule_94_x_post", "rule_89_lessons_learned"):
        assert expected in lite, f"{expected} absent du pack lite"


def test_rule_numbers_parsing():
    """R116 : les IDs de regle se lisent par prefixe numerique, pas en sous-chaine.

    Incident 29/10 : `any(r[1:] in n)` faisait passer "1" pour couvrir
    rule_100... (55/63 fichiers classes mandatory a tort) ; et `r in p.stem`
    comparait "R1" (majuscule) au stem "rule_01..." → couverture 0.
    """
    assert gen_rule_packs.rule_numbers("rule_01_foundation") == {1}
    assert gen_rule_packs.rule_numbers("rule_100_session_compliance") == {100}
    assert gen_rule_packs.rule_numbers(
        "rule_04_36_42_43_47_50_51_52") == {4, 36, 42, 43, 47, 50, 51, 52}
    # R1 ne couvre JAMAIS rule_100 (regression du bug de sous-chaine).
    assert 1 not in gen_rule_packs.rule_numbers("rule_100_session_compliance")
    # Le slug arrete la lecture : "rule_94_x_post" → {94}, pas de "post".
    assert gen_rule_packs.rule_numbers("rule_94_x_post") == {94}


def test_mandatory_files_are_exactly_lite():
    """Les 17 IDs mandatory decomptent en 11 fichiers — tous en pack lite.

    Contre-preuve du bug 29/10 : le matching errone en classait 55/63,
    ce qui ecrasait la perf de lite a 19% alors qu'il couvre 100% des
    mandatory (operating point « floor » du menu HarnessPro).
    """
    membership = gen_rule_packs.rule_packs(gen_rule_packs.load_metadata())
    mand_nums = gen_rule_packs.mandatory_rule_numbers()
    assert len(mand_nums) == 17
    mand_files = sorted(n for n in membership
                        if gen_rule_packs.rule_numbers(n) & mand_nums)
    assert len(mand_files) == 11
    lite = sorted(n for n, packs in membership.items() if "lite" in packs)
    assert lite == mand_files


def test_manual_trigger_rules_heavy_only():
    """Les regles a trigger manual (marketing) ne sont qu'en heavy."""
    membership = gen_rule_packs.rule_packs(gen_rule_packs.load_metadata())
    for manual in ("rule_119_marketing_technique", "rule_120_kuro_marketing",
                   "rule_121_pr_fix_marketing"):
        assert membership[manual] == ["heavy"], manual


def test_packs_are_distinct():
    """Les 3 operating points sont reels (pas 2 copies)."""
    outputs = gen_rule_packs.build_all()
    assert outputs["lite"] != outputs["medium"]
    assert outputs["medium"] != outputs["heavy"]
    # lite est strictement plus court (cout Inferieur)
    assert len(outputs["lite"]) < len(outputs["medium"])


def test_generation_deterministic():
    first = gen_rule_packs.build_all()
    second = gen_rule_packs.build_all()
    assert first == second


def test_no_drift_in_repo():
    """Garde : packs/ doit etre regenere apres tout changement de membership
    (--apply). Si ce test echec : python scripts/gen_rule_packs.py --apply."""
    membership = gen_rule_packs.rule_packs(gen_rule_packs.load_metadata())
    for pack in gen_rule_packs.PACK_NAMES:
        paths = gen_rule_packs.pack_rules(membership, pack)
        expected = gen_rule_packs.render_pack(pack, paths, membership)
        target = gen_rule_packs.PACKS_DIR / f"AGENTS_{pack}.md"
        assert target.exists(), f"{target.name} absent — lancer --apply"
        assert target.read_text(encoding="utf-8") == expected, (
            f"{target.name} en drift — lancer gen_rule_packs.py --apply")
