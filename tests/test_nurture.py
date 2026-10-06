import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import nurture
from nurture import add, advance, due, mark_lost


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(nurture, "STORE", tmp_path / "nurture.local.json")


def test_add_and_dedupe():
    fiche = add("alice", "reddit", "debug NaN")
    assert fiche["stage"] == "lead"
    with pytest.raises(ValueError):
        add("alice", "x", "doublon")
    with pytest.raises(ValueError):
        add("  ", "x", "vide")


def test_advance_chain():
    add("bob", "hn", "quant")
    assert advance("bob", "a répondu", "2026-10-02")["stage"] == "contact"
    assert advance("bob", "call jeudi")["stage"] == "call"
    assert advance("bob", "")["stage"] == "client"
    with pytest.raises(ValueError):
        advance("bob", "trop loin")


def test_advance_unknown():
    with pytest.raises(KeyError):
        advance("fantome", "x")


def test_lost_and_due():
    add("carol", "discord", "habits")
    advance("carol", "échange", "2026-09-20")
    assert "carol" in due("2026-09-28")
    mark_lost("carol", "pas de fit")
    assert "carol" not in due("2026-09-28")


def test_due_empty_next_excluded():
    add("dave", "x", "veille")
    assert "dave" not in due("2026-09-28")
