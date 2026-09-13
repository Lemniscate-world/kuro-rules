"""Tests kuro_llm — défaut modèle valide + garde anti-spam sentinelle (logique pure)."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_llm as llm  # noqa: E402


def test_modele_defaut_existe_cote_openrouter():
    # ox-alpha n'existe pas (445 modeles publies, 0 match) -> defaut :free valide
    assert llm.DEFAULT_OPENROUTER_MODEL.endswith(":free")
    assert "ox-alpha" not in llm.DEFAULT_OPENROUTER_MODEL


def test_alerte_silencieuse_en_sentinelle(monkeypatch):
    # KURO_FULL=false (run 30min, /tmp frais) : aucune ecriture, aucun POST
    monkeypatch.setenv("KURO_FULL", "false")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.invalid/hook")
    marker = Path(tempfile.gettempdir()) / "kuro_brain_alert.timestamp"
    before = marker.read_text(encoding="utf-8") if marker.exists() else None
    llm._alert_brain_down()
    after = marker.read_text(encoding="utf-8") if marker.exists() else None
    assert before == after


def test_ask_sans_cle_retourne_none_sans_crasher(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    monkeypatch.setenv("OLLAMA_URL", "http://127.0.0.1:9")  # port ferme -> echec rapide
    assert llm.ask("ping") is None
    assert llm.available() is None
