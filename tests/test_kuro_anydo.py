"""Tests kuro_anydo — confinement sorties + allowlist endpoint (logique pure)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_anydo as ka  # noqa: E402


def test_confined_out_refuse_evasion():
    assert ka._confined_out(Path("/etc/passwd"), "x.json") == ka.ROOT / "x.json"
    assert ka._confined_out(ka.ROOT / "sub" / "x.json", "x.json") == ka.ROOT / "x.json"


def test_allow_endpoint():
    assert ka._allow_endpoint("/messages?session=1") == "https://mcp.any.do/messages?session=1"
    assert ka._allow_endpoint("https://evil.example/hook") is None
    assert ka._allow_endpoint("http://mcp.any.do/x") is None


def test_match_projects_epingle_absente_isolee(monkeypatch):
    monkeypatch.setattr(ka, "_load_projects", lambda: None)
    r = ka.match_projects([{"title": "x"}])
    assert set(r) == {"error"}
    assert "Epingle" in r["error"]
