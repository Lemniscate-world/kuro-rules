"""Garde anti-regression leads (incident 2026-10-08 : 4 replies sans suivi).

4 replies (Velprium, Moto, TrainProof, BioTradingArena, 29/09->03/10) sont
restees sans suivi jusqu'au catch-up manuel du 08/10 car aucun run ne lisait
l'inbox. Cette garde verifie que la doc d'architecture versionnee impose
toujours : lecture inbox-first, garde replies-watch, statuts jamais relances.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC = ROOT / "ARCHITECTURE_AGENTS.md"


def _doc():
    return DOC.read_text(encoding="utf-8")


def test_doc_impose_inbox_first():
    txt = _doc()
    assert "IMAP" in txt
    assert "repondu/stop/lost" in txt


def test_doc_reference_garde_replies_watch():
    assert "replies-watch" in _doc()


def test_doc_rappelle_incident_suivi():
    assert "2026-10-08" in _doc()
