"""Tests kuro_strategy — OKR, pipeline, décisions (logique pure)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_strategy as ks  # noqa: E402


FINANCE = {"mrr_monthly": 50.0, "runway_months": 1.0, "burn_rate_monthly": 25.0, "starting_cash": 0.0, "status": "critical"}
METRICS = {"averages": {"velocity_per_week": 1.06, "lead_time_days": 47.2}}
PIPELINE = {"interviews_7d": 1, "total": 4}


def test_resolve_metric_finance():
    assert ks.resolve_metric("finance.mrr", {}, FINANCE, METRICS, PIPELINE) == 50.0


def test_resolve_metric_runway_null_sur_infini():
    f = dict(FINANCE, runway_months=None)
    assert ks.resolve_metric("finance.runway", {}, f, METRICS, PIPELINE) is None


def test_resolve_metric_manual():
    assert ks.resolve_metric("manual", {"current": 2}, FINANCE, METRICS, PIPELINE) == 2.0


def test_resolve_metric_pipeline():
    assert ks.resolve_metric("pipeline.interviews_7d", {}, FINANCE, METRICS, PIPELINE) == 1.0


def test_okr_progress_hit_et_miss():
    okrs = [
        {"key": "a", "label": "A", "target": 100, "metric": "finance.mrr"},
        {"key": "b", "label": "B", "target": 1, "metric": "pipeline.interviews_7d"},
    ]
    out = ks.okr_progress(okrs, FINANCE, METRICS, PIPELINE)
    assert out[0]["hit"] is False and out[0]["pct"] == 50
    assert out[1]["hit"] is True and out[1]["pct"] == 100


def test_decisions_runway_critique():
    d = ks.decisions(FINANCE, METRICS, {"overall": "green", "total": 10, "failures": 0}, [], {"interviews_7d": 1})
    assert any("Runway critique" in x for x in d)


def test_decisions_pipeline_vide():
    d = ks.decisions(FINANCE, METRICS, {"overall": "green", "total": 10, "failures": 0}, [], {"interviews_7d": 0})
    assert any("Pipeline vide" in x for x in d)


def test_decisions_okr_sous_50():
    okrs = [{"key": "m", "label": "MRR", "target": 100, "current": 10.0, "pct": 10, "hit": False}]
    d = ks.decisions(FINANCE, METRICS, {"overall": "green", "total": 10, "failures": 0}, okrs, {"interviews_7d": 2})
    assert any("MRR" in x for x in d)


def test_decisions_aucune_si_vert():
    okrs = [{"key": "m", "label": "MRR", "target": 100, "current": 100.0, "pct": 100, "hit": True}]
    d = ks.decisions(
        {"runway_months": 12, "status": "healthy"},
        {"averages": {"velocity_per_week": 5}},
        {"overall": "green", "total": 10, "failures": 0},
        okrs,
        {"interviews_7d": 3},
    )
    assert d == []


def test_render_contient_les_sections():
    payload = ks.build_payload.__wrapped__() if hasattr(ks.build_payload, "__wrapped__") else None
    sample = {
        "generated_at": "2026-08-24T10:00:00+02:00",
        "finance": {"cash": 0, "burn": 25.0, "mrr": 0.0, "runway_label": "0 (trésorerie vide)", "status": "critical"},
        "execution": {"velocity": 1.06, "lead_time": 47.2, "ci": {"overall": "green", "total": 38, "failures": 0}},
        "okr": [{"key": "a", "label": "A", "target": 3, "current": 1.0, "pct": 33, "hit": False}],
        "pipeline": {"total": 1, "interviews_7d": 1, "last_insight": "douleur X", "next_steps": ["suivi"]},
        "decisions": ["Runway critique"],
    }
    text = ks.render(sample)
    assert "DIGEST STRATÉGIQUE" in text
    assert "OKR:" in text
    assert "Pipeline" in text
    assert "Runway critique" in text
    assert payload is None  # build_payload n'est pas wrappé, garde-fou du test
