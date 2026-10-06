import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import kuro_llm  # noqa: E402


def pytest_sessionstart(session):
    """Purge __pycache__ : du bytecode perime a deja masque des sources
    (2026-10-04 : suite verte sur code fantome). Cout : quelques secondes."""
    import shutil as _shutil

    root = Path(__file__).resolve().parent.parent
    for cache in root.rglob("__pycache__"):
        try:
            if cache.is_dir():
                _shutil.rmtree(cache, ignore_errors=True)
        except Exception:
            continue


@pytest.fixture(autouse=True)
def _llm_hermetic(tmp_path, monkeypatch):
    """Isole tous les tests du routeur LLM : pas de reseau, pas d ecriture ~/.kuro."""
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("KURO_ROUTER", raising=False)
    monkeypatch.setenv("KURO_POLLINATIONS", "0")
    for _var in ("GROQ_API_KEY", "NVIDIA_API_KEY", "GEMINI_API_KEY",
                 "GOOGLE_AI_KEY", "HF_TOKEN", "HUGGINGFACE_API_KEY",
                 "MISTRAL_API_KEY"):
        monkeypatch.delenv(_var, raising=False)
    monkeypatch.setattr(kuro_llm, "_llm_last_path", lambda: tmp_path / "llm_last.json")
    monkeypatch.setattr(kuro_llm, "_cache_path", lambda: tmp_path / "llm_cache.json")
    monkeypatch.setattr(kuro_llm, "_queue_path", lambda: tmp_path / "llm_queue.jsonl")
    monkeypatch.setattr(kuro_llm, "_usage_path", lambda: tmp_path / "llm_usage.jsonl")
    monkeypatch.setattr(kuro_llm, "_breaker_path", lambda: tmp_path / "llm_breaker.json")
    monkeypatch.setattr(kuro_llm, "_usage_path", lambda: tmp_path / "llm_usage.jsonl")
    monkeypatch.setenv("KURO_PROJECTS_ROOTS", str(tmp_path))
