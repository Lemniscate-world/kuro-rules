"""Tests kuro_automate — dry-run n'execute rien, echecs non fatals (logique pure)."""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_automate as ka  # noqa: E402


def test_sh_dry_run_n_execute_rien():
    # Cette commande echouerait si executee : en dry-run elle est sautee.
    assert ka.sh([sys.executable, "-c", "raise SystemExit(99)"], dry_run=True) == 0


def test_sh_commande_ok():
    assert ka.sh([sys.executable, "--version"]) == 0


def test_sh_commande_ko_non_fatale():
    assert ka.sh([sys.executable, "-c", "raise SystemExit(3)"]) == 3


def test_sh_timeout_non_fatal(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired(cmd="x", timeout=900)
    monkeypatch.setattr(ka.subprocess, "run", boom)
    assert ka.sh(["n-importe-quoi"]) == 1
