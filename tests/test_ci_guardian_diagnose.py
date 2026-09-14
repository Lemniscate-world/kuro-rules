"""Tests ci_guardian — classification des échecs par signatures (logique pure)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from ci_guardian import classify_failure, fail_keys, should_alert  # noqa: E402


def _report(fails):
    repos = {}
    for repo, wf in fails:
        repos.setdefault(repo, []).append({"name": wf, "conclusion": "failure"})
    return {"overall": "red", "actions": [],
            "repos": [{"name": r, "workflows": w} for r, w in repos.items()]}


def test_should_alert_premier_rapport_rouge():
    assert should_alert(_report([("o/r", "CI")]), None) is True
    assert should_alert(_report([("o/r", "CI")]), {}) is True


def test_should_alert_silence_si_memes_echecs():
    r = _report([("o/r", "CI")])
    assert should_alert(r, _report([("o/r", "CI")])) is False


def test_should_alert_si_nouvel_echec():
    assert should_alert(_report([("o/r", "CI"), ("o/r2", "Lint")]),
                        _report([("o/r", "CI")])) is True
    assert should_alert(_report([]), _report([("o/r", "CI")])) is True


def test_should_alert_vert_sans_actions_silencieux():
    assert should_alert({"overall": "green", "actions": [], "repos": []}, None) is False


def test_secret_sonar_manquant():
    log = "ERROR Failed to query JRE metadata: GET https://api.sonarcloud.io/... HTTP 403. Please check the property sonar.token"
    diag = classify_failure(log)
    assert diag is not None
    assert "SONAR_TOKEN" in diag["cause"]
    assert not diag["auto_fixable"]


def test_sous_module_fantome():
    log = "##[error]fatal: No url found for submodule path 'hf_space' in .gitmodules"
    diag = classify_failure(log)
    assert diag is not None
    assert "sous-module" in diag["cause"].lower()
    assert diag["detail"] == "hf_space"


def test_dette_formatage_autofixable():
    log = "black....................................................................Failed\nwould reformat /home/runner/work/x.py"
    diag = classify_failure(log)
    assert diag is not None
    assert diag["auto_fixable"]
    assert diag["klass"] == "formatting"


def test_fichiers_proteges_autofixables():
    log = "  [FAIL] Protected file tracked: acquisition_tracker.md"
    diag = classify_failure(log)
    assert diag is not None
    assert diag["klass"] == "protected_files"
    assert diag["detail"] == "acquisition_tracker.md"


def test_findings_bandit():
    log = ">> Issue: [B615:huggingface_unsafe_download] Unsafe Hugging Face Hub download"
    diag = classify_failure(log)
    assert diag is not None
    assert "bandit" in diag["cause"].lower()
    assert not diag["auto_fixable"]


def test_asserts_production():
    log = 'VIOLATIONS=$(grep -rn "assert " --include="*.py" . --exclude-dir=tests'
    diag = classify_failure(log)
    assert diag is not None
    assert "assert" in diag["cause"].lower()


def test_dependance_manquante():
    log = "ModuleNotFoundError: No module named 'mcp'"
    diag = classify_failure(log)
    assert diag is not None
    assert "pendance" in diag["cause"]


def test_fichier_protege_fr_autofixable():
    log = "##[error]Fichier protege tracke (R76): git rm --cached SESSION_SUMMARY.md"
    diag = classify_failure(log)
    assert diag is not None
    assert diag["klass"] == "protected_files"
    assert diag["detail"] == "SESSION_SUMMARY.md"


def test_eslint_no_undef_diagnostic_seul():
    log = "/home/runner/work/x/DraggableHabitRow.tsx\n  26:16  error  'React' is not defined  no-undef"
    diag = classify_failure(log)
    assert diag is not None
    assert "no-undef" in diag["cause"]
    assert not diag["auto_fixable"]


def test_log_inconnu_retourne_none():
    assert classify_failure("") is None
    assert classify_failure("tout va bien, rien a signaler") is None


def test_ordre_des_signatures_secret_avant_autre():
    log = "sonar.token HTTP 403 ... F401 unused import"
    diag = classify_failure(log)
    assert "SONAR_TOKEN" in diag["cause"]
