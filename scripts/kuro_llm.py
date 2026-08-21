#!/usr/bin/env python3
"""kuro_llm.py — client LLM unifié pour l'intelligence Kuro (zéro dépendance).

Chaîne de moteurs :
    1. OpenRouter ($OPENROUTER_API_KEY, modèle $OPENROUTER_MODEL, défaut ox-alpha:free)
    2. Ollama local ($OLLAMA_URL, défaut http://localhost:11434, $OLLAMA_MODEL, défaut llama3)
    3. Aucun -> retourne None ; les appelants restent alors en mode déterministe.

Usage:
    from kuro_llm import ask
    reply = ask("Résume ces échecs CI...", system="Tu es l'analyste du studio lambda-Section.")
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_OPENROUTER_MODEL = "stealth/ox-alpha"
DEFAULT_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# Uniquement des modèles cloud Ollama (suffixe :cloud) — jamais les locaux.
# Ordre de préférence ; les modèles 403 (abonnement) / 410 (retirés) sont sautés.
CLOUD_PRIORITY = [
    "minimax-m3",
    "kimi-k2.7",
    "glm-5.2",
    "deepseek-v4-pro",
    "minimax-m2.7",
    "glm-5.1",
    "deepseek-v4-flash",
]


def _post(url: str, payload: dict, headers: dict, timeout: int) -> str | None:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json", **headers},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return data
    except Exception:
        return None


def _openrouter(prompt: str, system: str) -> tuple[str | None, str]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, "no-key"
    base = os.environ.get("OPENROUTER_BASE", DEFAULT_OPENROUTER_BASE)
    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
    data = _post(
        f"{base}/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": int(os.environ.get("OPENROUTER_MAX_TOKENS", "2500")),
            "temperature": 0.3,
        },
        {"Authorization": f"Bearer {key}"},
        timeout=120,
    )
    if not data:
        return None, "error"
    try:
        msg = data["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text:
            # Modele de raisonnement : le contenu peut rester en 'reasoning'
            text = (msg.get("reasoning") or "").strip()
        return (text, "ok") if text else (None, "empty")
    except Exception:
        return None, "bad-shape"


def _get_json(url: str, timeout: int = 5):
    req = urllib.request.Request(url, headers={"User-Agent": "Kuro/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None


def cloud_candidates(base: str) -> list[str]:
    """Liste ordonnée des modèles :cloud disponibles (jamais les locaux)."""
    data = _get_json(f"{base}/api/tags")
    names = [m.get("name", "") for m in (data or {}).get("models", []) if m.get("name")]
    cloud = [n for n in names if n.endswith(":cloud")]
    forced = os.environ.get("OLLAMA_MODEL")
    ordered: list[str] = []
    if forced and forced.endswith(":cloud") and forced in cloud:
        ordered.append(forced)
    for pref in CLOUD_PRIORITY:
        for n in cloud:
            if n.startswith(pref) and n not in ordered:
                ordered.append(n)
    for n in cloud:
        if n not in ordered:
            ordered.append(n)
    return ordered


def _ollama(prompt: str, system: str) -> tuple[str | None, str]:
    base = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    candidates = cloud_candidates(base)
    if not candidates:
        return None, "no-cloud-model"
    last_status = "no-attempt"
    for model in candidates:
        data = _post(
            f"{base}/api/generate",
            {"model": model, "prompt": f"{system}\n\n{prompt}", "stream": False},
            {},
            timeout=300,
        )
        if not data:
            last_status = f"unreachable({model})"
            continue
        try:
            text = data.get("response", "").strip()
            if text:
                print(f"kuro_llm: moteur ollama cloud = {model}")
                return text, "ok"
            last_status = f"empty({model})"
        except Exception:
            last_status = f"bad-shape({model})"
    return None, last_status


def _alert_brain_down() -> None:
    """Discord : cerveau indisponible (1 fois / 24h max)."""
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        return
    import tempfile

    marker = Path(tempfile.gettempdir()) / "kuro_brain_alert.timestamp"
    now = time.time()
    try:
        if marker.exists() and now - float(marker.read_text().strip() or 0) < 86400:
            return
        marker.write_text(str(now))
    except Exception:
        pass
    payload = {
        "username": "Kuro",
        "embeds": [
            {
                "title": "[ALERTE] Cerveau LLM indisponible",
                "description": "OpenRouter et Ollama cloud injoignables. "
                "Le robot continue en mode déterministe.",
                "color": 16098851,
            }
        ],
    }
    try:
        req = urllib.request.Request(
            webhook,
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Kuro/1.0 (lambda-Section bot)",
            },
        )
        with urllib.request.urlopen(req, timeout=15):
            print("kuro_llm: alerte cerveau postée")
    except Exception as exc:
        print(f"kuro_llm: alerte impossible ({exc})")


def ask(prompt: str, system: str = "Tu es l'analyste du studio lambda-Section.") -> str | None:
    """Chaîne de moteurs : OpenRouter cloud d'abord, Ollama cloud en fallback."""
    text, status = _openrouter(prompt, system)
    if text:
        print(f"kuro_llm: openrouter/{os.environ.get('OPENROUTER_MODEL', DEFAULT_OPENROUTER_MODEL)} ok")
        return text
    if status != "no-key":
        print(f"kuro_llm: openrouter indisponible ({status})")
    text, status = _ollama(prompt, system)
    if text:
        print("kuro_llm: fallback ollama cloud ok")
        return text
    print(f"kuro_llm: ollama cloud indisponible ({status})")
    _alert_brain_down()
    return None


def available() -> str | None:
    """Nom du moteur dispo sans consommer d'appel."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if cloud_candidates(os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)):
        return "ollama-cloud"
    return None


if __name__ == "__main__":
    engine = available()
    print(f"moteur disponible: {engine or 'aucun (mode déterministe)'}")
