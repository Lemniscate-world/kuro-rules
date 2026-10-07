#!/usr/bin/env python3
"""kuro_llm.py — client LLM unifié pour l'intelligence Kuro (zéro dépendance).

Chaîne de moteurs (defaut, sans routeur) :
    1. OpenRouter ($OPENROUTER_API_KEY, $OPENROUTER_MODEL + cascade :free)
    2. Groq gratuit ($GROQ_API_KEY, defaut llama-3.3-70b-versatile)
    3. DeepSeek ($DEEPSEEK_API_KEY)
    4. Ollama local, modele explicite $OLLAMA_MODEL non-:cloud (ex: qwen3:8b)
    5. Ollama cloud (:cloud, quota mensuel starter)
    6. Pollinations sans cle (copie OpenQuant, kill-switch KURO_POLLINATIONS=0)
    7. Aucun -> retourne None ; les appelants restent en mode déterministe.
    Quand DeepSeek tombe, la chaine continue seule : local -> cloud ->
    pollinations -> file d attente -> rejouable (--drain).

Tiers (ask tier=) : auto (ordre ci-dessus), routine (gratuit d abord :
local, pollinations, ...), dur (costaud d abord : openrouter, ...).

Routeur opt-in : KURO_ROUTER=litellm (lib optionnelle, jamais obligatoire).
Dernier moteur utilise ecrit dans ~/.kuro/llm_last.json (lu par Xenon).

Usage:
    from kuro_llm import ask
    reply = ask("Résume ces échecs CI...", system="Tu es l'analyste du studio lambda-Section.")
"""

import hashlib
import json
import os
import sys
import threading
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def _load_dotenv() -> None:
    """Repli .env local (racine repo) si les cles ne sont pas dans l'environnement.

    setdefault uniquement : l'environnement reel gagne toujours (jamais d'ecrasement),
    jamais de secret journalise, jamais d'exception. Sans ce repli, tout affichage
    lance depuis un contexte sans env (Xenon, doctor, API redemarree) voit le
    cerveau "tout off" alors que les cles sont dans .env.
    """
    try:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip('"').strip("'")
    except Exception:
        pass


_load_dotenv()

DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
DEFAULT_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
DEFAULT_DEEPSEEK_BASE = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-flash"
DEFAULT_GROQ_BASE = "https://api.groq.com/openai/v1"
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_OLLAMA_URL = "http://localhost:11434"

# Cascade gratuite OpenRouter (oct 2026, $0) : le 1er qui repond gagne.
# Surchargeable via $OPENROUTER_MODELS (csv). $OPENROUTER_MODEL reste prioritaire.
FREE_OPENROUTER_CASCADE = [
    "qwen/qwen3-coder:free",
    "deepseek/deepseek-v4-flash:free",
    "google/gemma-4-31b-it:free",
    "z-ai/glm-4.5-air:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

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


def _openrouter_models() -> list[str]:
    """Modeles OpenRouter a essayer dans l ordre (1er qui repond gagne)."""
    raw = os.environ.get("OPENROUTER_MODELS", "")
    models = [m.strip() for m in raw.split(",") if m.strip()]
    if not models:
        primary = os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        models = [primary] + [m for m in FREE_OPENROUTER_CASCADE if m != primary]
    return models


def _openrouter(prompt: str, system: str) -> tuple[str | None, str]:
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        return None, "no-key"
    base = os.environ.get("OPENROUTER_BASE", DEFAULT_OPENROUTER_BASE)
    last_status = "no-attempt"
    for model in _openrouter_models():
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
            {"Authorization": f"Bearer {key}",
             "HTTP-Referer": os.environ.get("OPENROUTER_REFERER", "https://github.com/kuro-rules"),
             "X-Title": "Kuro"},
            timeout=120,
        )
        if not data:
            last_status = f"error({model})"
            continue
        _TLS.usage = _openai_usage(data)
        try:
            msg = data["choices"][0]["message"]
            text = (msg.get("content") or "").strip()
            if not text:
                # Modele de raisonnement : le contenu peut rester en 'reasoning'
                text = (msg.get("reasoning") or "").strip()
            if text:
                if model != os.environ.get("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL):
                    print(f"kuro_llm: openrouter cascade = {model}")
                return text, "ok"
            last_status = f"empty({model})"
        except Exception:
            last_status = f"bad-shape({model})"
    return None, last_status


def _groq(prompt: str, system: str) -> tuple[str | None, str]:
    """Jambe gratuite rapide : Groq (compatible OpenAI, free tier genereux)."""
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None, "no-key"
    base = os.environ.get("GROQ_BASE", DEFAULT_GROQ_BASE)
    model = os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL)
    data = _post(
        f"{base}/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": int(os.environ.get("GROQ_MAX_TOKENS", "2500")),
            "temperature": 0.3,
        },
        {"Authorization": f"Bearer {key}"},
        timeout=120,
    )
    if not data:
        return None, "error"
    _TLS.usage = _openai_usage(data)
    try:
        text = (data["choices"][0]["message"].get("content") or "").strip()
        return (text, "ok") if text else (None, "empty")
    except Exception:
        return None, "bad-shape"


def _deepseek(prompt: str, system: str) -> tuple[str | None, str]:
    """Fallback payant : API DeepSeek (compatible OpenAI)."""
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        return None, "no-key"
    base = os.environ.get("DEEPSEEK_BASE", DEFAULT_DEEPSEEK_BASE)
    model = os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL)
    data = _post(
        f"{base}/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": int(os.environ.get("DEEPSEEK_MAX_TOKENS", "2500")),
            "temperature": 0.3,
        },
        {"Authorization": f"Bearer {key}"},
        timeout=120,
    )
    if not data:
        return None, "error"
    _TLS.usage = _openai_usage(data)
    try:
        msg = data["choices"][0]["message"]
        text = (msg.get("content") or "").strip()
        if not text:
            # Modeles raisonnants (v4-pro) : la reponse reste en reasoning_content
            # si max_tokens trop bas pour finir le raisonnement.
            text = (msg.get("reasoning_content") or msg.get("reasoning") or "").strip()
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


def _local_ollama(prompt: str, system: str) -> tuple[str | None, str]:
    """Jambe locale : modele Ollama NON-cloud explicite via $OLLAMA_MODEL.

    Jamais d auto-choix (un 17 Go ou un embedding par defaut = piege).
    Exemple : OLLAMA_MODEL=qwen3:8b (5 Go, tient en VRAM 8 Go).
    """
    model = os.environ.get("OLLAMA_MODEL")
    if not model:
        return None, "no-local-model"
    if model.endswith(":cloud"):
        return None, "cloud-not-here"
    base = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    tags = _get_json(f"{base}/api/tags") or {}
    names = [m.get("name", "") for m in tags.get("models", []) if m.get("name")]
    if model not in names:
        return None, f"not-pulled({model})"
    data = _post(
        f"{base}/api/generate",
        {"model": model, "prompt": f"{system}\n\n{prompt}", "stream": False,
         "options": {"num_predict": int(os.environ.get("OLLAMA_MAX_TOKENS", "1200"))}},
        {},
        timeout=300,
    )
    if not data:
        return None, f"unreachable({model})"
    _TLS.usage = _ollama_usage(data)
    try:
        text = data.get("response", "").strip()
        return (text, "ok") if text else (None, f"empty({model})")
    except Exception:
        return None, f"bad-shape({model})"


def _llm_last_path() -> Path:
    return Path.home() / ".kuro" / "llm_last.json"


def _prompt_hash(prompt: str) -> str:
    try:
        return hashlib.sha256(prompt.encode("utf-8", "ignore")).hexdigest()[:16]
    except Exception:
        return "unhashable"


def _cache_path() -> Path:
    return Path.home() / ".kuro" / "llm_cache.json"


def _cache_load() -> dict:
    try:
        data = json.loads(_cache_path().read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _cache_lookup(prompt: str) -> str | None:
    """Reponse exacte en cache (TTL defaut 7 j). Jamais d exception."""
    if os.environ.get("KURO_CACHE", "1") == "0":
        return None
    try:
        entry = _cache_load().get(_prompt_hash(prompt)) or {}
        ttl = int(os.environ.get("KURO_CACHE_TTL", "604800"))
        if ttl <= 0 or time.time() - float(entry.get("at", 0)) > ttl:
            return None
        return entry.get("text") or None
    except Exception:
        return None


def _cache_store(prompt: str, text: str) -> None:
    try:
        cache = _cache_load()
        cache[_prompt_hash(prompt)] = {"text": text, "at": time.time()}
        while len(cache) > 200:  # borne memoire : on oublie le plus vieux
            cache.pop(next(iter(cache)))
        _cache_path().write_text(json.dumps(cache), encoding="utf-8")
    except Exception:
        pass


def _queue_path() -> Path:
    return Path.home() / ".kuro" / "llm_queue.jsonl"


def _queue_pending(prompt: str, system: str, tier: str) -> None:
    """File d attente des appels sans cerveau (dedup par hash, cap 100)."""
    try:
        wanted = _prompt_hash(prompt)
        kept: list[dict] = []
        attempts = 0
        path = _queue_path()
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    item = json.loads(line)
                except Exception:
                    continue
                if not isinstance(item, dict):
                    continue
                if item.get("hash") == wanted:
                    attempts = int(item.get("attempts", 0))
                    continue
                kept.append(item)
        kept.append({"hash": wanted, "prompt": prompt[:2000], "system": system[:500],
                     "tier": tier, "attempts": attempts + 1, "at": time.time()})
        path.write_text("\n".join(json.dumps(i) for i in kept[-100:]), encoding="utf-8")
    except Exception:
        pass


def drain_queue(limit: int = 5) -> list[dict]:
    """Rejoue la file quand un cerveau est revenu. Jamais d exception."""
    try:
        path = _queue_path()
        items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        items = [i for i in items if isinstance(i, dict)]
    except Exception:
        return []
    # On libere d abord : les echecs se re-file via ask() (attempts+1).
    todo, later = items[: max(1, limit)], items[max(1, limit):]
    try:
        path.write_text("\n".join(json.dumps(i) for i in later), encoding="utf-8")
    except Exception:
        pass
    results: list[dict] = []
    for item in todo:
        text = ask(item.get("prompt", ""), system=item.get("system", ""),
                   tier=item.get("tier", "auto"))
        if text:
            results.append({"prompt": item.get("prompt", "")[:120],
                            "engine": "drained", "text": text[:500]})
    return results


def _record_brain(engine: str | None, seconds: float, prompt: str = "",
                  model: str = "") -> None:
    """Dernier cerveau utilise (lu par Xenon). Jamais bloquant.

    prompt_hash = empreinte 16 hex (pas le texte : pas de fuite).
    model = label complet ("openrouter/nvidia/...:free", "" si routeur/cache).
    Sert a mesurer le taux de repetition avant tout cache (cf. GPTCache).
    """
    try:
        path = _llm_last_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        digest = _prompt_hash(prompt)
        path.write_text(
            json.dumps({"engine": engine or "deterministe",
                        "model": model or "",
                        "latency_s": round(seconds, 1),
                        "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "prompt_hash": digest}),
            encoding="utf-8",
        )
    except Exception:
        pass


def _usage_path() -> Path:
    return _llm_last_path().parent / "llm_usage.jsonl"


# Cout estime $ / 1M tokens (mix entree+sortie, ordre de grandeur, variable
# selon modele exact — affiche comme ~est dans le TUI, jamais facture).
# Regle d honestete : 0.0 = vraiment gratuit (tiers :free, local, cache),
# None = prix inconnu (le TUI affiche ~$? au lieu de mentir $0.0000).
# Table versionnee dans llm_pricing.json (repli integre si absent) :
# mettre a jour version+date a chaque revision des prix.
_USAGE_COST_PER_MTOK = {
    "groq": 0.0,
    "nvidia": 0.0,
    "gemini": 0.0,
    "hf": 0.0,
    "mistral": 0.0,
    "deepseek": 1.0,
    "ollama-cloud": 2.0,
    "litellm:openrouter": 0.0,
    "litellm:groq": 0.0,
    "litellm:nvidia": 0.0,
    "litellm:gemini": 0.0,
    "litellm:huggingface": 0.0,
    "litellm:mistral": 0.0,
    "litellm:deepseek": 1.0,
    "pollinations": 0.0,
    "cache": 0.0,
    "deterministe": 0.0,
    "ollama-local": 0.0,
    "ollama": 0.0,
    "local": 0.0,
}
_PRICING_CACHE: dict = {}


def _pricing_table() -> tuple[dict, int, str]:
    """(rates, version, updated) depuis llm_pricing.json, sinon repli integre."""
    try:
        if _PRICING_CACHE.get("rates"):
            cached = _PRICING_CACHE
            return cached["rates"], cached["version"], cached["updated"]
        path = Path(__file__).resolve().parent / "llm_pricing.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        rates = data.get("rates") if isinstance(data, dict) else None
        if not isinstance(rates, dict) or not rates:
            raise ValueError("table vide")
        version = int(data.get("version", 0) or 0)
        updated = str(data.get("updated") or "?")
        _PRICING_CACHE.update({"rates": rates, "version": version,
                               "updated": updated})
        return rates, version, updated
    except Exception:
        _PRICING_CACHE.update({"rates": dict(_USAGE_COST_PER_MTOK),
                               "version": 0, "updated": "built-in"})
        cached = _PRICING_CACHE
        return cached["rates"], cached["version"], cached["updated"]


def pricing_version() -> str:
    """'v1 @2026-10-07' pour affichage (jamais d exception)."""
    try:
        _, version, updated = _pricing_table()
        return f"v{version} @{updated}"
    except Exception:
        return "v? @?"


def _model_rate(model: str, engine: str | None) -> float | None:
    """$/MTok blended pour un appel, ou None si prix inconnu.

    Le modele exact decide, pas la jambe : un :free OpenRouter coute 0
    (vrai zero) mais un modele payant non tarife rend None — le TUI
    affiche alors un compteur "cout inconnu" au lieu de $0.0000.
    """
    m = (model or "").lower()
    if ":free" in m:
        return 0.0
    rates, _version, _updated = _pricing_table()
    leg = ((engine or "").split("/")[0].split(":")[0] or "").lower()
    if leg in ("", "cache", "deterministe", "local", "ollama-local",
               "ollama", "pollinations",
               "groq", "nvidia", "gemini", "hf", "mistral"):
        return 0.0
    if leg in rates:
        return rates[leg]
    if leg == "cloud":
        return rates.get("ollama-cloud")
    if (engine or "").lower().startswith("litellm:"):
        return rates.get(engine.lower().split("/")[0], None)
    return None

# Compteurs reels du dernier appel, par thread (l API est multi-thread) :
# les jambes y deposent {"total_tokens": N}, _done les consomme et efface.
_TLS = threading.local()


def _openai_usage(data: dict) -> dict | None:
    """total_tokens d une reponse OpenAI-like (None si absent)."""
    try:
        u = data.get("usage") or {}
        total = int(u.get("total_tokens", 0)) or (
            int(u.get("prompt_tokens", 0)) + int(u.get("completion_tokens", 0)))
        return {"total_tokens": total} if total > 0 else None
    except Exception:
        return None


def _ollama_usage(data: dict) -> dict | None:
    """total_tokens d une reponse Ollama /api/generate (None si absent)."""
    try:
        total = int(data.get("prompt_eval_count", 0)) + int(data.get("eval_count", 0))
        return {"total_tokens": total} if total > 0 else None
    except Exception:
        return None


def _record_usage(engine: str | None, seconds: float, prompt: str = "",
                  text: str | None = None, total_tokens: int | None = None,
                  legs: list | None = None, model: str = "") -> None:
    """Une ligne JSON par appel LLM (lu par Xenon : couts estimes).

    Tokens reels si fournis, sinon estimes ~ caracteres/4 (convention).
    legs = [[jambe, statut]...] de la tentative (vide si routeur/cache).
    model = label complet pour le cout et l affichage ("" si inconnu).
    est_cost_usd = null quand le prix est inconnu (jamais 0 par defaut).
    Jamais bloquant, jamais d exception.
    """
    try:
        prompt_chars = len(prompt or "")
        resp_chars = len(text or "")
        if total_tokens is None:
            total_tokens = round((prompt_chars + resp_chars) / 4)
            reels = False
        else:
            reels = True
        rate = _model_rate(model, engine)
        cost = None if rate is None else round(total_tokens * rate / 1_000_000, 6)
        path = _usage_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"day": time.strftime("%Y-%m-%d"),
                 "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                 "engine": engine or "deterministe",
                 "model": model or "",
                 "latency_s": round(seconds, 1),
                 "prompt_chars": prompt_chars, "resp_chars": resp_chars,
                 "tokens": total_tokens, "tokens_reels": reels,
                 "legs": [[str(a), str(b)] for a, b in (legs or [])][:8],
                 "est_cost_usd": cost}
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
        # borne : garde les 2000 dernieres lignes
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) > 2000:
                path.write_text("\n".join(lines[-2000:]) + "\n", encoding="utf-8")
        except Exception:
            pass
    except Exception:
        pass


def _litellm_router(prompt: str, system: str) -> tuple[str | None, str]:
    """Routeur externe opt-in (KURO_ROUTER=litellm). Toujours sans crash.

    Ordre = chaine Kuro (openrouter, groq, deepseek, local). Absent ou non
    configure -> repli sur la chaine interne (l appelant continue).
    """
    if os.environ.get("KURO_ROUTER") != "litellm":
        return None, "router-off"
    fallbacks: list[str] = []
    local_model = os.environ.get("OLLAMA_MODEL")
    if local_model and not local_model.endswith(":cloud"):
        fallbacks.append(f"ollama/{local_model}")
    if os.environ.get("OPENROUTER_API_KEY"):
        fallbacks.append("openrouter/" + os.environ.get(
            "OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL))
    if os.environ.get("GROQ_API_KEY"):
        fallbacks.append("groq/" + os.environ.get(
            "GROQ_MODEL", DEFAULT_GROQ_MODEL))
    if os.environ.get("NVIDIA_API_KEY"):
        fallbacks.append("nvidia_nim/" + os.environ.get(
            "NVIDIA_MODEL", "moonshotai/kimi-k3"))
    if os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_AI_KEY", ""):
        fallbacks.append("gemini/" + os.environ.get(
            "GEMINI_MODEL", "gemini-2.5-flash"))
    if os.environ.get("HF_TOKEN", "") or os.environ.get("HUGGINGFACE_API_KEY", ""):
        fallbacks.append("huggingface/" + os.environ.get(
            "HF_MODEL", "zai-org/GLM-5.3"))
    if os.environ.get("MISTRAL_API_KEY"):
        fallbacks.append("mistral/" + os.environ.get(
            "MISTRAL_MODEL", "mistral-small-latest"))
    if os.environ.get("DEEPSEEK_API_KEY"):
        fallbacks.append("deepseek/" + os.environ.get(
            "DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL))
    if not fallbacks:
        return None, "router-empty"
    try:
        import litellm
    except ImportError:
        return None, "no-litellm"
    if "OLLAMA_API_BASE" not in os.environ:
        os.environ["OLLAMA_API_BASE"] = os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)
    primary, rest = fallbacks[0], fallbacks[1:]
    try:
        resp = litellm.completion(
            model=primary,
            fallbacks=rest or None,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2500,
            timeout=150,
        )
        text = (resp.choices[0].message.content or "").strip()
        try:
            raw = resp.usage
            _TLS.usage = {"total_tokens": int(raw.prompt_tokens)
                          + int(raw.completion_tokens)}
        except Exception:
            _TLS.usage = None
        if text:
            return text, f"litellm:{primary}"
        return None, "litellm-empty"
    except Exception as exc:
        return None, f"litellm-error({type(exc).__name__})"


def _pollinations(prompt: str, system: str) -> tuple[str | None, str]:
    """Filet sans cle, copie du pattern OpenQuant (1 req/15s anonyme).

    Kill-switch : KURO_POLLINATIONS=0. Jamais avant les jambes avec cle.
    """
    if os.environ.get("KURO_POLLINATIONS", "1") == "0":
        return None, "disabled"
    data = _post(
        "https://text.pollinations.ai/openai",
        {"model": "openai",
         "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
         "max_tokens": int(os.environ.get("POLLINATIONS_MAX_TOKENS", "1200")),
         "temperature": 0.3},
        {},
        timeout=120,
    )
    if not data:
        return None, "error"
    _TLS.usage = _openai_usage(data)
    try:
        msg = data["choices"][0]["message"]
        text = (msg.get("content") or msg.get("reasoning") or "").strip()
        return (text, "ok") if text else (None, "empty")
    except Exception:
        return None, "bad-shape"


# Disjoncteur (copie du pattern OpenQuant) : 3 echecs reels consecutifs
# -> jambe sautee pendant KURO_CB_COOLDOWN (defaut 1800 s). Les statuts
# de non-configuration ne comptent jamais (pas de inutile).
_CB_FAILS = 3
_CB_CONFIG_STATUSES = {"no-key", "no-local-model", "cloud-not-here", "disabled",
                       "not-pulled", "no-cloud-model", "router-off", "no-litellm",
                       "router-empty"}


def _breaker_path() -> Path:
    return Path.home() / ".kuro" / "llm_breaker.json"


def _breaker_cooldown() -> int:
    try:
        return max(60, int(os.environ.get("KURO_CB_COOLDOWN", "1800")))
    except Exception:
        return 1800


def _breaker_skip(label: str) -> str | None:
    """Message restant si disjoncte, sinon None. Jamais d exception."""
    try:
        state = json.loads(_breaker_path().read_text(encoding="utf-8"))
        entry = state.get(label) or {}
        left = float(entry.get("cool_until", 0) or 0) - time.time()
        if left > 0:
            return f"breaker {max(1, round(left / 60))} min restantes"
        return None
    except Exception:
        return None


def _breaker_note(label: str, failed: bool) -> None:
    """Succes -> reset ; echec reel -> compteur, disjoncte apres 3."""
    try:
        path = _breaker_path()
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(state, dict):
                state = {}
        except Exception:
            state = {}
        if failed:
            entry = state.get(label) or {}
            fails = int(entry.get("fails", 0) or 0) + 1
            entry = {"fails": fails, "cool_until": 0.0}
            if fails >= _CB_FAILS:
                entry["cool_until"] = time.time() + _breaker_cooldown()
            state[label] = entry
        else:
            state.pop(label, None)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
    except Exception:
        pass


def _chat_completions(base: str, model: str, key: str, prompt: str,
                      system: str, timeout: int = 120,
                      extra_headers: dict | None = None,
                      max_tokens: int = 1200) -> tuple[str | None, str]:
    """Appel OpenAI chat/completions generique (copie du pattern OpenQuant).

    Retourne (texte, "ok") ou (None, statut). Jamais d exception levee
    (les erreurs reseau remontent en "error" via _post).
    """
    if not key:
        return None, "no-key"
    headers = {"Authorization": f"Bearer {key}"}
    if extra_headers:
        headers.update(extra_headers)
    data = _post(
        f"{base.rstrip('/')}/chat/completions",
        {"model": model,
         "messages": [{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
         "max_tokens": int(os.environ.get("KURO_CHAT_MAX_TOKENS", str(max_tokens))),
         "temperature": 0.3},
        headers,
        timeout=timeout,
    )
    if not data:
        return None, "error"
    _TLS.usage = _openai_usage(data)
    try:
        msg = data["choices"][0]["message"]
        text = (msg.get("content") or msg.get("reasoning") or "").strip()
        return (text, "ok") if text else (None, "empty")
    except Exception:
        return None, "bad-shape"


def _nvidia(prompt: str, system: str) -> tuple[str | None, str]:
    """NVIDIA Build gratuit (Kimi K3, le + intelligent gratuit)."""
    return _chat_completions(
        os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        os.environ.get("NVIDIA_MODEL", "moonshotai/kimi-k3"),
        os.environ.get("NVIDIA_API_KEY", ""), prompt, system, timeout=150)


def _gemini(prompt: str, system: str) -> tuple[str | None, str]:
    """Gemini gratuit permanent (1M ctx). Cle : aistudio.google.com."""
    return _chat_completions(
        os.environ.get("GEMINI_BASE_URL",
                       "https://generativelanguage.googleapis.com/v1beta/openai/"),
        os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
        os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_AI_KEY", ""),
        prompt, system, timeout=120)


def _hf(prompt: str, system: str) -> tuple[str | None, str]:
    """HuggingFace Inference Providers (free tier + credits mensuels)."""
    return _chat_completions(
        os.environ.get("HF_BASE_URL", "https://router.huggingface.co/v1"),
        os.environ.get("HF_MODEL", "zai-org/GLM-5.3"),
        os.environ.get("HF_TOKEN", "") or os.environ.get("HUGGINGFACE_API_KEY", ""),
        prompt, system, timeout=150)


def _mistral(prompt: str, system: str) -> tuple[str | None, str]:
    """Mistral free tier (quotas justes). Cle : console.mistral.ai."""
    return _chat_completions(
        os.environ.get("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"),
        os.environ.get("MISTRAL_MODEL", "mistral-small-latest"),
        os.environ.get("MISTRAL_API_KEY", ""), prompt, system, timeout=120)


def _legs_for_tier(tier: str) -> list[tuple]:
    """Ordre des jambes par besoin : routine=gratuit d abord, dur=costaud d abord."""
    g = globals()  # resolu a l appel (les tests monkeypatchent ces noms)
    table = {
        "openrouter": (g["_openrouter"],
                       "openrouter/" + os.environ.get(
                           "OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL),
                       {"no-key"}),
        "groq": (g["_groq"],
                 "groq/" + os.environ.get("GROQ_MODEL", DEFAULT_GROQ_MODEL),
                 {"no-key"}),
        "nvidia": (g["_nvidia"],
                   "nvidia/" + os.environ.get("NVIDIA_MODEL", "moonshotai/kimi-k3"),
                   {"no-key"}),
        "gemini": (g["_gemini"],
                   "gemini/" + os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
                   {"no-key"}),
        "hf": (g["_hf"],
               "hf/" + os.environ.get("HF_MODEL", "zai-org/GLM-5.3"),
               {"no-key"}),
        "mistral": (g["_mistral"],
                    "mistral/" + os.environ.get("MISTRAL_MODEL", "mistral-small-latest"),
                    {"no-key"}),
        "deepseek": (g["_deepseek"],
                     "deepseek/" + os.environ.get(
                         "DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
                     {"no-key"}),
        "local": (g["_local_ollama"], "ollama-local",
                  {"no-local-model", "cloud-not-here"}),
        "cloud": (g["_ollama"], "ollama-cloud", set()),
        "pollinations": (g["_pollinations"], "pollinations", {"disabled"}),
    }
    orders = {
        "routine": ["local", "pollinations", "groq", "nvidia", "gemini",
                    "hf", "mistral", "openrouter", "deepseek", "cloud"],
        "dur": ["openrouter", "deepseek", "nvidia", "groq", "gemini", "hf",
                "mistral", "cloud", "local", "pollinations"],
        "auto": ["openrouter", "groq", "deepseek", "nvidia", "gemini", "hf",
                 "mistral", "local", "cloud", "pollinations"],
    }
    return [table[name] for name in orders.get(tier, orders["auto"])]


def _alert_brain_down() -> None:
    """Discord : cerveau indisponible (cycle complet uniquement, 1 fois / 24h max).

    La sentinelle 30min tourne sur VM fraiche (/tmp vide) : sans ce garde, chaque
    run re-poste l'alerte. KURO_FULL vaut 'false' en sentinelle, 'true' en cycle
    complet, absent en local (alerte autorisee).
    """
    if os.environ.get("KURO_FULL") == "false":
        return
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
                "description": (
                    f"OpenRouter ({os.environ.get('OPENROUTER_MODEL', DEFAULT_OPENROUTER_MODEL)}) "
                    "et Ollama cloud injoignables. "
                    + ("DeepSeek : cle absente — `gh secret set DEEPSEEK_API_KEY --repo Lemniscate-world/kuro-rules`. "
                       if not os.environ.get("DEEPSEEK_API_KEY") else "DeepSeek : cle presente mais appel en echec. ")
                    + "Le robot continue en mode déterministe."
                ),
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


def ask(prompt: str, system: str = "Tu es l'analyste du studio lambda-Section.",
        tier: str = "auto") -> str | None:
    """Chaîne : routeur opt-in, puis jambes dans l ordre du tier."""
    start = time.monotonic()

    def _done(text: str | None, engine: str, trail: list | None = None,
              model: str = "") -> str | None:
        seconds = time.monotonic() - start
        usage = getattr(_TLS, "usage", None)
        _TLS.usage = None
        tokens = None
        try:
            tokens = int((usage or {}).get("total_tokens", 0)) or None
        except Exception:
            tokens = None
        _record_brain(engine if text else None, seconds, prompt, model)
        _record_usage(engine if text else None, seconds, prompt, text, tokens,
                      trail or [], model)
        if text:
            _cache_store(prompt, text)
        return text

    text, status = _litellm_router(prompt, system)
    if text:
        print(f"kuro_llm: routeur litellm ok ({status})")
        return _done(text, status, [], model=status)
    if status not in ("router-off", "no-litellm", "router-empty"):
        print(f"kuro_llm: routeur litellm indisponible ({status})")
    cached = _cache_lookup(prompt)
    if cached:
        print("kuro_llm: cache exact ok (0 appel)")
        return _done(cached, "cache", [])
    trail: list = []
    for _fn, label, quiet in _legs_for_tier(tier):
        short = label.split("/")[0]
        skip_msg = _breaker_skip(short)
        if skip_msg is not None:
            trail.append([short, "breaker-cool"])
            continue
        text, status = _fn(prompt, system)
        trail.append([short, status])
        if text:
            print(f"kuro_llm: {label} ok")
            _breaker_note(short, False)
            return _done(text, short, trail, model=label)
        _breaker_note(short, status not in quiet
                      and status not in _CB_CONFIG_STATUSES)
        if status not in quiet:
            print(f"kuro_llm: {label} indisponible ({status})")
    print("kuro_llm: toutes jambes epuisees, mode deterministe")
    _queue_pending(prompt, system, tier)
    _alert_brain_down()
    return _done(None, None, trail)


def _recent_leg_outcomes(limit: int = 60) -> dict[str, str]:
    """Dernier statut connu par jambe (historique local). Jamais d exception."""
    out: dict[str, str] = {}
    try:
        lines = _usage_path().read_text(encoding="utf-8").splitlines()[-limit:]
    except Exception:
        return out
    for line in lines:
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        for pair in entry.get("legs") or []:
            try:
                out[str(pair[0])] = str(pair[1])
            except Exception:
                continue
    return out


def _norm_leg(engine: str | None) -> str:
    name = (engine or "").strip()
    if name.startswith("litellm:"):
        name = name[len("litellm:"):]
    return name.split("/")[0] or "?"


def brain_status() -> list[dict]:
    """Etat live des jambes SANS depenser de tokens (cles + tags + historique).

    state : ok (prouve recent) | down (echec recent) | off (non configure) |
    unknown (configure jamais teste) | on (toujours pret). Jamais d exception.
    """
    rows: list[dict] = []
    try:
        recent = _recent_leg_outcomes()

        def _keyed(name: str, var: str, var2: str = "") -> None:
            key = os.environ.get(var, "") or (os.environ.get(var2, "") if var2 else "")
            if not key:
                rows.append({"leg": name, "state": "off", "detail": "pas de cle"})
            elif recent.get(name) == "ok":
                rows.append({"leg": name, "state": "ok", "detail": "repond"})
            elif recent.get(name):
                rows.append({"leg": name, "state": "down",
                             "detail": str(recent[name])[:40]})
            else:
                rows.append({"leg": name, "state": "unknown",
                             "detail": "configure, jamais teste"})

        _keyed("openrouter", "OPENROUTER_API_KEY")
        _keyed("groq", "GROQ_API_KEY")
        _keyed("nvidia", "NVIDIA_API_KEY")
        _keyed("gemini", "GEMINI_API_KEY", "GOOGLE_AI_KEY")
        _keyed("hf", "HF_TOKEN", "HUGGINGFACE_API_KEY")
        _keyed("mistral", "MISTRAL_API_KEY")
        _keyed("deepseek", "DEEPSEEK_API_KEY")

        model = os.environ.get("OLLAMA_MODEL")
        if not model or model.endswith(":cloud"):
            rows.append({"leg": "local", "state": "off",
                         "detail": "OLLAMA_MODEL absent"})
        else:
            tags = _get_json(
                f"{os.environ.get('OLLAMA_URL', DEFAULT_OLLAMA_URL)}/api/tags") or {}
            names = [m.get("name", "") for m in tags.get("models", [])]
            if not tags:
                rows.append({"leg": "local", "state": "down",
                             "detail": "daemon injoignable"})
            elif model in names:
                rows.append({"leg": "local", "state": "ok",
                             "detail": f"modele {model}"})
            else:
                rows.append({"leg": "local", "state": "off",
                             "detail": "non telecharge"})

        if cloud_candidates(os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)):
            rows.append({"leg": "ollama-cloud", "state": "unknown",
                         "detail": "quota starter ?"})
        else:
            rows.append({"leg": "ollama-cloud", "state": "off",
                         "detail": "aucun modele :cloud"})

        if os.environ.get("KURO_POLLINATIONS", "1") == "0":
            rows.append({"leg": "pollinations", "state": "off",
                         "detail": "desactive"})
        else:
            rows.append({"leg": "pollinations", "state": "unknown",
                         "detail": "1 req/15s, jamais sonde"})

        if os.environ.get("KURO_ROUTER") != "litellm":
            rows.append({"leg": "litellm", "state": "off",
                         "detail": "routeur non arme"})
        else:
            try:
                import litellm  # noqa: F401

                rows.append({"leg": "litellm", "state": "on",
                             "detail": "routeur arme"})
            except ImportError:
                rows.append({"leg": "litellm", "state": "down",
                             "detail": "lib absente"})
    except Exception:
        pass
    return rows


def available() -> str | None:
    """Nom du moteur dispo sans consommer d'appel."""
    if os.environ.get("OPENROUTER_API_KEY"):
        return "openrouter"
    if os.environ.get("GROQ_API_KEY"):
        return "groq"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    local_model = os.environ.get("OLLAMA_MODEL")
    if local_model and not local_model.endswith(":cloud"):
        tags = _get_json(
            f"{os.environ.get('OLLAMA_URL', DEFAULT_OLLAMA_URL)}/api/tags") or {}
        if local_model in [m.get("name", "") for m in tags.get("models", [])]:
            return "ollama-local"
    if cloud_candidates(os.environ.get("OLLAMA_URL", DEFAULT_OLLAMA_URL)):
        return "ollama-cloud"
    return None


def stats_command(since: str = "", as_json: bool = False) -> int:
    """Stats du journal d usage : appels/couts/latence par moteur (+ cache a part).

    Meme regle d honestete que le TUI : seuls les vrais appels comptent,
    couts inconnus comptes a part, jamais $0 menteur.
    """
    from collections import Counter
    rows: list[dict] = []
    try:
        lines = _usage_path().read_text(encoding="utf-8").splitlines()[-2000:]
    except Exception:
        lines = []
    for line in lines:
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        day = str(entry.get("day") or "")
        if since and day < since:
            continue
        rows.append(entry)
    real = [e for e in rows if str(e.get("engine") or "?") not in
            ("", "cache", "deterministe")]
    cache = len(rows) - len(real)
    by_engine: dict[str, dict] = {}
    for e in real:
        eng = str(e.get("engine") or "?")
        slot = by_engine.setdefault(eng, {"calls": 0, "cost": 0.0,
                                         "unknown": 0, "lat": []})
        slot["calls"] += 1
        raw = e.get("est_cost_usd")
        if raw is None:
            slot["unknown"] += 1
        else:
            try:
                slot["cost"] += float(raw or 0.0)
            except Exception:
                pass
        try:
            slot["lat"].append(float(e.get("latency_s") or 0.0))
        except Exception:
            pass
    for slot in by_engine.values():
        lats = sorted(slot.pop("lat"))
        slot["cost"] = round(slot["cost"], 6)
        slot["p50"] = lats[len(lats) // 2] if lats else None
        slot["p95"] = lats[min(len(lats) - 1, int(len(lats) * 0.95))] if lats else None
    payload = {"entries": len(rows), "real_calls": len(real),
               "cache_hits": cache, "by_engine": by_engine,
               "pricing": pricing_version()}
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0
    print(f"Journal : {len(rows)} entrees ({len(real)} appels reels, {cache} hits cache)")
    for eng in sorted(by_engine, key=lambda k: -by_engine[k]["calls"]):
        s = by_engine[eng]
        unk = f" +{s['unknown']} cout inconnu" if s["unknown"] else ""
        print(f"  {eng:<16} {s['calls']:>4} appels  ~${s['cost']:.4f}{unk}  "
              f"p50 {s['p50']}s p95 {s['p95']}s")
    print(f"Tarifs : {payload['pricing']}")
    return 0


if __name__ == "__main__":
    if "--drain" in sys.argv:
        drained = drain_queue()
        for item in drained:
            print(f"[drained] {item['prompt'][:80]} -> {item['text'][:200]}")
        print(f"file traitee : {len(drained)} reponse(s)")
    elif "--stats" in sys.argv:
        try:
            since = sys.argv[sys.argv.index("--stats") + 1]
            if since.startswith("-"):
                since = ""
        except (ValueError, IndexError):
            since = ""
        raise SystemExit(stats_command(
            since=since, as_json="--json" in sys.argv))
    else:
        engine = available()
        print(f"moteur disponible: {engine or 'aucun (mode déterministe)'}")
