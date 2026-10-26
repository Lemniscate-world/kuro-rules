"""Tests de l'evaluateur fige des regles (evals/eval_rules.py).

Hermétique : les checks sont evalues sur un mini-repo fabrique dans
tmp_path, jamais sur le vrai depot (sauf verrou, lire seule).
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))

import eval_rules  # noqa: E402

MANDATORY_LINE = "\n".join(
    f"| {r} | ✅ DONE | ok |" for r in eval_rules.MANDATORY_RULES)


def make_repo(root: Path) -> Path:
    """Mini-repo kuro-rules valide : 10/10 checks OK."""
    rules = root / "rules"
    rules.mkdir(parents=True)
    (rules / "rule_01_foundation.md").write_text(
        "# RULE 1: Read Rules First\n\n## Rule\n\nRead AGENTS.md first.\n",
        encoding="utf-8")
    (rules / "rule_02_other.md").write_text(
        "# RULE 2: Other\n\n## Rule\n\nDo the thing.\n", encoding="utf-8")
    (rules / "COMPLIANCE_CHECKLIST.md").write_text(
        "# CHECKLIST\n\n## MANDATORY\n"
        "| # | Statut | Note |\n|---|---|---|\n" + MANDATORY_LINE + "\n",
        encoding="utf-8")
    (rules / "_metadata.yaml").write_text(
        "defaults:\n  scope: company\n  trigger: always\n  status: active\n"
        "overrides: {}\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "# AGENTS.md\n\n## Rule Index\n"
        "- **rule_01_foundation**: RULE 1\n"
        "- **rule_02_other**: RULE 2\n", encoding="utf-8")
    (root / "SESSION_SUMMARY.md").write_text(
        "# Session\n\n## Resume\n\nPas grand chose.\n\n"
        "### Résumé Compact (R79)\n\nCourt resume de huit mots ici.\n",
        encoding="utf-8")
    (root / ".gitignore").write_text(
        ".env\n*.local.json\n__pycache__\n", encoding="utf-8")
    return root


def test_mini_repo_passes(tmp_path):
    repo = make_repo(tmp_path)
    summary = eval_rules.evaluate(repo)
    fails = [c for c in summary["checks"] if not c["ok"]]
    assert not fails, fails
    assert summary["pass_rate"] == 1.0


def test_utf8_and_mojibake_detected(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "rules" / "rule_02_other.md").write_bytes(
        "# RULE 2\n\nTexte cass\xe9 : mojibake Ã© ici\n".encode("utf-8"))
    summary = eval_rules.evaluate(repo)
    by_id = {c["id"]: c for c in summary["checks"]}
    assert not by_id["no_mojibake_rules"]["ok"]


def test_u_fffd_detected(tmp_path):
    repo = make_repo(tmp_path)
    (repo / "rules" / "rule_02_other.md").write_text(
        "# RULE 2\n\nTexte�cassé\n", encoding="utf-8")
    summary = eval_rules.evaluate(repo)
    by_id = {c["id"]: c for c in summary["checks"]}
    assert not by_id["utf8_rules"]["ok"]


def test_index_drift_detected(tmp_path):
    repo = make_repo(tmp_path)
    with (repo / "AGENTS.md").open("a", encoding="utf-8") as fh:
        fh.write("- **rule_99_ghost**: RULE GHOST\n")
    summary = eval_rules.evaluate(repo)
    by_id = {c["id"]: c for c in summary["checks"]}
    assert not by_id["index_in_sync"]["ok"]
    assert "orpheline" in by_id["index_in_sync"]["detail"]


def test_violated_detected(tmp_path):
    repo = make_repo(tmp_path)
    with (repo / "rules" / "COMPLIANCE_CHECKLIST.md").open(
            "a", encoding="utf-8") as fh:
        fh.write("| R1 | 🔴 VIOLATED | oups |\n")
    summary = eval_rules.evaluate(repo)
    by_id = {c["id"]: c for c in summary["checks"]}
    assert not by_id["checklist_no_violated"]["ok"]


def test_compact_summary_too_long(tmp_path):
    repo = make_repo(tmp_path)
    long_text = "mot " * 160
    (repo / "SESSION_SUMMARY.md").write_text(
        "### Résumé Compact (R79)\n\n" + long_text + "\n",
        encoding="utf-8")
    summary = eval_rules.evaluate(repo)
    by_id = {c["id"]: c for c in summary["checks"]}
    assert not by_id["compact_summary_r79"]["ok"]


def test_compact_summary_recent_session_wins(tmp_path):
    """SESSION_SUMMARY en ordre decroissant : c'est le compact LE PLUS
    RECENT (en haut) qui compte, pas le plus ancien (en bas)."""
    repo = make_repo(tmp_path)
    recent_ok = "### Résumé Compact (R79)\n\nCourt et correct ici.\n\n"
    old_violating = "### Résumé Compact (R79)\n\n" + "mot " * 160 + "\n"
    (repo / "SESSION_SUMMARY.md").write_text(
        "# Session Summary - 2026-10-26\n\n" + recent_ok
        + "---\n\n# Session Summary - 2020-01-01\n\n" + old_violating,
        encoding="utf-8")
    summary = eval_rules.evaluate(repo)
    by_id = {c["id"]: c for c in summary["checks"]}
    assert by_id["compact_summary_r79"]["ok"], by_id["compact_summary_r79"]


def test_lock_refuses_modified_evaluator(tmp_path, monkeypatch):
    """Evaluateur modifie depuis le freeze → exit 2, rien n'est evalue."""
    lock = tmp_path / "frozen_eval.lock.json"
    lock.write_text(json.dumps({
        "frozen_at": "2026-10-26T00:00:00+00:00",
        "eval_sha256": "0" * 64,
        "baseline": {"pass_rate": 1.0},
    }), encoding="utf-8")
    monkeypatch.setattr(eval_rules, "LOCK_PATH", lock)
    assert eval_rules.main([]) == 2


def test_freeze_writes_lock(tmp_path, monkeypatch):
    lock = tmp_path / "frozen_eval.lock.json"
    monkeypatch.setattr(eval_rules, "LOCK_PATH", lock)
    rc = eval_rules.main(["--freeze", "--report",
                          str(tmp_path / "report.json")])
    assert rc == 0
    data = json.loads(lock.read_text(encoding="utf-8"))
    assert data["eval_sha256"] == eval_rules.eval_sha256()
    assert data["baseline"]["pass_rate"] == 1.0


def test_lock_verrouille_passe_apres_freeze(tmp_path, monkeypatch):
    """Apres freeze avec le bon hash, un run normal passe (exit 0)."""
    lock = tmp_path / "frozen_eval.lock.json"
    monkeypatch.setattr(eval_rules, "LOCK_PATH", lock)
    assert eval_rules.main(["--freeze", "--report",
                            str(tmp_path / "r.json")]) == 0
    rc = eval_rules.main(["--report", str(tmp_path / "r.json")])
    assert rc in (0, 1)  # 0 si le vrai repo est conforme, 1 sinon — pas 2


def test_check_basics():
    """Sanity : les fonctions de check retournent (bool, str)."""
    for fn in (eval_rules.check_session_summary_exists,
               eval_rules.check_gitignore_sensitive):
        ok, detail = fn(Path(__file__).resolve().parent.parent)
        assert isinstance(ok, bool) and isinstance(detail, str)


@pytest.mark.parametrize("bad_pack", [["lite"], ["nope"], ["lite", "nope"]])
def test_metadata_packs_invalid_rejected(tmp_path, bad_pack):
    """Une membership hors enum (ou non imbriquee) est refusee."""
    import gen_rule_packs
    repo = make_repo(tmp_path)
    meta = {"defaults": {"packs": bad_pack}, "overrides": {}}
    old_dir = gen_rule_packs.RULES_DIR
    try:
        gen_rule_packs.RULES_DIR = repo / "rules"
        with pytest.raises(SystemExit):
            membership = gen_rule_packs.rule_packs(meta)
            gen_rule_packs.validate_nesting(membership)
    finally:
        gen_rule_packs.RULES_DIR = old_dir
