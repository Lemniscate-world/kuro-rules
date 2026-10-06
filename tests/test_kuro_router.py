"""Tests routeur LLM : jambe locale, opt-in litellm, llm_last.json."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

import kuro_llm  # noqa: E402


def _boom(*args, **kwargs):
    raise AssertionError("aucun appel reseau attendu")


def test_local_sans_modele_ni_reseau(monkeypatch):
    monkeypatch.setattr(kuro_llm, "_post", _boom)
    assert kuro_llm._local_ollama("q", "s") == (None, "no-local-model")


def test_local_ignore_cloud(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "kimi-k2.7:cloud")
    monkeypatch.setattr(kuro_llm, "_post", _boom)
    assert kuro_llm._local_ollama("q", "s") == (None, "cloud-not-here")


def test_local_succes(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setattr(kuro_llm, "_get_json",
                        lambda url, timeout=5: {"models": [{"name": "qwen3:8b"}]})
    monkeypatch.setattr(kuro_llm, "_post",
                        lambda *a, **k: {"response": "  salut  "})
    assert kuro_llm._local_ollama("q", "s") == ("salut", "ok")


def test_local_non_telecharge_sans_post(monkeypatch):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setattr(kuro_llm, "_get_json",
                        lambda url, timeout=5: {"models": [{"name": "autre"}]})
    monkeypatch.setattr(kuro_llm, "_post", _boom)
    text, status = kuro_llm._local_ollama("q", "s")
    assert text is None and status.startswith("not-pulled")


def test_ask_enregistre_moteur(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: ("ok-text", "ok"))
    assert kuro_llm.ask("q") == "ok-text"
    data = json.loads((tmp_path / "llm_last.json").read_text(encoding="utf-8"))
    assert data["engine"] == "openrouter"
    assert isinstance(data["latency_s"], (int, float))


def test_router_off_par_defaut():
    assert kuro_llm._litellm_router("q", "s") == (None, "router-off")


def test_router_vide_sans_moteur(monkeypatch):
    monkeypatch.setenv("KURO_ROUTER", "litellm")
    for var in ("OPENROUTER_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY", "OLLAMA_MODEL"):
        monkeypatch.delenv(var, raising=False)
    assert kuro_llm._litellm_router("q", "s") == (None, "router-empty")


def _fake_litellm(calls, behaviour="ok"):
    def completion(**kwargs):
        calls.append(kwargs)
        if behaviour == "boom":
            raise RuntimeError("panne simulee")
        msg = SimpleNamespace(content="hello-local" if behaviour == "ok" else "  ")
        return SimpleNamespace(choices=[SimpleNamespace(message=msg)])

    return SimpleNamespace(completion=completion)


def test_router_litellm_succes(monkeypatch):
    calls = []
    monkeypatch.setitem(sys.modules, "litellm", _fake_litellm(calls))
    monkeypatch.setenv("KURO_ROUTER", "litellm")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle-test")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.setenv("OLLAMA_API_BASE", "http://x")
    text, engine = kuro_llm._litellm_router("q", "s")
    assert (text, engine) == ("hello-local", "litellm:ollama/qwen3:8b")
    assert calls[0]["model"] == "ollama/qwen3:8b"
    assert any(str(f).startswith("openrouter/") for f in calls[0]["fallbacks"])


def test_router_panne_bascule_chaine(monkeypatch):
    monkeypatch.setitem(sys.modules, "litellm", _fake_litellm([], "boom"))
    monkeypatch.setenv("KURO_ROUTER", "litellm")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setenv("OLLAMA_API_BASE", "http://x")
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: ("chain-ok", "ok"))
    assert kuro_llm.ask("q") == "chain-ok"


def test_pollinations_desactive_sans_reseau(monkeypatch):
    monkeypatch.setenv("KURO_POLLINATIONS", "0")
    monkeypatch.setattr(kuro_llm, "_post", _boom)
    assert kuro_llm._pollinations("q", "s") == (None, "disabled")


def test_pollinations_succes(monkeypatch):
    monkeypatch.delenv("KURO_POLLINATIONS", raising=False)
    monkeypatch.setattr(kuro_llm, "_post", lambda *a, **k: {
        "choices": [{"message": {"content": "  hello-monde  "}}]})
    assert kuro_llm._pollinations("q", "s") == ("hello-monde", "ok")


def test_tiers_ordres(monkeypatch):
    appels = []

    def _mk(name):
        return lambda p, s: (appels.append(name), (None, "vide"))[1]

    monkeypatch.setattr(kuro_llm, "_openrouter", _mk("openrouter"))
    monkeypatch.setattr(kuro_llm, "_groq", _mk("groq"))
    monkeypatch.setattr(kuro_llm, "_nvidia", _mk("nvidia"))
    monkeypatch.setattr(kuro_llm, "_gemini", _mk("gemini"))
    monkeypatch.setattr(kuro_llm, "_hf", _mk("hf"))
    monkeypatch.setattr(kuro_llm, "_mistral", _mk("mistral"))
    monkeypatch.setattr(kuro_llm, "_deepseek", _mk("deepseek"))
    monkeypatch.setattr(kuro_llm, "_local_ollama", _mk("local"))
    monkeypatch.setattr(kuro_llm, "_ollama", _mk("cloud"))
    monkeypatch.setattr(kuro_llm, "_pollinations", _mk("pollinations"))
    monkeypatch.setattr(kuro_llm, "_alert_brain_down", lambda: None)
    kuro_llm.ask("q", tier="routine")
    assert appels == ["local", "pollinations", "groq", "nvidia", "gemini",
                      "hf", "mistral", "openrouter", "deepseek", "cloud"]
    appels.clear()
    kuro_llm.ask("q", tier="dur")
    assert appels == ["openrouter", "deepseek", "nvidia", "groq", "gemini",
                      "hf", "mistral", "cloud", "local", "pollinations"]
    appels.clear()
    kuro_llm.ask("q", tier="nimporte-quoi")
    assert appels == ["openrouter", "groq", "deepseek", "nvidia", "gemini",
                      "hf", "mistral", "local", "cloud", "pollinations"]


def test_groq_sans_cle_sans_reseau(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(kuro_llm, "_post", _boom)
    assert kuro_llm._groq("q", "s") == (None, "no-key")


def test_groq_succes(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "cle-test")
    monkeypatch.setattr(kuro_llm, "_post", lambda *a, **k: {
        "choices": [{"message": {"content": "  hello-groq  "}}]})
    assert kuro_llm._groq("q", "s") == ("hello-groq", "ok")


def test_openrouter_cascade_essaie_suivant(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle-test")
    monkeypatch.delenv("OPENROUTER_MODELS", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    calls = []
    def _fake_post(url, payload, headers, timeout):
        calls.append(payload["model"])
        if len(calls) == 1:
            return None
        return {"choices": [{"message": {"content": "ok-cascade"}}]}
    monkeypatch.setattr(kuro_llm, "_post", _fake_post)
    text, status = kuro_llm._openrouter("q", "s")
    assert (text, status) == ("ok-cascade", "ok")
    assert len(calls) == 2


def test_prompt_hash_stable(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: ("ok", "ok"))
    kuro_llm.ask("meme question")
    h1 = json.loads((tmp_path / "llm_last.json").read_text(encoding="utf-8"))
    kuro_llm.ask("meme question")
    h2 = json.loads((tmp_path / "llm_last.json").read_text(encoding="utf-8"))
    kuro_llm.ask("question differente")
    h3 = json.loads((tmp_path / "llm_last.json").read_text(encoding="utf-8"))
    assert len(h1["prompt_hash"]) == 16
    assert h1["prompt_hash"] == h2["prompt_hash"] != h3["prompt_hash"]


def test_cache_hit_sans_legs(monkeypatch):
    def _boom(*a, **k):
        raise AssertionError("aucune jambe ne doit tourner sur cache hit")

    for leg in ("_openrouter", "_groq", "_deepseek", "_local_ollama", "_ollama",
                "_pollinations"):
        monkeypatch.setattr(kuro_llm, leg, _boom)
    kuro_llm._cache_store("q cachee", "reponse-cachee")
    assert kuro_llm.ask("q cachee") == "reponse-cachee"


def test_cache_expire_rejoue_legs(monkeypatch, tmp_path):
    vieux = {kuro_llm._prompt_hash("q"): {"text": "perime", "at": 0}}
    (tmp_path / "llm_cache.json").write_text(json.dumps(vieux), encoding="utf-8")
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: ("frais", "ok"))
    assert kuro_llm.ask("q") == "frais"


def test_file_dedup_puis_drain(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: (None, "vide"))
    monkeypatch.setattr(kuro_llm, "_groq", lambda p, s: (None, "vide"))
    monkeypatch.setattr(kuro_llm, "_deepseek", lambda p, s: (None, "vide"))
    monkeypatch.setattr(kuro_llm, "_local_ollama", lambda p, s: (None, "vide"))
    monkeypatch.setattr(kuro_llm, "_ollama", lambda p, s: (None, "vide"))
    monkeypatch.setattr(kuro_llm, "_pollinations", lambda p, s: (None, "vide"))
    monkeypatch.setattr(kuro_llm, "_alert_brain_down", lambda: None)
    assert kuro_llm.ask("q file") is None
    assert kuro_llm.ask("q file") is None
    lines = (tmp_path / "llm_queue.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["attempts"] == 2
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: ("reponse", "ok"))
    drained = kuro_llm.drain_queue()
    assert len(drained) == 1 and drained[0]["text"] == "reponse"
    rest = (tmp_path / "llm_queue.jsonl").read_text(encoding="utf-8").strip()
    assert rest == ""


def _all_fail(monkeypatch, status="error"):
    def _fail(p, s):
        return None, status

    monkeypatch.setattr(kuro_llm, "_openrouter", _fail)
    monkeypatch.setattr(kuro_llm, "_deepseek", _fail)
    monkeypatch.setattr(kuro_llm, "_local_ollama", _fail)
    monkeypatch.setattr(kuro_llm, "_ollama", _fail)
    monkeypatch.setattr(kuro_llm, "_pollinations", _fail)
    monkeypatch.setattr(kuro_llm, "_alert_brain_down", lambda: None)


def test_breaker_saute_apres_3_echecs(monkeypatch, tmp_path):
    appels = []

    def _fail_count(p, s):
        appels.append(1)
        return None, "error"

    monkeypatch.setattr(kuro_llm, "_openrouter", _fail_count)
    monkeypatch.setattr(kuro_llm, "_deepseek", lambda p, s: (None, "error"))
    monkeypatch.setattr(kuro_llm, "_local_ollama", lambda p, s: (None, "error"))
    monkeypatch.setattr(kuro_llm, "_ollama", lambda p, s: (None, "error"))
    monkeypatch.setattr(kuro_llm, "_pollinations", lambda p, s: (None, "error"))
    monkeypatch.setattr(kuro_llm, "_alert_brain_down", lambda: None)
    for _ in range(3):
        assert kuro_llm.ask("q") is None
    assert len(appels) == 3
    assert kuro_llm.ask("q") is None
    assert len(appels) == 3, "4e appel : jambe sautee par le breaker"
    state = json.loads((tmp_path / "llm_breaker.json").read_text(encoding="utf-8"))
    assert state["openrouter"]["fails"] >= 3
    assert state["openrouter"]["cool_until"] > 0


def test_breaker_reset_sur_succes(monkeypatch, tmp_path):
    _all_fail(monkeypatch)
    assert kuro_llm.ask("q") is None
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: ("ok", "ok"))
    assert kuro_llm.ask("q") == "ok"
    state = json.loads((tmp_path / "llm_breaker.json").read_text(encoding="utf-8"))
    assert "openrouter" not in state


def test_breaker_cooldown_expire(monkeypatch, tmp_path):
    import time as _time

    _all_fail(monkeypatch)
    for _ in range(3):
        kuro_llm.ask("q")
    path = tmp_path / "llm_breaker.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["openrouter"]["cool_until"] = _time.time() - 10
    path.write_text(json.dumps(state), encoding="utf-8")
    appels = []
    monkeypatch.setattr(kuro_llm, "_openrouter",
                        lambda p, s: (appels.append(1), (None, "error"))[1])
    kuro_llm.ask("q")
    assert len(appels) == 1, "cooldown expire : jambe reessayee"


def test_breaker_ignore_non_configure(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: (None, "no-key"))
    monkeypatch.setattr(kuro_llm, "_deepseek", lambda p, s: (None, "no-key"))
    monkeypatch.setattr(kuro_llm, "_local_ollama", lambda p, s: (None, "no-local-model"))
    monkeypatch.setattr(kuro_llm, "_ollama", lambda p, s: (None, "no-cloud-model"))
    monkeypatch.setattr(kuro_llm, "_pollinations", lambda p, s: (None, "disabled"))
    monkeypatch.setattr(kuro_llm, "_alert_brain_down", lambda: None)
    for _ in range(5):
        assert kuro_llm.ask("q") is None
    path = tmp_path / "llm_breaker.json"
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
        assert all(v.get("fails", 0) == 0 for v in state.values())


def test_legs_traces_dans_usage(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: ("ok", "ok"))
    assert kuro_llm.ask("q") == "ok"
    entry = _last_usage(tmp_path)
    assert ["openrouter", "ok"] in entry["legs"]


def test_brain_status_preuves_recentes(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "cle")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("KURO_ROUTER", raising=False)
    (tmp_path / "llm_usage.jsonl").write_text(json.dumps(
        {"legs": [["openrouter", "error"], ["deepseek", "ok"]]}) + "\n",
        encoding="utf-8")
    rows = {r["leg"]: r["state"] for r in kuro_llm.brain_status()}
    assert rows["openrouter"] == "down"
    assert rows["deepseek"] == "ok"
    assert rows["local"] == "off"


def _last_usage(tmp_path):
    lines = (tmp_path / "llm_usage.jsonl").read_text(encoding="utf-8").splitlines()
    assert lines, "aucune ligne d usage ecrite"
    return json.loads(lines[-1])


def test_usage_tokens_reels(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_post", lambda *a, **k: {
        "choices": [{"message": {"content": "salut"}}],
        "usage": {"prompt_tokens": 30, "completion_tokens": 70,
                  "total_tokens": 100}})
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle-test")
    assert kuro_llm.ask("bonjour le monde") == "salut"
    entry = _last_usage(tmp_path)
    assert entry["engine"] == "openrouter"
    assert entry["tokens"] == 100 and entry["tokens_reels"] is True
    assert entry["est_cost_usd"] == 0.0  # :free -> cout 0


def test_usage_estime_sans_compteurs(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_post", lambda *a, **k: {
        "choices": [{"message": {"content": "salut"}}]})
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle-test")
    assert kuro_llm.ask("bonjour") == "salut"
    entry = _last_usage(tmp_path)
    assert entry["tokens_reels"] is False
    assert entry["tokens"] == round((len("bonjour") + len("salut")) / 4)


def test_usage_ollama_reel(monkeypatch, tmp_path):
    monkeypatch.setenv("OLLAMA_MODEL", "qwen3:8b")
    monkeypatch.setattr(kuro_llm, "_get_json",
                        lambda url, timeout=5: {"models": [{"name": "qwen3:8b"}]})
    monkeypatch.setattr(kuro_llm, "_post", lambda *a, **k: {
        "response": "ok", "prompt_eval_count": 20, "eval_count": 80})
    monkeypatch.setattr(kuro_llm, "_openrouter", lambda p, s: (None, "no-key"))
    monkeypatch.setattr(kuro_llm, "_deepseek", lambda p, s: (None, "no-key"))
    assert kuro_llm.ask("question") == "ok"
    entry = _last_usage(tmp_path)
    assert entry["engine"] == "ollama-local"
    assert entry["tokens"] == 100 and entry["est_cost_usd"] == 0.0


def _write_usage(tmp_path, rows):
    path = tmp_path / "llm_usage.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n",
                    encoding="utf-8")


def test_brain_status_tout_off(monkeypatch):
    for var in ("OPENROUTER_API_KEY", "GROQ_API_KEY", "DEEPSEEK_API_KEY", "OLLAMA_MODEL",
                "KURO_ROUTER"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("KURO_POLLINATIONS", "0")
    monkeypatch.setattr(kuro_llm, "cloud_candidates", lambda base: [])
    rows = {r["leg"]: r["state"] for r in kuro_llm.brain_status()}
    assert rows["openrouter"] == "off"
    assert rows["groq"] == "off"
    assert rows["deepseek"] == "off"
    assert rows["local"] == "off"
    assert rows["pollinations"] == "off"
    assert rows["litellm"] == "off"
    assert rows["nvidia"] == "off"
    assert rows["gemini"] == "off"
    assert rows["hf"] == "off"
    assert rows["mistral"] == "off"


def test_brain_status_preuves_recentes(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "cle")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.delenv("KURO_ROUTER", raising=False)
    _write_usage(tmp_path, [
        {"engine": "openrouter", "legs": [["openrouter", "ok"]]},
        {"engine": "deterministe",
         "legs": [["openrouter", "error"], ["deepseek", "error"],
                  ["local", "no-local-model"]]},
    ])
    rows = {r["leg"]: (r["state"], r["detail"]) for r in kuro_llm.brain_status()}
    assert rows["openrouter"][0] == "down"
    assert rows["deepseek"][0] == "down"
    assert rows["local"][0] == "off"


def test_usage_enregistre_modele_complet(monkeypatch, tmp_path):
    monkeypatch.setattr(kuro_llm, "_post", lambda *a, **k: {
        "choices": [{"message": {"content": "salut"}}],
        "usage": {"total_tokens": 100}})
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle-test")
    assert kuro_llm.ask("bonjour le monde") == "salut"
    entry = _last_usage(tmp_path)
    assert entry["model"].endswith(":free"), entry
    brain = json.loads((tmp_path / "llm_last.json").read_text(encoding="utf-8"))
    assert brain["model"].endswith(":free")


def test_usage_modele_payant_cout_inconnu(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENROUTER_MODEL", "openai/gpt-4o")
    monkeypatch.setattr(kuro_llm, "_post", lambda *a, **k: {
        "choices": [{"message": {"content": "salut"}}],
        "usage": {"total_tokens": 100}})
    monkeypatch.setenv("OPENROUTER_API_KEY", "cle-test")
    assert kuro_llm.ask("bonjour") == "salut"
    entry = _last_usage(tmp_path)
    assert "gpt-4o" in entry["model"] and ":free" not in entry["model"]
    assert entry["est_cost_usd"] is None, "prix inconnu : null, pas $0 menteur"


def test_model_rate_honnete():
    assert kuro_llm._model_rate("openrouter/x:free", "openrouter") == 0.0
    assert kuro_llm._model_rate("openai/gpt-4o", "openrouter") is None
    assert kuro_llm._model_rate("", "openrouter") is None
    assert kuro_llm._model_rate("", "deepseek") == 1.0
    assert kuro_llm._model_rate("", "ollama-local") == 0.0
    assert kuro_llm._model_rate("", "groq") == 0.0
    assert kuro_llm._model_rate("x", "litellm:deepseek") == 1.0
    assert kuro_llm._model_rate("x", "litellm:openrouter") == 0.0
    assert kuro_llm._model_rate("x", "litellm:truc") is None
