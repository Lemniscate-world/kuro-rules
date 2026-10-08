"""Tests kuro_paths.confine_arg : confinement anti path-traversal."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from kuro_paths import confine_arg  # noqa: E402


def test_relatif_accepte(tmp_path):
    assert confine_arg("a/b.md", tmp_path) == (tmp_path / "a/b.md").resolve()


def test_absolu_dans_base_accepte(tmp_path):
    target = (tmp_path / "x.md").resolve()
    assert confine_arg(str(target), tmp_path) == target


def test_evasion_refusee(tmp_path):
    with pytest.raises(SystemExit):
        confine_arg("../../etc/passwd", tmp_path)
    with pytest.raises(SystemExit):
        confine_arg("/etc/passwd", tmp_path)


def test_repli_default(tmp_path):
    assert confine_arg("../../x", tmp_path, default="safe.md") == tmp_path / "safe.md"


def test_vide_refuse(tmp_path):
    with pytest.raises(SystemExit):
        confine_arg("", tmp_path)
