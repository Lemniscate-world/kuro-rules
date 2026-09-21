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


def test_track_new_reste_new_le_meme_jour(tmp_path, monkeypatch):
    monkeypatch.setattr(ks, "DECISIONS_FILE", tmp_path / "dec.json")
    first, _ = ks.track_decisions([("a", "Texte A")])
    assert first[0]["status"] == "NEW"
    second, _ = ks.track_decisions([("a", "Texte A")])
    assert second[0]["status"] == "NEW"
    assert second[0]["age_days"] == 0


def test_track_resolved_puis_reouverture(tmp_path, monkeypatch):
    import json
    from datetime import date, timedelta
    store = tmp_path / "dec.json"
    monkeypatch.setattr(ks, "DECISIONS_FILE", store)
    ks.track_decisions([("a", "Texte A"), ("b", "Texte B")])
    # Simule le lendemain : "a" devient OPEN avec age, "b" disparait -> RESOLVED
    raw = json.loads(store.read_text(encoding="utf-8"))
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    for v in raw.values():
        v["first_seen"] = yesterday
    store.write_text(json.dumps(raw), encoding="utf-8")
    opened, resolved = ks.track_decisions([("a", "Texte A")])
    assert [(d["key"], d["status"], d["age_days"]) for d in opened] == [("a", "OPEN", 1)]
    assert [(r["key"], r["status"]) for r in resolved] == [("b", "RESOLVED")]
    reopened, still = ks.track_decisions([("a", "Texte A"), ("b", "Texte B v2")])
    assert {d["key"]: d["status"] for d in reopened} == {"a": "OPEN", "b": "NEW"}
    assert still == []


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


def test_plan_compliance_detecte_sans_plan(tmp_path):
    (tmp_path / "RepoA" / ".git").mkdir(parents=True)
    (tmp_path / "RepoB" / ".git").mkdir(parents=True)
    (tmp_path / "RepoB" / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    (tmp_path / "NotaRepo").mkdir()
    out = ks.plan_compliance(tmp_path)
    assert out["total"] == 2
    assert out["sans_plan"] == ["RepoA"]
    assert out["actifs_sans_cap"] == []  # velocite inconnue en test -> pas d'exigence


def test_plan_compliance_actifs_sans_cap(tmp_path, monkeypatch):
    (tmp_path / "Actif" / ".git").mkdir(parents=True)
    (tmp_path / "Actif" / "PLAN.md").write_text("# plan\n", encoding="utf-8")
    import kuro_metrics
    monkeypatch.setattr(kuro_metrics, "build_payload",
                        lambda **k: {"projects": [{"name": "Actif", "velocity_per_week": 3.0}]})
    out = ks.plan_compliance(tmp_path)
    assert out["actifs_sans_cap"] == ["Actif"]


def test_campaign_guerre_bataille_gate():
    metrics = {"averages": {"velocity_per_week": 2.0},
               "projects": [{"name": "Top", "velocity_per_week": 4.0, "ci_failures": 1}],
               "pivot_candidates": []}
    okrs = [{"key": "m", "label": "MRR", "target": 100, "current": 10.0, "pct": 10, "hit": False}]
    camp = ks.campaign(metrics, okrs, {"last": None}, {"sans_plan": ["X"]})
    assert "MRR" in camp["guerre"]
    assert "Top" in camp["bataille"]
    assert "CI en echec" in camp["gate_necessite"]
    assert "R105" in camp["gate_consequences"]
    assert "sans PLAN" in camp["arene"]


def test_decisions_plans_et_render_campagne():
    d = ks.decisions(FINANCE, METRICS, {"overall": "green", "total": 10, "failures": 0}, [],
                     {"interviews_7d": 2},
                     {"sans_plan": ["A", "B"], "actifs_sans_cap": ["C"]})
    assert any("sans PLAN.md" in x for x in d)
    assert any("sans sous-plan" in x for x in d)
    text = ks.render({
        "generated_at": "2026-09-20T10:00:00+02:00",
        "finance": {"cash": 0, "burn": 1, "mrr": 0, "runway_label": "x", "status": "s"},
        "execution": {"velocity": 1, "lead_time": 2, "ci": {"total": 1, "failures": 0}},
        "okr": [], "pipeline": {"total": 0, "interviews_7d": 0, "last_insight": None, "next_steps": []},
        "decisions": [],
        "campaign": {"guerre": "G", "bataille": "B", "arene": "A",
                     "gate_necessite": "N", "gate_consequences": "C"},
        "plans": {"sans_plan": ["A"], "actifs_sans_cap": []},
    })
    assert "Campagne" in text and "Gate" in text and "sans PLAN.md" in text
