import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from cta_kit import CTA, MAGNETS, cta, utm


def test_utm_basic():
    out = utm("https://github.com/org/repo", "reddit", "social", "checklist")
    assert out == "https://github.com/org/repo?utm_source=reddit&utm_medium=social&utm_campaign=checklist"


def test_utm_keeps_existing_query():
    out = utm("https://example.com/p?x=1", "x", "social", "hub")
    assert "x=1" in out and "utm_source=x" in out


def test_utm_rejects_bad_url():
    with pytest.raises(ValueError):
        utm("not a url", "x")
    with pytest.raises(ValueError):
        utm("ftp://example.com/f", "x")
    with pytest.raises(ValueError):
        utm("", "x")


def test_cta_all_channels():
    for channel in CTA:
        text = cta(channel, "https://example.com/m?utm_source=t")
        assert "https://example.com/m" in text
        assert "{url}" not in text


def test_cta_unknown_channel():
    with pytest.raises(ValueError):
        cta("fax", "https://example.com")


def test_magnets_registry_shape():
    assert len(MAGNETS) >= 2
    for slug, m in MAGNETS.items():
        assert slug and m["title"] and m["promise"] and m["format"] and m["audience"]
