"""Tests kuro_dashboard.scan — payload dashboard, hermetique, jamais de scan ~/Documents."""

import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import scan as sc  # noqa: E402


@pytest.fixture(autouse=True)
def _no_cache():
    sc._PAYLOAD_CACHE.update({"ts": 0.0, "payload": None})
    yield
    sc._PAYLOAD_CACHE.update({"ts": 0.0, "payload": None})


def _rules_tree(tmp_path: Path) -> Path:
    root = tmp_path / "kuro-rules"
    (root / "dashboard").mkdir(parents=True)
    (root / "KNOWLEDGE_BASE" / "post_mortem").mkdir(parents=True)
    (root / "KNOWLEDGE_BASE" / "mom_tests").mkdir(parents=True)
    (root / "KNOWLEDGE_BASE" / "notes").mkdir(parents=True)
    (root / "KNOWLEDGE_BASE" / "post_mortem" / "pm1.md").write_text(
        "# Crash X\nRetour d'experience detaille.\n", encoding="utf-8")
    (root / "KNOWLEDGE_BASE" / "mom_tests" / "m1.md").write_text(
        "# Mom test\nQuestion posee.\n", encoding="utf-8")
    (root / "KNOWLEDGE_BASE" / "notes" / "n1.md").write_text(
        "Simple note sans titre.\nDeuxieme ligne.\n", encoding="utf-8")
    (root / "AGENTS.md").write_text(
        "## RULE 14: Failure memory\nGarde les post-mortems.\n"
        "## RULE 99: Danse de la pluie\nRien a voir.\n"
        "## RULE 10: Dashboard control\nLe dashboard local.\n",
        encoding="utf-8")
    (root / "SYNC_LOG.md").write_text(
        "## 2026-10-04 09:00:00\n- ProjA : a.md, b.md\n- ProjB\n",
        encoding="utf-8")
    (root / "projects.txt").write_text("ProjA\n", encoding="utf-8")
    (root / "exclude.txt").write_text("", encoding="utf-8")
    return root


def _patch_roots(monkeypatch, root: Path, docs: Path):
    monkeypatch.setattr(sc, "ROOT_DIR", root)
    monkeypatch.setattr(sc, "DASHBOARD_DIR", root / "dashboard")
    monkeypatch.setattr(sc, "DOCS_DIR", docs)
    monkeypatch.setattr(sc, "KNOWLEDGE_DIR", root / "KNOWLEDGE_BASE")
    monkeypatch.setattr(sc, "PROJECTS_FILE", root / "projects.txt")
    monkeypatch.setattr(sc, "EXCLUDE_FILE", root / "exclude.txt")
    monkeypatch.setattr(sc, "AGENTS_FILE", root / "AGENTS.md")
    monkeypatch.setattr(sc, "SYNC_LOG_FILE", root / "SYNC_LOG.md")
    monkeypatch.setattr(sc, "OUTPUT_FILE", root / "dashboard" / "dashboard-data.json")


def test_run_git_ok_et_ko(tmp_path):
    import subprocess
    (tmp_path / ".git").mkdir()
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=tmp_path, check=True)
    ok = sc.run_git(tmp_path, "branch", "--show-current")
    assert isinstance(ok.ok, bool)
    ko = sc.run_git(tmp_path / "inexistant-qui-nexiste-pas", "status")
    # dossier inexistant ou pas un repo -> ok False, jamais d'exception
    assert ko.ok is False
    assert "T" in sc.iso_from_timestamp(1700000000)
    assert "T" in sc.iso_from_timestamp(-99999999999)  # hors plage -> repli now, jamais d'exception
    assert sc.read_text(tmp_path / "f.txt") == "x"


def test_run_git_sans_git(monkeypatch):
    monkeypatch.setattr(sc.subprocess, "run", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError()))
    out = sc.run_git(Path("."), "status")
    assert out.ok is False and "git" in out.output.lower()


def test_parse_list_et_normalize(tmp_path):
    f = tmp_path / "l.txt"
    f.write_text("# commentaire\n\na\n b \n", encoding="utf-8")
    assert sc.parse_list_file(f) == ["a", "b"]
    assert sc.parse_list_file(tmp_path / "nope.txt") == []
    assert sc.normalize_name("  AbC ") == "abc"


def test_parse_remote_variants():
    assert sc.parse_remote("")["organization"] == "local-only"
    ssh = sc.parse_remote("git@github.com:MyOrg/MyRepo.git")
    assert ssh["organization"] == "MyOrg" and ssh["host"] == "github.com"
    https = sc.parse_remote("https://github.com/Org/Repo.git")
    assert https["organization"] == "Org" and https["repository"] == "Repo"
    assert sc.parse_remote("nimporte-quoi")["organization"] == "local-only"


def test_first_lines_et_kind(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("# Titre\nCorps utile.\n", encoding="utf-8")
    assert sc.first_heading_or_line(p) == "Titre"
    assert sc.first_summary_line(p) == "Corps utile."
    vide = tmp_path / "v.md"
    vide.write_text("", encoding="utf-8")
    assert "V" in sc.first_heading_or_line(vide)
    assert sc.first_summary_line(vide) == "No summary yet."
    assert sc.detect_kind(Path("x/post_mortem/a.md")) == "post-mortem"
    assert sc.detect_kind(Path("x/mom_tests/a.md")) == "mom-test"
    assert sc.detect_kind(Path("x/notes/a.md")) == "note"


def test_collect_knowledge_et_rules(tmp_path, monkeypatch):
    root = _rules_tree(tmp_path)
    _patch_roots(monkeypatch, root, tmp_path)
    entries = sc.collect_knowledge_entries()
    assert len(entries) == 3
    kinds = {e["kind"] for e in entries}
    assert {"post-mortem", "mom-test", "note"} <= kinds
    rules = sc.collect_rule_highlights()
    numbers = {r["number"] for r in rules}
    assert 14 in numbers and 10 in numbers and 99 not in numbers
    # sans fichiers -> vide, jamais d'exception
    monkeypatch.setattr(sc, "KNOWLEDGE_DIR", tmp_path / "nope")
    assert sc.collect_knowledge_entries() == []
    monkeypatch.setattr(sc, "AGENTS_FILE", tmp_path / "nope.md")
    assert sc.collect_rule_highlights() == []


def test_parse_sync_log(tmp_path, monkeypatch):
    root = _rules_tree(tmp_path)
    _patch_roots(monkeypatch, root, tmp_path)
    parsed = sc.parse_sync_log()
    assert parsed["lastRun"] == "2026-10-04 09:00:00"
    assert parsed["repoCount"] == 2 and parsed["fileCount"] == 2
    monkeypatch.setattr(sc, "SYNC_LOG_FILE", tmp_path / "nope.md")
    assert sc.parse_sync_log()["lastRun"] is None
    vide = tmp_path / "s.md"
    vide.write_text("pas de header\n", encoding="utf-8")
    monkeypatch.setattr(sc, "SYNC_LOG_FILE", vide)
    assert sc.parse_sync_log()["entries"] == []


def test_collect_project_snapshot_missing(tmp_path, monkeypatch):
    root = _rules_tree(tmp_path)
    _patch_roots(monkeypatch, root, tmp_path)
    snap = sc.collect_project_snapshot("Ghost", None)
    assert snap["exists"] is False and snap["status"] == "missing"
    snap2 = sc.collect_project_snapshot("Ghost2", tmp_path / "nulle-part")
    assert snap2["status"] == "missing"


def test_collect_project_snapshot_git(tmp_path, monkeypatch):
    import subprocess
    root = _rules_tree(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    repo = docs / "Demo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "README.md").write_text("hello", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    (repo / "sale.txt").write_text("modif", encoding="utf-8")
    _patch_roots(monkeypatch, root, docs)
    snap = sc.collect_project_snapshot("Demo", repo)
    assert snap["exists"] is True
    assert snap["status"] == "attention"
    assert snap["hasReadme"] is True
    assert snap["dirtyCount"] >= 0


def test_summarize_et_alerts():
    projs = [
        {"name": "A", "exists": True, "dirtyCount": 1, "hasAgents": True},
        {"name": "B", "exists": False, "dirtyCount": 0, "hasAgents": False},
        {"name": "C", "exists": True, "dirtyCount": 0, "hasAgents": False},
    ]
    s = sc.summarize_status(projs)
    assert s["trackedProjects"] == 3 and s["dirtyProjects"] == 1
    alerts = sc.build_alerts(projs, [{"name": "Extra"}], [], {"lastRun": None})
    titles = [a["title"] for a in alerts]
    assert any("missing" in t.lower() for t in titles)
    assert any("dirty" in t.lower() for t in titles)
    assert any("not tracked" in t.lower() for t in titles)
    # cas nominal : pas d'alerte post-mortem si present, pas d'alerte sync si run
    calmes = sc.build_alerts(
        [{"name": "A", "exists": True, "dirtyCount": 0, "hasAgents": True}],
        [], [{"kind": "post-mortem"}], {"lastRun": "2026-10-04"})
    assert all("post-mortem" not in a["title"].lower() for a in calmes)


def test_organization_groups_et_untracked(tmp_path):
    projs = [
        {"name": "b", "exists": True, "organization": "Org", "dirtyCount": 0},
        {"name": "a", "exists": True, "organization": "Org", "dirtyCount": 1},
        {"name": "ghost", "exists": False, "organization": "Org", "dirtyCount": 0},
    ]
    groups = sc.build_organization_groups(projs)
    assert groups[0]["name"] == "Org" and groups[0]["dirtyCount"] == 1
    assert [p["name"] for p in groups[0]["projects"]] == ["a", "b"]
    fake = tmp_path / "R"
    fake.mkdir()
    snap = sc.collect_project_snapshot("R", None)
    assert snap["exists"] is False
    # discover_untracked : nom deja suivi -> ignore
    out = sc.discover_untracked_repositories({"r"}, [])
    assert out == []


def test_detect_git_repositories_exclut(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir()
    for name in ("Keep", "SkipMe"):
        d = docs / name
        (d / ".git").mkdir(parents=True)
    excl = tmp_path / "exclude.txt"
    excl.write_text("SkipMe\n", encoding="utf-8")
    monkeypatch.setattr(sc, "DOCS_DIR", docs)
    monkeypatch.setattr(sc, "EXCLUDE_FILE", excl)
    monkeypatch.setattr(sc, "ROOT_DIR", docs / "kuro-rules")
    found = sc.detect_git_repositories()
    assert {p.name for p in found} == {"Keep"}
    monkeypatch.setattr(sc, "DOCS_DIR", tmp_path / "nulle-part")
    assert sc.detect_git_repositories() == []


def test_daemon_state_tolerant(tmp_path, monkeypatch):
    # sans DB -> inactive, jamais error
    monkeypatch.setattr(sc, "KURO_DB_FILE", tmp_path / "nope.db")
    st = sc.collect_kuro_daemon_state()
    assert st["status"] == "inactive" and st["projectCount"] == 0
    # DB partielle (que projects) -> compteurs, pas error
    db = tmp_path / "k.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE projects (id INTEGER)")
    conn.execute("INSERT INTO projects VALUES (1)")
    conn.commit()
    conn.close()
    monkeypatch.setattr(sc, "KURO_DB_FILE", db)
    st2 = sc.collect_kuro_daemon_state()
    assert st2["projectCount"] == 1
    assert st2["status"] in ("inactive", "active")
    assert st2["alerts"] == []
    # DB complete avec heartbeat recent -> active
    db2 = tmp_path / "k2.db"
    conn = sqlite3.connect(db2)
    conn.execute("CREATE TABLE projects (id INTEGER)")
    conn.execute("CREATE TABLE alerts (id INTEGER, alert_type TEXT, message TEXT, severity TEXT, acknowledged INTEGER, created_at TEXT, project_id INTEGER)")
    conn.execute("CREATE TABLE heartbeat (timestamp TEXT)")
    conn.execute("INSERT INTO heartbeat VALUES (datetime('now'))")
    conn.commit()
    conn.close()
    monkeypatch.setattr(sc, "KURO_DB_FILE", db2)
    st3 = sc.collect_kuro_daemon_state()
    assert st3["status"] == "active"
    assert st3["heartbeatAt"] is not None


def test_coverage_et_ci_state(tmp_path, monkeypatch):
    root = _rules_tree(tmp_path)
    monkeypatch.setattr(sc, "ROOT_DIR", root)
    # coverage absent au depart
    covf = root / "coverage.local.json"
    if covf.exists():
        covf.unlink()
    c0 = sc.collect_coverage_state()
    assert c0["present"] is False and c0["stale"] is True
    covf.write_text(json.dumps({"generated_at": "2026-10-05T00:00:00+00:00",
                                "repos": [{"name": "A", "pct_total": 80}]}),
                    encoding="utf-8")
    c1 = sc.collect_coverage_state()
    assert c1["present"] is True and c1["repos"] == 1 and c1["avgPct"] == 80
    # ci-status absent -> present False
    monkeypatch.setattr(sc.Path, "home", classmethod(lambda cls: tmp_path))
    ci = sc.collect_ci_status_state()
    assert ci["present"] is False
    (root / "ci-status.json").write_text(
        json.dumps({"generated_at": "2026-10-05T00:00:00+00:00", "overall": "green"}),
        encoding="utf-8")
    ci2 = sc.collect_ci_status_state()
    assert ci2["present"] is True and ci2["overall"] == "green"


def test_build_payload_complet(tmp_path, monkeypatch):
    root = _rules_tree(tmp_path)
    docs = tmp_path / "docs"
    docs.mkdir()
    _patch_roots(monkeypatch, root, docs)
    monkeypatch.setattr(sc, "KURO_DB_FILE", tmp_path / "nope.db")
    payload = sc.build_payload(use_cache=False)
    for key in ("generatedAt", "summary", "trackedProjects", "organizations",
                "knowledgeBase", "ruleHighlights", "syncLog", "kuroDaemon",
                "kuroRulesRepo", "coverage", "ciStatus"):
        assert key in payload
    assert payload["summary"]["trackedProjects"] == 1
    # cache : second appel renvoie le meme objet
    payload2 = sc.build_payload(use_cache=True)
    assert payload2["generatedAt"] == payload["generatedAt"]
    # main ecrit le fichier
    rc = sc.main()
    assert rc == 0
    assert (root / "dashboard" / "dashboard-data.json").exists()
