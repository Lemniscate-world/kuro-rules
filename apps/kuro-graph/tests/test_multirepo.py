import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GRAPH = ROOT / "apps" / "kuro-graph"
sys.path.insert(0, str(GRAPH))

import ecosystem as eco
from state import new_state
from nodes_multirepo import node_fanout, node_impact, route_after_fanout


def test_classify_remote_owned():
    assert eco.classify_remote("https://github.com/Lemniscate-world/LifeTrack.git") == "OWNED"
    assert eco.classify_remote("https://github.com/pbakaus/forma.git") == "OWNED"
    assert eco.classify_remote("https://github.com/Lemniscate-SHA-256/x.git") == "OWNED"


def test_classify_remote_external_unknown():
    assert eco.classify_remote("https://github.com/Demeter-Financial-Labs/y.git") == "EXTERNAL"
    assert eco.classify_remote("https://github.com/Quant-Search/OpenQuant.git") == "UNKNOWN"
    assert eco.classify_remote("") == "UNKNOWN"


def test_sync_scope_guard():
    assert eco.sync_scope("OWNED") == "full"
    assert eco.sync_scope("EXTERNAL") == "redirector-only"
    assert eco.sync_scope("UNKNOWN") == "redirector-only"


def test_build_impact_shape():
    impact = eco.build_impact("read-only audit", {"LifeTrack": {}, "Forma": {}})
    assert impact["impacted"] == ["Forma", "LifeTrack"]
    assert impact["breaking"] is False
    assert impact["matrix_updated"] is False
    breaking = eco.build_impact("BREAKING interface change", {"LifeTrack": {}})
    assert breaking["breaking"] is True


def test_fanout_unknown_dirs_no_fail(tmp_path, monkeypatch):
    a = tmp_path / "LifeTrack"
    b = tmp_path / "Forma"
    a.mkdir()
    b.mkdir()
    monkeypatch.setattr(eco, "DOCUMENTS", tmp_path)
    monkeypatch.setattr(eco, "pilot_paths", lambda documents=None: [a, b])
    out = node_fanout(new_state())
    # Pas de .git -> UNKNOWN -> skip trace, 0 fail.
    assert out["fails"] == 0
    assert out["repos"]["LifeTrack"]["label"] == "UNKNOWN"
    assert out["repos"]["Forma"]["label"] == "UNKNOWN"
    assert route_after_fanout(out) == "end"


def test_fanout_owned_reads_summary(tmp_path, monkeypatch):
    a = tmp_path / "LifeTrack"
    a.mkdir()
    (a / "SESSION_SUMMARY.md").write_text("# Test\nprogres 10%\n", encoding="utf-8")
    monkeypatch.setattr(eco, "pilot_paths", lambda documents=None: [a])
    monkeypatch.setattr(eco, "classify_repo", lambda p: ("OWNED", "https://github.com/Lemniscate-world/LifeTrack.git"))
    out = node_fanout(new_state())
    assert out["repos"]["LifeTrack"]["audited"] is True
    assert out["repos"]["LifeTrack"]["summary_chars"] > 0
    assert route_after_fanout(out) == "impact"
    out2 = node_impact({**out, "multirepo_change": "read-only audit"})
    assert out2["ecosystem_impact"]["impacted"] == ["LifeTrack"]
    assert out2["multirepo_audited"] == ["LifeTrack"]
