"""Tests de la boucle d'evolution (scripts/evolve_rules.py).

DPP greedy (determinant, diversite), verrou de l'evaluateur, et front de
Pareto des packs. Lecture seule du depot reel + fabrique de locks factices.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

import eval_rules  # noqa: E402
import evolve_rules  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------- determinant

def test_det_identity():
    assert evolve_rules.det([[1.0]]) == pytest.approx(1.0)
    assert evolve_rules.det([[1.0, 0.0], [0.0, 1.0]]) == pytest.approx(1.0)


def test_det_2x2():
    assert evolve_rules.det([[1.0, 2.0], [3.0, 4.0]]) == pytest.approx(-2.0)


def test_det_singular():
    assert evolve_rules.det([[1.0, 2.0], [2.0, 4.0]]) == 0.0


# ------------------------------------------------------------------ DPP

def test_fingerprint_normalised():
    vec = evolve_rules.fingerprint(REPO / "rules" / "rule_86_kuro.md")
    norm = sum(v * v for v in vec.values()) ** 0.5
    assert norm == pytest.approx(1.0, abs=1e-9)


def test_coreset_distinct_and_bounded():
    paths = sorted((REPO / "rules").glob("rule_*.md"))
    coreset = evolve_rules.dpp_coreset(paths, 10)
    names = [c["rule"] for c in coreset]
    assert len(names) == len(set(names)) == 10
    for c in coreset:
        assert 0.0 < c["difficulty"] <= 1.0
        assert c["tokens_est"] > 0


def test_coreset_prefers_diverse_dense_rules():
    """Le coreset doit inclure la regle la plus dense du depot (R94)."""
    paths = sorted((REPO / "rules").glob("rule_*.md"))
    longest = max(paths, key=lambda p: len(p.read_text(encoding="utf-8")))
    coreset = evolve_rules.dpp_coreset(paths, 5)
    assert longest.stem in [c["rule"] for c in coreset]


# ---------------------------------------------------------------- locks

def test_check_lock_absent(tmp_path, monkeypatch):
    monkeypatch.setattr(evolve_rules, "LOCK_PATH", tmp_path / "nope.json")
    with pytest.raises(SystemExit, match="VERROU ABSENT"):
        evolve_rules.check_lock()


def test_check_lock_mismatch(tmp_path, monkeypatch):
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({"eval_sha256": "f" * 64}), encoding="utf-8")
    monkeypatch.setattr(evolve_rules, "LOCK_PATH", lock)
    with pytest.raises(SystemExit, match="REFUSE"):
        evolve_rules.check_lock()


def test_check_lock_ok():
    """Le verrou reel du depot matche l'evaluateur reel (sinon : re-freeze)."""
    lock = evolve_rules.check_lock()
    assert lock["eval_sha256"] == eval_rules.eval_sha256()


# --------------------------------------------------------------- Pareto

def test_pareto_no_dominance():
    membership = gen_rule_packs_membership()
    rows = evolve_rules.pareto_packs(membership)
    assert [r["pack"] for r in rows] == ["lite", "medium", "heavy"]
    # couverture croissante et cout croissant → personne domine personne
    for r in rows:
        assert r["dominated_by"] is None, r


def test_pareto_lite_cheaper_than_heavy():
    rows = evolve_rules.pareto_packs(gen_rule_packs_membership())
    by_pack = {r["pack"]: r for r in rows}
    assert by_pack["lite"]["tokens_est"] < by_pack["heavy"]["tokens_est"]
    assert by_pack["lite"]["perf_cover"] < by_pack["heavy"]["perf_cover"]


def test_pareto_mandatory_cover_not_substring_bug():
    """R116 : la perf pondere sur les VRAIS mandatory (parsing numerique).

    Incident 29/10 : `any(r[1:] in n)` comparait "1" a l interieur de
    "rule_100..." → 55/63 fichiers mandatory, max_perf ecrase, et lite
    affiche a 19% alors qu il contient les 11 fichiers mandatory reels
    (les 17 IDs de la checklist). Ici : 11 fichiers, pas 55.
    """
    import gen_rule_packs
    membership = gen_rule_packs_membership()
    rows = evolve_rules.pareto_packs(membership)
    by_pack = {r["pack"]: r for r in rows}
    mand_nums = gen_rule_packs.mandatory_rule_numbers()
    # Reconstitution independante du denominateur attendu.
    all_rules = sorted(membership)
    mand_files = [n for n in all_rules
                  if gen_rule_packs.rule_numbers(n) & mand_nums]
    assert len(mand_files) == 11
    max_perf = 2 * len(mand_files) + (len(all_rules) - len(mand_files))
    # lite contient exactement les 11 fichiers mandatory → perf = 2*11/max.
    assert by_pack["lite"]["perf_cover"] == round(2 * 11 / max_perf, 3)
    # heavy couvre tout → 100%.
    assert by_pack["heavy"]["perf_cover"] == 1.0


def gen_rule_packs_membership():
    import gen_rule_packs
    return gen_rule_packs.rule_packs(gen_rule_packs.load_metadata())


# ---------------------------------------------------------- integration

def test_build_report_floor_respected():
    """Le rapport reel passe le plafond h0 (baseline scellee)."""
    report = evolve_rules.build_report(coreset_size=5)
    assert report["evaluator_locked"] is True
    assert report["current"]["floor_respected"] is True
    assert report["current"]["pass_rate"] >= report["baseline_h0"]["pass_rate"]
    assert len(report["coreset"]) == 5
    assert report["next_actions"]
