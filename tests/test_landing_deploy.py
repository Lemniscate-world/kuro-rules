import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from landing_deploy import build, build_checklist


def test_build_neuraldbg():
    html = build("neuraldbg", "https://example.com/checklist.pdf", "kuro@example.com")
    assert "<!DOCTYPE html>" in html
    assert "NeuralDBG" in html
    assert "https://example.com/checklist.pdf" in html
    assert "mailto:kuro@example.com" in html
    assert "337 clones" in html


def test_build_lifetrack():
    html = build("lifetrack", "https://example.com/reset.pdf", "kuro@example.com")
    assert "LifeTrack" in html and "Local-first" in html


def test_rejects_unknown_product():
    with pytest.raises(ValueError):
        build("nope", "https://example.com", "a@b.c")


def test_rejects_bad_url_and_contact():
    with pytest.raises(ValueError):
        build("neuraldbg", "fichier local avec espaces", "a@b.c")
    with pytest.raises(ValueError):
        build("neuraldbg", "https://example.com", "pas-un-email")


def test_relative_magret_allowed():
    html = build("neuraldbg", "checklist.html", "a@b.c")
    assert "checklist.html" in html


def test_build_checklist():
    html = build_checklist("neuraldbg", "a@b.c")
    assert html.count("<li>") == 7
    assert "landing.html" in html
    with pytest.raises(ValueError):
        build_checklist("nope", "a@b.c")


def test_offer_block_neuraldbg_only():
    n = build("neuraldbg", "checklist.html", "a@b.c")
    assert "Free private beta" in n
    assert "Beta%20application%20NeuralDBG" in n
    lt = build("lifetrack", "checklist.html", "a@b.c")
    assert "private beta" not in lt.lower()
