"""Tests inventory_versions.py + release-please templates (VERSIONING.md)."""

import json
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import install_hooks as hooks
import inventory_versions as inv


def test_static_pyproject_version():
    assert inv.static_pyproject_version('version = "1.5.0"\n') == "1.5.0"
    assert inv.static_pyproject_version('dynamic = ["version"]\n') == ""


def test_audit_one_tmp_project(tmp_path):
    proj = tmp_path / "demo"
    proj.mkdir()
    (proj / "package.json").write_text(json.dumps({"version": "0.2.0"}), encoding="utf-8")
    row = inv.audit_one(tmp_path, "demo")
    assert row["present"] == "yes"
    assert row["version"] == "0.2.0" and row["source"] == "package.json"
    assert row["changelog"] == "no" and row["release_wf"] == "no"


def test_audit_one_missing():
    row = inv.audit_one(REPO, "no-such-project-xyz")
    assert row["present"] == "no"


def test_release_please_configs_valid():
    for t in ("node", "python", "rust", "generic"):
        cfg = json.loads((REPO / "templates" / f"release-please-config-{t}.json")
                         .read_text(encoding="utf-8"))
        assert cfg["packages"] == {".": cfg["packages"]["."]}
        assert cfg["release-type"] in ("node", "python", "rust", "simple")


def test_release_please_workflow_valid():
    wf = yaml.safe_load((REPO / "templates" / "release-please.yml").read_text(encoding="utf-8"))
    assert wf["jobs"]["release-please"]["runs-on"] == "ubuntu-latest"
    steps = wf["jobs"]["release-please"]["steps"]
    assert any("release-please-action" in str(s.get("uses", "")) for s in steps)


def test_compliance_has_r91_fleet_job():
    wf = yaml.safe_load((REPO / "templates" / "kuro-compliance.yml").read_text(encoding="utf-8"))
    names = [s.get("name", "") for s in wf["jobs"]["compliance"]["steps"]]
    assert any("R91" in n for n in names)
    assert any("R112" in n for n in names)


def test_fleet_snapshot_exists_and_covers_projects():
    snap = REPO / "FLEET_VERSIONS.md"
    assert snap.exists()
    text = snap.read_text(encoding="utf-8")
    assert "no version" in text
    for name in ("OpenQuant", "Helium", "Odin"):
        assert name in text


def test_kuro_hook_marker_detection(tmp_path):
    kuro = tmp_path / "a"
    kuro.write_text("# x\nSource de verite: kuro-rules/templates/git-hooks/pre-push.sh\n",
                    encoding="utf-8")
    foreign = tmp_path / "b"
    foreign.write_text("#!/bin/sh\necho custom\n", encoding="utf-8")
    assert hooks.is_kuro_hook(kuro) is True
    assert hooks.is_kuro_hook(foreign) is False
    assert hooks.is_kuro_hook(tmp_path / "missing") is False


def test_commit_msg_template_has_strict_escape():
    text = (REPO / "templates" / "git-hooks" / "commit-msg.sh").read_text(encoding="utf-8")
    assert "CONVENTIONAL_STRICT" in text
    assert "Source de verite: kuro-rules/templates" in text


def test_kuro_rules_dogfoods_release_please():
    cfg = json.loads((REPO / "release-please-config.json").read_text(encoding="utf-8"))
    assert cfg["release-type"] == "simple"
    manifest = json.loads((REPO / ".release-please-manifest.json").read_text(encoding="utf-8"))
    assert manifest["."] == (REPO / "VERSION").read_text(encoding="utf-8").strip()
    wf = yaml.safe_load((REPO / ".github" / "workflows" / "release-please.yml")
                        .read_text(encoding="utf-8"))
    assert any("release-please-action" in str(s.get("uses", ""))
               for s in wf["jobs"]["release-please"]["steps"])


def test_fleet_sync_automation_wired():
    wrapper = (REPO / "scripts" / "fleet_sync_scheduled.ps1").read_text(encoding="utf-8")
    for token in ("generate_targets.py", "sync-rules.ps1", "install_hooks.py",
                  "inventory_versions.py"):
        assert token in wrapper
    installer = (REPO / "scripts" / "Install-KuroScheduledTask.ps1").read_text(encoding="utf-8")
    assert "KuroFleetSync" in installer
