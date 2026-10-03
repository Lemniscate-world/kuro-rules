"""Tests kuro_omnigraph_export — logique pure, fichiers temporaires, zero reseau."""

import json

import kuro_omnigraph_export as koe


SAMPLE = """
## Section

| Projet | Progression | Statut | Description |
|--------|-------------|--------|-------------|
| **NeuralDBG** | 57% | Actif | Debugger causal |
| **Oblivion** | 35% | Actif | IDE a 0 FCFA |
| Vault | 5% | Outil | Base perso |
| **Haki** | — | Archive | Renomme Oblivion |
"""


def test_slugify():
    assert koe.slugify("NeuralDBG") == "neuraldbg"
    assert koe.slugify("  XP_Farming System ") == "xp-farming-system"
    assert koe.slugify("") == "projet"


def test_parse_table_rows():
    projects = koe.parse_epingle_projects(SAMPLE)
    by_name = {p["name"]: p for p in projects}
    assert by_name["NeuralDBG"]["progress"] == 57
    assert by_name["NeuralDBG"]["status"] == "Actif"
    assert by_name["Oblivion"]["progress"] == 35
    assert by_name["Haki"]["progress"] == 0
    assert "Projet" not in by_name


def test_parse_ignore_livrables_table():
    text = (
        "| Projet | Section | Livrable | Frequence |\n"
        "|---|---|---|---|\n"
        "| **OpenQuant** | L-2 | Modele de trading | Mensuel |\n"
        "| Projet | Progression | Statut | Description |\n"
        "|---|---|---|---|\n"
        "| **NeuralDBG** | 57% | Actif | Debugger |\n"
    )
    projects = koe.parse_epingle_projects(text)
    assert [p["name"] for p in projects] == ["NeuralDBG"]


def test_parse_empty_no_crash():
    assert koe.parse_epingle_projects("") == []
    assert koe.parse_epingle_projects(None) == []


def test_deny_private_paths(tmp_path):
    for forbidden in [
        "finances.local.json",
        "strategy.local.json",
        "pipeline.local.json",
        "SESSION_SUMMARY.md",
        "PLAN.md",
        "LAUNCH_POSTS.md",
    ]:
        try:
            koe.assert_public_path(tmp_path / forbidden)
            raise AssertionError(f"ExportError attendu pour {forbidden}")
        except koe.ExportError:
            pass


def test_deny_tracking_and_backups(tmp_path):
    for forbidden in [
        tmp_path / "docs" / "tracking" / "x.md",
        tmp_path / "SYNC_BACKUPS" / "y.md",
        tmp_path / "data.local.json",
    ]:
        try:
            koe.assert_public_path(forbidden)
            raise AssertionError(f"ExportError attendu pour {forbidden}")
        except koe.ExportError:
            pass


def test_build_records_dedupe_et_regles():
    records = koe.build_records(
        [
            {"name": "NeuralDBG", "progress": 57, "status": "Actif"},
            {"name": "NeuralDBG", "progress": 57, "status": "Actif"},
            {"name": "", "progress": 3, "status": "Actif"},
            {"name": "OpenQuant", "progress": "oops", "status": "Actif"},
        ]
    )
    projects = [r for r in records if r["type"] == "Project"]
    rules = [r for r in records if r["type"] == "Rule"]
    assert len(projects) == 2
    assert len(rules) == 3
    assert all(isinstance(p["data"]["progress"], int) for p in projects)


def test_write_jsonl_roundtrip(tmp_path):
    out = tmp_path / "export.jsonl"
    records = koe.build_records([{"name": "A", "progress": 5, "status": "Actif"}])
    count = koe.write_jsonl(records, out)
    assert count == len(records) > 0
    lines = out.read_text(encoding="utf-8").splitlines()
    assert all(json.loads(line) for line in lines)


def test_write_jsonl_empty_no_crash(tmp_path):
    out = tmp_path / "empty.jsonl"
    assert koe.write_jsonl([], out) == 0


def test_run_export_end_to_end(tmp_path):
    epingle = tmp_path / "Epingle_Projets.md"
    epingle.write_text(SAMPLE, encoding="utf-8")
    projects_txt = tmp_path / "projects.txt"
    projects_txt.write_text("# liste\nNeuralDBG\n", encoding="utf-8")
    out = tmp_path / "out.jsonl"
    stats = koe.run_export(epingle, projects_txt, out)
    assert stats["projects"] == 4
    assert stats["rules"] == 3
    assert stats["lines"] == 7


def test_schema_assets_non_regression():
    assert "progress: I32" in koe.SCHEMA_PG
    assert "progress: Int" not in koe.SCHEMA_PG
    assert "node Project" in koe.SCHEMA_PG
    assert "edge Follows: Project -> Rule" in koe.SCHEMA_PG
    assert "query active_projects" in koe.QUERIES_GQ
