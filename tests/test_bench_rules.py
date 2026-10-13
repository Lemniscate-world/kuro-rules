"""Tests bench_rules.py — 10/10 required on the repo itself."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import bench_rules


def test_bench_10_sur_10():
    results = bench_rules.run_bench(REPO)
    assert len(results) == 10
    failures = [(n, d) for n, ok, d in results if not ok]
    assert failures == [], f"bench failures: {failures}"


def test_bench_cli_exit_0():
    r = subprocess.run([sys.executable, "scripts/bench_rules.py"],
                       capture_output=True, text=True, cwd=REPO, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "10/10 checks passed." in r.stdout
