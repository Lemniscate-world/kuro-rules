"""Smoke genere par Kuro (kuro_autotest.py) — import + symboles."""
import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parent.parent / "scripts/enforce_rules_ci.py"


def _load():
    spec = importlib.util.spec_from_file_location("mod_under_test", MOD)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_smoke_imports():
    mod = _load()
    assert hasattr(mod, "normalize"), "manque normalize"
    assert hasattr(mod, "load_master"), "manque load_master"
    assert hasattr(mod, "rule_count"), "manque rule_count"
    assert hasattr(mod, "local_projects"), "manque local_projects"
    assert hasattr(mod, "github_request"), "manque github_request"
    assert hasattr(mod, "list_remote_repos"), "manque list_remote_repos"
    assert hasattr(mod, "fetch_agents_md"), "manque fetch_agents_md"
    assert hasattr(mod, "fix_agents_md"), "manque fix_agents_md"
    assert hasattr(mod, "write_report"), "manque write_report"
    assert hasattr(mod, "main"), "manque main"
