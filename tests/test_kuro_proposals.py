"""Tests kuro_proposals — P-ID, statuts, budgets, vacances, francais (logique pure)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_proposals as kp  # noqa: E402


def test_add_dedup_et_statut(tmp_path):
    store = tmp_path / "p.json"
    pid = kp.add("src", "Faire X", path=store)
    assert pid.startswith("P-")
    assert kp.add("src", "Faire X", path=store) == pid  # dedup ouverte
    assert kp.set_status(pid, "valide", path=store) is True
    assert kp.set_status(pid, "nope", path=store) is False
    assert kp.set_status("P-20990101-99", "valide", path=store) is False
    pend = kp.pending(path=store)
    assert [p["id"] for p in pend] == [pid]
    kp.set_status(pid, "applique", path=store)
    assert kp.pending(path=store) == []


def test_budgets_quotidiens(tmp_path):
    store = tmp_path / "p.json"
    assert kp.budget_left("merge", path=store) == 1
    assert kp.budget_use("merge", path=store) is True
    assert kp.budget_left("merge", path=store) == 0
    assert kp.budget_use("merge", path=store) is False
    assert kp.budget_left("inconnu", path=store) == 0


def test_vacances_env(monkeypatch, tmp_path):
    monkeypatch.delenv("KURO_VACANCES", raising=False)
    assert kp.vacances(path=tmp_path / "v.flag") is False
    monkeypatch.setenv("KURO_VACANCES", "1")
    assert kp.vacances(path=tmp_path / "v.flag") is True


def test_clean_fr_sans_emoji():
    assert kp.clean_fr("✓ OK → fait · tout") == "OK OK -> fait - tout"
    assert kp.clean_fr("caf� chantier") == "caf? chantier"


def test_seen_marques(tmp_path):
    store = tmp_path / "p.json"
    assert kp.seen("k", path=store) is False
    kp.mark_seen("k", path=store)
    assert kp.seen("k", path=store) is True
