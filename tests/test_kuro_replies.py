"""Tests de la file de réponses (pur, sans réseau)."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import kuro_replies as kr  # noqa: E402

NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def test_parse_sections_et_table():
    text = "## 1. Posts\n\n| A | B |\n|---|---|\n| x | y |\n| | |\n\n## 5. Collabs\n"
    sections = kr.parse_sections(text)
    assert set(sections) == {1, 5}
    assert kr.parse_table(sections[1]) == [{"A": "x", "B": "y"}]
    assert kr.parse_table(sections[5]) == []


def test_normalize_notification_issue():
    item = kr.normalize_notification({
        "reason": "mention",
        "updated_at": "2026-10-19T10:00:00Z",
        "repository": {"full_name": "exo-explore/exo"},
        "subject": {
            "title": "LAN discovery",
            "type": "Issue",
            "url": "https://api.github.com/repos/exo-explore/exo/issues/2271",
        },
    })
    assert item["url"] == "https://github.com/exo-explore/exo/issues/2271"
    assert item["number"] == "2271"
    assert item["priority"] == "haute"
    assert item["source"] == "github"


def test_normalize_pull_url_singulier():
    item = kr.normalize_notification({
        "reason": "review_requested",
        "repository": {"full_name": "o/r"},
        "subject": {
            "title": "fix",
            "type": "PullRequest",
            "url": "https://api.github.com/repos/o/r/pulls/12",
        },
    })
    assert item["url"] == "https://github.com/o/r/pull/12"


def test_classify_retard_et_a_traiter():
    late, due = kr.classify([
        {"title": "vieille", "updated_at": "2026-10-17T12:00:00Z"},
        {"title": "recente", "updated_at": "2026-10-19T11:00:00Z"},
    ], now=NOW, horizon_hours=24)
    assert [i["title"] for i in late] == ["vieille"]
    assert late[0]["age_hours"] == 48.0
    assert [i["title"] for i in due] == ["recente"]


def test_tracker_collecte_collabs_et_non_prouves(tmp_path):
    tracker = tmp_path / "tracker.md"
    tracker.write_text(
        "## 1. Posts publiés\n\n"
        "| Date | Plateforme | Titre / message (60 car) | Lien | Résultat |\n"
        "|---|---|---|---|---|\n"
        "| 2026-09-28 | GitHub | LAN | https://github.com/o/r/issues/1 | "
        "🔴 non prouvé — No activity |\n\n"
        "## 4. Suivi 24 h\n\n"
        "| Échéance | Thread / lien | Dernière interaction | Action attendue | État |\n"
        "|---|---|---|---|---|\n"
        "| 2026-10-19 | https://github.com/o/r/issues/1 | 0 réponse | relance unique | à faire |\n"
        "| 2026-10-18 | https://github.com/o/r/issues/2 | répondu | archiver | fait |\n\n"
        "## 5. Collabs reçues\n\n"
        "| Date | Qui | Canal | Demande | Statut | Suite |\n"
        "|---|---|---|---|---|---|\n"
        "| 2026-10-18 | Ana | LinkedIn | audit perf | nouveau | |\n"
        "| 2026-10-17 | Bob | mail | pub | refusé | |\n",
        encoding="utf-8",
    )
    signals = kr.load_tracker(tracker)
    assert signals["unverified"][0]["title"] == "LAN"
    assert len(signals["followups"]) == 1
    assert signals["followups"][0]["Action attendue"] == "relance unique"
    assert [c["Qui"] for c in signals["collabs"]] == ["Ana"]


def test_inbox_absente_ou_invalide(tmp_path, capsys):
    assert kr.load_inbox(tmp_path / "absent.json") == []
    bad = tmp_path / "bad.json"
    bad.write_text("{pas du json", encoding="utf-8")
    assert kr.load_inbox(bad) == []
    assert "inbox illisible" in capsys.readouterr().err


def test_fetch_gh_panne_donne_liste_vide(capsys):
    def boom():
        raise RuntimeError("gh absent")

    assert kr.fetch_github_notifications(boom) == []
    assert "gh indisponible" in capsys.readouterr().err


def test_main_json_sans_reseau(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kr, "confine_arg", lambda value, base: Path(value))
    tracker = tmp_path / "tracker.md"
    tracker.write_text(
        "## 5. Collabs reçues\n\n"
        "| Date | Qui | Canal | Demande | Statut | Suite |\n"
        "|---|---|---|---|---|---|\n"
        "| 2026-10-18 | Ana | LinkedIn | audit perf | nouveau | |\n",
        encoding="utf-8",
    )
    inbox = tmp_path / "inbox.json"
    inbox.write_text(json.dumps([{
        "source": "linkedin",
        "title": "Proposition de collab",
        "url": "https://example.test/dm/1",
        "received_at": "2026-10-17T12:00:00Z",
    }]), encoding="utf-8")

    rc = kr.main([
        "--tracker", str(tracker), "--inbox", str(inbox),
        "--json", "--now", NOW.isoformat(), "--horizon-hours", "24",
    ])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert [i["title"] for i in payload["late"]] == ["Proposition de collab"]
    assert payload["late"][0]["age_hours"] == 48.0
    assert [c["Qui"] for c in payload["collabs"]] == ["Ana"]


def test_main_strict_sort_1_si_retard(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(kr, "confine_arg", lambda value, base: Path(value))
    tracker = tmp_path / "tracker.md"
    tracker.write_text("## 1. Posts publiés\n", encoding="utf-8")
    inbox = tmp_path / "inbox.json"
    inbox.write_text(json.dumps([{
        "source": "x",
        "title": "réponse en attente",
        "received_at": "2026-10-17T12:00:00Z",
    }]), encoding="utf-8")

    rc = kr.main([
        "--tracker", str(tracker), "--inbox", str(inbox),
        "--strict", "--now", NOW.isoformat(),
    ])
    assert rc == 1
    assert "EN RETARD (1)" in capsys.readouterr().out
