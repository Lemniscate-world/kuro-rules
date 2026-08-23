"""Tests kuro_finance + kuro_metrics — logique pure, fichiers temporaires, zéro réseau."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_finance as kf  # noqa: E402
import kuro_metrics as km  # noqa: E402


def base_data(**over):
    data = {
        "currency": "USD",
        "starting_cash": 25,
        "months": [
            {"month": "2026-05", "expenses": [{"label": "a", "amount": 25}], "revenues": []},
            {"month": "2026-06", "expenses": [{"label": "b", "amount": 25}], "revenues": []},
        ],
    }
    data.update(over)
    return data


# ---------- calculs de base ----------

def test_burn_et_runway_critiques(tmp_path):
    payload = kf.compute(base_data(), source_file=tmp_path / "f.json")
    assert payload["burn_rate_monthly"] == 25.0
    assert payload["net_burn_monthly"] == 25.0
    assert payload["runway_months"] == 1.0
    assert payload["status"] == "critical"


def test_runway_infini_si_les_revenus_couvrent_le_burn(tmp_path):
    data = base_data()
    data["months"][0]["revenues"] = [{"label": "vente", "amount": 100}]
    data["months"][1]["revenues"] = [{"label": "vente", "amount": 100}]
    payload = kf.compute(data, source_file=tmp_path / "f.json")
    assert payload["mrr_monthly"] == 100.0
    assert payload["net_burn_monthly"] == -75.0
    assert payload["runway_months"] is None
    assert payload["status"] == "healthy"


def test_runway_zero_si_tresorerie_vide(tmp_path):
    payload = kf.compute(base_data(starting_cash=0), source_file=tmp_path / "f.json")
    assert payload["runway_months"] == 0.0


def test_fenetre_glissante_limite_l_analyse(tmp_path):
    months = [
        {"month": f"2026-0{i}", "expenses": [{"label": "x", "amount": float(i * 10)}], "revenues": []}
        for i in range(1, 5)
    ]
    payload = kf.compute(base_data(months=months), window=2, source_file=tmp_path / "f.json")
    assert payload["months_analyzed"] == 2
    assert payload["burn_rate_monthly"] == 35.0


# ---------- erreurs fichier ----------

def test_fichier_manquant_message_aide():
    try:
        kf.load_finances(Path("inexistant-finances.json"))
        raise AssertionError("FinanceError attendu")
    except kf.FinanceError as exc:
        assert "example" in str(exc)


def test_json_invalide_leve_erreur(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{oops", encoding="utf-8")
    try:
        kf.load_finances(p)
        raise AssertionError("FinanceError attendu")
    except kf.FinanceError:
        pass


# ---------- formatage monnaie ----------

def test_format_usd_deux_decimales():
    assert kf.fmt_amount(12.5, "USD") == "$12.50"


def test_format_fcfa_sans_decimales():
    assert kf.fmt_amount(1500, "FCFA").endswith("FCFA")
    out = kf.fmt_amount(1500, "XOF")
    assert "." not in out
    assert "1 500" in out


# ---------- unit economics (CAC / LTV) ----------

def test_unit_economics_saines(tmp_path):
    data = base_data(acquisition={
        "monthly_marketing_spend": 30,
        "new_customers_per_month": 3,
        "arpu_monthly": 15,
        "gross_margin_pct": 80,
        "avg_customer_lifetime_months": 12,
    })
    ue = kf.compute(data, source_file=tmp_path / "f.json")["unit_economics"]
    assert ue["configured"]
    assert ue["cac"] == 10.0
    assert ue["ltv"] == 144.0
    assert ue["ltv_cac_ratio"] >= 3
    assert ue["status"] == "healthy"


def test_unit_economics_incomplete_si_donnees_partielles(tmp_path):
    data = base_data(acquisition={
        "monthly_marketing_spend": 30,
        "new_customers_per_month": 3,
    })
    ue = kf.compute(data, source_file=tmp_path / "f.json")["unit_economics"]
    assert ue["configured"]
    assert ue["cac"] == 10.0
    assert ue["ltv"] is None
    assert ue["ltv_cac_ratio"] is None
    assert ue["status"] == "incomplete"


def test_unit_economics_absente_par_defaut(tmp_path):
    ue = kf.compute(base_data(), source_file=tmp_path / "f.json")["unit_economics"]
    assert not ue["configured"]
    assert ue["status"] == "idle"


# ---------- historique & tendance ----------

def test_tendance_calcule_les_deltas():
    previous = {
        "at": "2026-08-01T10:00:00+00:00",
        "runway_months": 2.5,
        "burn_rate_monthly": 20.0,
    }
    current = {"at": "2026-08-22T10:00:00+00:00", "runway_months": 1.0, "burn_rate_monthly": 25.0}
    trend = kf.build_trend(previous, current)
    assert trend["previous_at"] == previous["at"]
    assert trend["runway_delta_months"] == -1.5
    assert trend["burn_delta"] == 5.0


def test_tendance_sur_champs_manquants_est_sure():
    trend = kf.build_trend({}, {})
    assert trend["runway_delta_months"] is None
    assert trend["burn_delta"] is None


def test_historique_append_puis_trim(tmp_path, monkeypatch):
    hist = tmp_path / "hist.jsonl"
    monkeypatch.setattr(kf, "HISTORY_MAX_LINES", 3)
    payload = kf.compute(base_data(), source_file=tmp_path / "f.json")
    for _ in range(4):
        assert kf.append_history(payload, path=hist)
    lines = hist.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    entry = json.loads(lines[-1])
    assert entry["runway_months"] == 1.0
    assert entry["status"] == "critical"


def test_second_releve_produit_une_tendance(tmp_path, monkeypatch):
    hist = tmp_path / "hist.jsonl"
    monkeypatch.setattr(kf, "HISTORY_FILE", hist)
    data_file = tmp_path / "f.json"
    data_file.write_text(json.dumps(base_data()), encoding="utf-8")
    first = kf.compute_from_default(path=data_file, keep_history=True)
    assert "trend" not in first
    second = kf.compute_from_default(path=data_file, keep_history=True)
    assert second["trend"]["previous_at"] == first["computed_at"]
    assert second["trend"]["runway_delta_months"] == 0.0


# ---------- kuro_metrics (parsing pur) ----------

def test_ci_failure_by_repo_calcule_le_taux():
    ci = {
        "repos": [
            {
                "name": "org/LifeTrack",
                "workflows": [{"conclusion": "failure"}, {"conclusion": "success"}],
            }
        ]
    }
    table = km.ci_failure_by_repo(ci)
    assert table["LifeTrack"]["total"] == 2
    assert table["LifeTrack"]["failures"] == 1
    assert abs(table["LifeTrack"]["failure_rate"] - 0.5) < 1e-9


def test_ci_table_vide_sur_entree_invalide():
    assert km.ci_failure_by_repo(None) == {}
    assert km.ci_failure_by_repo({}) == {}


def test_ci_ignore_les_workflows_vides():
    ci = {"repos": [{"name": "org/X", "workflows": []}]}
    assert km.ci_failure_by_repo(ci) == {}
