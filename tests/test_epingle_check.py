"""Tests check_epingle_completeness — logique pure, zero git reseau."""

import check_epingle_completeness as cc


def test_error_owned_absent():
    e, w, i = cc.check(["Forma"], set(), {"forma": "OWNED"})
    assert e == [("Forma", "OWNED verifie mais absent d'Epingle — ajouter (R85)")]
    assert w == [] and i == []


def test_warn_fork_et_unknown():
    e, w, i = cc.check(["Py-Fork", "Mystere"],
                       set(),
                       {"py-fork": "OWNED", "mystere": "UNKNOWN"})
    assert e == []
    assert any(n == "Py-Fork" and "fork" in r for n, r in w)
    assert any(n == "Mystere" and "UNKNOWN" in r for n, r in w)


def test_info_sans_clone_et_alias_kuro():
    e, w, i = cc.check(["FuturProjet", "kuro"], {"kuroguardian"}, {})
    assert e == [] and w == []
    # kuro matche via alias -> rien ; FuturProjet sans clone -> info
    assert all(n != "kuro" for n, _ in e + w + i)
    assert i == [("FuturProjet", "suivi-sans-clone-local")]


def test_org_registry_inconnues():
    warns = cc.check_org_registry(
        {"Quant-Search": 2, "Lemniscate-world": 5},
        ("github.com/Lemniscate-world/",),
        ("github.com/Demeter-Financial-Labs/",))
    assert any(n == "Quant-Search" for n, _ in warns)
    assert all(n != "Lemniscate-world" for n, _ in warns)
