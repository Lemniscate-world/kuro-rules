"""Tests gen_x_posts — logique pure, sans reseau ni git reel (R102)."""

import sys
from datetime import date, timedelta
from pathlib import Path

import gen_x_posts as gx


def test_classify_ownership_owned():
    assert gx.classify_ownership("origin https://github.com/Lemniscate-world/Foo.git") == "OWNED"
    assert gx.classify_ownership("origin https://github.com/LambdaSection/Bar.git") == "OWNED"
    assert gx.classify_ownership("origin https://github.com/pbakaus/Baz.git") == "OWNED"


def test_classify_ownership_orgs_satellites():
    assert gx.classify_ownership("origin https://github.com/Quant-Search/OpenQuant.git") == "OWNED"
    assert gx.classify_ownership("origin https://github.com/HeliumXChain/Helium.git") == "OWNED"
    assert gx.classify_ownership("origin https://github.com/AI8-Algorithm-Intelligence-Section-8/Dissect.git") == "OWNED"
    assert gx.classify_ownership("origin https://github.com/Demeter-Financial-Labs/X.git") == "EXTERNAL"
    assert gx.classify_ownership("") == "UNKNOWN"
    assert gx.classify_ownership("origin https://github.com/random/Repo.git") == "UNKNOWN"


def test_is_eligible_owned_actif_uniquement():
    assert gx.is_eligible("Actif", "OWNED") is True
    assert gx.is_eligible("Validation", "OWNED") is True
    assert gx.is_eligible("Actif", "EXTERNAL") is False
    assert gx.is_eligible("Actif", "UNKNOWN") is False
    assert gx.is_eligible("Archive", "OWNED") is False
    assert gx.is_eligible("En Pause", "OWNED") is False
    assert gx.is_eligible("Prototypage", "OWNED") is False


def test_velocity_score_recompense_fraicheur():
    today = date.today().isoformat()
    old = (date.today() - timedelta(days=100)).isoformat()
    fresh = gx.velocity_score({"c30": 10, "date": today})
    stale = gx.velocity_score({"c30": 10, "date": old})
    assert fresh > stale
    assert gx.velocity_score(None) < -100


def test_format_post_contraintes_r94(monkeypatch):
    monkeypatch.setattr(gx, "voice_for", lambda *a, **k: "log")
    facts = {"hash": "abc1234", "msg": "fix: moteur causal", "c30": 12, "c7": 3}
    post = gx.format_post("NeuralDBG", 57, "Actif", facts)
    assert gx.x_len(post) <= 280
    assert "#NeuralDBG" in post
    assert "12 commits 30j" in post
    assert "Correctif" in post and "explique les" in post
    assert "abc1234" not in post and "demain" not in post.lower()
    assert "https://github.com/LambdaSection/NeuralDBG" in post


def test_sanitize_redacte_secrets_et_paths():
    s = gx.sanitize("api_key: abc123 C:\\Users\\x\\secret msg /home/u/f.txt")
    assert "abc123" not in s
    assert "C:\\Users" not in s
    assert "/home/u" not in s


def test_select_top_owned_only(monkeypatch, tmp_path):
    projs = [
        {"name": "Alpha", "pct": 50, "status": "Actif", "desc": "", "external_section": False},
        {"name": "Beta", "pct": 40, "status": "Actif", "desc": "", "external_section": False},
        {"name": "Gamma", "pct": 60, "status": "Actif", "desc": "", "external_section": True},
    ]
    today = date.today().isoformat()
    facts_map = {
        "Alpha": {"hash": "a1", "date": today, "msg": "gros fix", "c30": 20, "c7": 5, "branch": "main", "dirty": False},
        "Beta": {"hash": "b1", "date": today, "msg": "petit fix", "c30": 2, "c7": 1, "branch": "main", "dirty": False},
    }
    own_map = {"Alpha": "OWNED", "Beta": "EXTERNAL"}
    monkeypatch.setattr(gx, "find_repo", lambda n, _idx=None: Path("/fake") / n)
    monkeypatch.setattr(gx, "get_ownership", lambda p: own_map.get(p.name, "UNKNOWN"))
    monkeypatch.setattr(gx, "collect_velocity", lambda p: facts_map.get(p.name))
    selected, skipped = gx.select_top(projs, 3, docs_dir=str(tmp_path))
    names = [r["project"]["name"] for r in selected]
    assert names == ["Alpha"]
    assert any(s[0] == "Beta" for s in skipped)
    assert any(s[0] == "Gamma" for s in skipped)


def test_write_drafts_hub_et_projet(tmp_path):
    today = date.today().isoformat()
    facts = {"hash": "abc1234", "date": today, "msg": "fix test", "c30": 5, "c7": 2, "branch": "main", "dirty": False}
    selected = [{"project": {"name": "Alpha", "pct": 42, "status": "Actif", "desc": ""},
                 "facts": facts, "ownership": "OWNED", "score": 25}]
    written = gx.write_drafts(selected, tmp_path, today=today)
    assert len(written) == 2  # projet + HUB
    paths = [Path(p) for _, p, _ in written]
    assert all(p.exists() for p in paths)
    for p in paths:
        assert len(p.read_text(encoding="utf-8")) <= 300


def test_load_projects_inclut_laboratoire(tmp_path):
    ep = tmp_path / "Epingle.md"
    ep.write_text(
        "## λ-Section-1 — Test\n\n"
        "| Projet | Progression | Statut | Description |\n"
        "|---|---|---|---|\n"
        "| **Alpha** | 50% | Actif | desc |\n\n"
        "## Laboratoire — Labo\n\n"
        "| Projet | Progression | Statut | Description |\n"
        "|---|---|---|---|\n"
        "| **Horcruxe Labs** | 45% | Actif | labo |\n",
        encoding="utf-8",
    )
    projs = gx.load_projects(ep)
    names = [p["name"] for p in projs]
    assert "Alpha" in names
    assert "Horcruxe Labs" in names


def test_build_repo_index_dir_absent_ne_crashe_pas(tmp_path):
    assert gx.build_repo_index(tmp_path / "n-existe-pas") == {}

def test_build_repo_index_ne_reient_que_git(tmp_path):
    (tmp_path / "Alpha" / ".git").mkdir(parents=True)
    (tmp_path / "Beta").mkdir()
    idx = gx.build_repo_index(tmp_path)
    assert set(idx) == {"alpha"}
    assert gx.find_repo("ALPHA", idx) == tmp_path / "Alpha"
    assert gx.find_repo("Beta", idx) is None


def test_select_top_docs_absents_tout_skip_sans_crash(tmp_path):
    projs = [{"name": "Alpha", "pct": 50, "status": "Actif",
              "desc": "", "external_section": False}]
    selected, skipped = gx.select_top(projs, 3, docs_dir=str(tmp_path / "vide"))
    assert selected == []
    assert skipped == [("Alpha", "no-local-repo")]


def test_write_drafts_vide_sans_hub(tmp_path):
    assert gx.write_drafts([], tmp_path, today="2026-01-01") == []
    assert list(tmp_path.glob("*.md")) == []


def test_write_drafts_slugs_dedupliques(tmp_path):
    facts = {"hash": "a1", "date": "2026-09-21", "msg": "x", "c30": 1,
             "c7": 1, "branch": "main", "dirty": False}
    sel = [
        {"project": {"name": "A B", "pct": 10, "status": "Actif", "desc": ""},
         "facts": facts, "ownership": "OWNED", "score": 5},
        {"project": {"name": "A-B", "pct": 10, "status": "Actif", "desc": ""},
         "facts": facts, "ownership": "OWNED", "score": 4},
    ]
    written = gx.write_drafts(sel, tmp_path, today="2026-01-01")
    slugs = sorted(Path(p).stem for _, p, _ in written if "HUB" not in p)
    assert len(set(slugs)) == len(slugs)


def test_ascii_log_garde_accents_supprime_emojis():
    assert gx.ascii_log("Déjà café \U0001F680 ok") == "Déjà café  ok"


def test_load_projects_inexistant_leve_runtimeerror(tmp_path):
    try:
        gx.load_projects(tmp_path / "absent.md")
    except RuntimeError:
        return
    raise AssertionError("RuntimeError attendue")


def test_select_only_force_sans_cutoff(monkeypatch, tmp_path):
    projs = [
        {"name": "Alpha", "pct": 50, "status": "Actif", "desc": "", "external_section": False},
        {"name": "Beta", "pct": 40, "status": "Actif", "desc": "", "external_section": False},
    ]
    today = date.today().isoformat()
    facts_map = {
        "Alpha": {"hash": "a1", "date": today, "msg": "gros", "c30": 20, "c7": 5,
                  "branch": "main", "dirty": False},
        "Beta": {"hash": "b1", "date": today, "msg": "petit", "c30": 1, "c7": 0,
                 "branch": "main", "dirty": False},
    }
    monkeypatch.setattr(gx, "find_repo", lambda n, _idx=None: Path("/fake") / n)
    monkeypatch.setattr(gx, "get_ownership", lambda p: "OWNED")
    monkeypatch.setattr(gx, "collect_velocity", lambda p: facts_map.get(p.name))
    top, _ = gx.select_top(projs, 1, docs_dir=str(tmp_path))
    assert [r["project"]["name"] for r in top] == ["Alpha"]
    forced, skipped = gx.select_only(projs, ["beta", "Inconnu"], docs_dir=str(tmp_path))
    assert [r["project"]["name"] for r in forced] == ["Beta"]
    assert skipped == [("Inconnu", "inconnu-epingle")]


def test_find_repo_alias_kuroguardian(tmp_path):
    (tmp_path / "kuro" / ".git").mkdir(parents=True)
    idx = gx.build_repo_index(tmp_path)
    assert gx.find_repo("KuroGuardian", idx) == tmp_path / "kuro"


def test_is_tracked_alias_et_direct():
    names = {"kuroguardian", "helium"}
    assert gx.is_tracked("KuroGuardian", names) is True
    assert gx.is_tracked("kuro", names) is True
    assert gx.is_tracked("Inconnu", names) is False


def test_write_drafts_nettoie_stale_meme_date(tmp_path):
    facts = {"hash": "a1", "date": "2026-09-21", "msg": "x", "c30": 1,
             "c7": 1, "branch": "main", "dirty": False}
    stale = tmp_path / "x_post_2026-01-01-sorti.md"
    stale.write_text("vieux", encoding="utf-8")
    autres = tmp_path / "x_post_2025-01-01-garde.md"
    autres.write_text("autre date", encoding="utf-8")
    sel = [{"project": {"name": "Alpha", "pct": 42, "status": "Actif", "desc": ""},
            "facts": facts, "ownership": "OWNED", "score": 25}]
    gx.write_drafts(sel, tmp_path, today="2026-01-01")
    assert not stale.exists()
    assert autres.exists()
    assert (tmp_path / "x_post_2026-01-01.md").exists()


def test_lint_bloque_alpha_openquant():
    assert gx.lint_post("OpenQuant", "gates anti edge avec sharpe 2.1") == ["edge", "sharpe"]
    assert gx.lint_post("OpenQuant", "12 commits 30j, 59% Actif.") == []
    assert gx.lint_post("Helium", "edge computing mesh") == []
    assert "sidak" in gx.lint_post("OpenQuant", "seuil t calibre Sidak, bootstrap prefere")
    assert "seuil" in gx.lint_post("OpenQuant", "seuil t calibre Sidak, bootstrap prefere")


def test_format_post_safe_fallback_generique():
    facts = {"hash": "a1", "date": "2026-09-21",
             "msg": "feat(edge): nouveau signal alpha sharpe", "c30": 9,
             "c7": 2, "branch": "main", "dirty": False}
    post = gx.format_post_safe("OpenQuant", 59, "Actif", facts)
    assert post is not None and len(post) <= 280
    assert gx.lint_post("OpenQuant", post) == []
    assert "fonctionnalités" in post


def test_format_post_safe_none_si_sans_fallback(monkeypatch):
    monkeypatch.setitem(gx.POSTING_STRATEGIES, "openquant",
                        {"never": ["x"], "generic_fallback": False})
    facts = {"hash": "a1", "date": "2026-09-21", "msg": "x releve", "c30": 1,
             "c7": 0, "branch": "main", "dirty": False}
    assert gx.format_post_safe("OpenQuant", 1, "Actif", facts) is None


def test_format_long_contenu_sans_promesse():
    facts = {"hash": "a1", "date": "2026-09-21", "msg": "fix cache", "c30": 3,
             "c7": 1, "branch": "main", "dirty": True}
    long = gx.format_long("Helium", 28, "Actif", facts, "Blockchain Rust.")
    assert "GPU" in long and "Caption X" in long
    assert "Travaux réalisés" in long and "Prochaine étape" in long
    assert "demain" not in long.lower() and len(long) <= 1900


def test_lint_universel_partout():
    assert "email" in gx.lint_post("Helium", "contact jean@exemple.com pour suite")
    assert "secret" in gx.lint_post("Helium", "api_key: abc123 ici")
    assert "chemin-local" in gx.lint_post("Helium", "voir C:\\Users\\x\\f.txt")
    assert "blob-secret" in gx.lint_post("Helium", "cle " + "a" * 40)
    assert "telephone" in gx.lint_post("Helium", "appeler le +228 90 11 22 33")
    assert "montant" in gx.lint_post("Helium", "budget 5000 € validé")
    assert "ip-privee" in gx.lint_post("Helium", "noeud 192.168.1.10 up")
    assert gx.lint_post("Helium", "12 commits 30j, 28% Actif.") == []


def test_lint_strategies_projets():
    assert gx.lint_post("NeuralDBG-Engine", "nouvelle heuristique de tri") != []
    assert gx.lint_post("Forma", "dossier assuré Dupont traité") != []
    assert gx.lint_post("LifeTrack", "suivi dose et traitement") != []
    assert gx.lint_post("Helium", "rotation seed des noeuds") != []
    assert gx.lint_post("Horcruxe Labs", "prépare soumission du papier") != []
    assert gx.lint_post("Helium", "mesh P2P installable en une commande") == []


def test_split_conventional():
    assert gx.split_conventional("feat(mesh): install en 1 commande") == ("Nouveau", "install en 1 commande")
    assert gx.split_conventional("maintenance courante") == (None, "maintenance courante")


def test_is_trivia_filtre():
    assert gx.is_trivia("chore: fix pre-commit remove kuro audit local hook")
    assert gx.is_trivia("Merge branch 'main' into x")
    assert gx.is_trivia("fix: typo dans le README")
    assert gx.is_trivia("fix(discord): 'papier' partout au lieu de 'fictif'")
    assert not gx.is_trivia("feat(mesh): install en 1 commande")
    assert not gx.is_trivia("fix(engine): repair RL demo contract")


def test_week_themes_agrege(monkeypatch, tmp_path):
    subs = ["chore: fix pre-commit hook",
            "feat(mesh): install en 1 commande",
            "fix: typo",
            "perf(api): cache 10x plus rapide"]
    monkeypatch.setattr(gx, "collect_week_subjects", lambda p, days=7, limit=30: subs)
    assert gx.week_themes(tmp_path) == ["Install en 1 commande", "Cache 10x plus rapide"]


def test_format_post_themes_multi(monkeypatch):
    monkeypatch.setattr(gx, "voice_for", lambda *a, **k: "log")
    facts = {"hash": "a1", "msg": "x", "c30": 9, "c7": 3,
             "themes": ["Install en 1 commande", "Releases publiées"]}
    post = gx.format_post("Helium", 28, "Actif", facts)
    assert "Install en 1 commande et releases publiées" in post
    assert "a1" not in post and gx.x_len(post) <= 280
    assert "https://github.com/HeliumXChain/Helium" in post


def test_voix_rotation_4_formats():
    th = ["Mesh installable", "Releases"]
    assert "Ce qu'on a appris sur H" in gx.voice_line1("H", "tag", th, "m", "lecon")
    assert gx.voice_line1("H", "tag", th, "9 commits", "chiffre").startswith("H : 9 commits")
    assert "vous gérez ça comment" in gx.voice_line1("H", "tag", th, "m", "question")
    assert "Mesh installable et releases" in gx.voice_line1("H", "tag", th, "m", "log")
    assert set(gx.voice_for("Helium") for _ in range(1)) <= {"log", "lecon", "chiffre", "question"}
    assert "how do you handle this" in gx.voice_line1("H", "tag", th, "m", "question", lang="en")
    assert "What we learned" in gx.voice_line1("H", "tag", th, "m", "lecon", lang="en")


def test_format_en_hub(monkeypatch):
    monkeypatch.setattr(gx, "voice_for", lambda *a, **k: "log")
    facts = {"hash": "a1", "msg": "feat: mesh MVP", "c30": 9, "c7": 3,
             "themes": ["Mesh MVP", "One-click install"],
             "theme_verbs": ["Shipped", "Fixed"]}
    post = gx.format_post("Helium", 28, "Actif", facts, lang="en")
    assert gx.x_len(post) <= 280
    assert "Shipped mesh MVP" in post
    assert "private GPU/RAM sharing network" in post
    assert "Active" in post and "Actif" not in post
    assert "https://github.com/HeliumXChain/Helium" in post


def test_presentation_et_split_en():
    assert "statistically validated" in gx.presentation_for("OpenQuant", lang="en")
    assert gx.split_conventional("fix: cache", lang="en") == ("Fixed", "cache")


def test_flesch_ordre():
    simple = "Le chat dort. Il ronronne doucement."
    lourd = ("L'anticonstitutionnalité présuppose des circonlocutions "
             "intergouvernementales substantiellement incompréhensibles.")
    assert gx.flesch_ease(simple) > gx.flesch_ease(lourd)
    assert gx.flesch_ease("") == 0.0


def test_en_action_verbs_et_franglais():
    assert gx.EN_ACTION_VERBS["feat"] == "Shipped"
    assert gx.looks_french("les résultats avec des données") is True
    assert gx.looks_french("shipped mesh MVP with releases") is False
    facts = {"hash": "a1", "msg": "x", "c30": 9, "c7": 3,
             "themes": ["Mesh MVP", "One-click install"],
             "theme_verbs": ["Shipped", "Fixed"]}
    import post_brain as pb
    s, issues = pb.deterministic_score("Helium", "test", ["A"], lang="en")
    assert isinstance(s, int)
    s2, issues2 = pb.deterministic_score(
        "Helium", "les résultats avec des données ici", ["A"], lang="en")
    assert any("FR/EN" in i for i in issues2) and s2 < s


def test_presentation_for():
    assert "GPU" in gx.presentation_for("Helium")
    assert gx.presentation_for("InconnuXYZ", "Super outil de test. Suite.") == "super outil de test"
    assert gx.presentation_for("InconnuXYZ") == "projet du studio"


def test_next_step(tmp_path):
    assert gx.next_step(tmp_path / "absent") == "Poursuite des travaux en cours."
    assert gx.next_step(None) == "Poursuite des travaux en cours."
    (tmp_path / "SESSION_SUMMARY.md").write_text(
        "# Titre\n## Prochaines étapes\n- Brancher la capture Kit\n- Autre\n", encoding="utf-8")
    assert gx.next_step(tmp_path) == "Brancher la capture Kit"


def test_format_long_structure():
    facts = {"hash": "a1", "date": "2026-09-21", "msg": "fix cache", "c30": 3,
             "c7": 1, "branch": "main", "dirty": False,
             "themes": ["Cache plus rapide"], "next": "Stabiliser le cache"}
    long = gx.format_long("Helium", 28, "Actif", facts, "")
    assert "est réseau privé" in long
    assert "Travaux réalisés :" in long and "1. Cache plus rapide." in long
    assert "Prochaine étape : Stabiliser le cache" in long
    assert "Repo : https://github.com/HeliumXChain/Helium" in long
    assert "Caption X :" in long


def test_project_link_et_x_len():
    assert gx.project_link("Helium") == "https://github.com/HeliumXChain/Helium"
    assert gx.project_link("Inconnu") == ""
    assert gx.x_len("abc https://github.com/x/y def") == 4 + 23 + 4
    assert gx.x_len("sans lien") == 9


def test_cut_words_au_mot():
    assert gx._cut_words("alpha beta gamma", 100) == "alpha beta gamma"
    cut = gx._cut_words("alpha beta gamma delta", 12)
    assert cut.endswith("...") and "gamm" not in cut


def test_write_drafts_saute_sans_themes(tmp_path):
    facts = {"hash": "a1", "date": "2026-09-21", "msg": "chore: fix pre-commit x",
             "c30": 5, "c7": 0, "branch": "main", "dirty": False, "themes": []}
    sel = [{"project": {"name": "KuroGuardian", "pct": 8, "status": "Actif", "desc": ""},
            "facts": facts, "ownership": "OWNED", "score": 22}]
    import io
    from contextlib import redirect_stdout
    with redirect_stdout(io.StringIO()):
        written = gx.write_drafts(sel, tmp_path / "out", today="2099-01-01")
    assert written == []
    assert list((tmp_path / "out").glob("x_post_*.md")) == []
