"""Tests kuro_skills — logique pure, fichiers temporaires, zéro réseau."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_skills as ks  # noqa: E402


# ---------- barre de progression ----------

def test_barre_proportionnelle():
    assert ks.bar(0) == "░" * 10
    assert ks.bar(100) == "█" * 10
    assert ks.bar(50) == "█████░░░░░"
    assert len(ks.bar(37)) == 10


# ---------- filtrage et renommage ----------

def test_hidden_skills_filtres():
    assert "pip" in ks.HIDDEN_SKILLS
    assert "npm" in ks.HIDDEN_SKILLS
    assert "Python" not in ks.HIDDEN_SKILLS


def test_rename_skills():
    assert ks.RENAME_SKILLS["github-actions"] == "GitHub Actions"
    assert ks.RENAME_SKILLS["docker"] == "Docker"


# ---------- bornes du score ----------

def test_pct_bornes():
    assert ks.MIN_PCT == 5
    assert ks.MAX_PCT == 95


def test_bar_plafonne_sans_depasser():
    out = ks.bar(120)
    assert out == "█" * 12  # 12 caractères mais jamais utilisé en pratique (pct<=95)


# ---------- rendu de section ----------

def _payload():
    return {
        "generated_at": "2026-08-23T12:00:00+02:00",
        "window_days": 90,
        "repo_count": 43,
        "skills": [
            {"name": "Python", "pct": 90, "kb": 5000, "repos": 37, "commits_90d": 319,
             "ci_green_frac": 0.75, "tests_frac": 0.5, "new": False},
            {"name": "Rust", "pct": 30, "kb": 400, "repos": 6, "commits_90d": 209,
             "ci_green_frac": 1.0, "tests_frac": 0.3, "new": True},
        ],
    }


def test_rendu_contient_pourcentages_et_preuves():
    section = ks.render_section(_payload())
    assert "**Python**" in section
    assert "90%" in section
    assert "37 repo(s)" in section
    assert "CI 75% vert" in section
    assert "🆕" in section  # Rust est nouveau


def test_rendu_limite_au_top():
    section = ks.render_section(_payload(), top=1)
    assert "Python" in section
    assert "+ 1 autres" in section
    assert "Rust" in section  # cité dans la ligne "autres"


# ---------- mise à jour README entre marqueurs ----------

def test_update_readme_insere_et_remplace(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        "# Skills\n\n"
        f"{ks.START_MARK}\nancien contenu\n{ks.END_MARK}\n\nsuite\n",
        encoding="utf-8",
    )
    changed = ks.update_readme(readme, "nouveau contenu")
    assert changed
    text = readme.read_text(encoding="utf-8")
    assert "ancien contenu" not in text
    assert "nouveau contenu" in text
    assert text.count(ks.START_MARK) == 1


def test_update_readme_inchange_si_identique(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text(
        f"# Skills\n\n{ks.START_MARK}\ncontenu\n{ks.END_MARK}\n",
        encoding="utf-8",
    )
    assert ks.update_readme(readme, "contenu") is False


def test_update_readme_echoue_sans_marqueurs(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("# Skills sans marqueurs\n", encoding="utf-8")
    try:
        ks.update_readme(readme, "x")
        raise AssertionError("SystemExit attendu")
    except SystemExit:
        pass
