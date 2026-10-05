"""Tests kuro_compute — validation locale, forwarding Helium, file persistee. Zero reseau reel."""

import io
import json
import sys
import urllib.error
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import kuro_compute as kc  # noqa: E402
from kuro_dashboard import api as kuro_api  # noqa: E402


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def _fake_urlopen(calls, routes):
    """routes: {path: payload} ou {path: ComputeError/urllib error a lever}."""
    def _fake(req, timeout=10):
        body = json.loads(req.data.decode("utf-8")) if req.data else None
        calls.append({
            "url": req.full_url,
            "method": req.get_method(),
            "auth": req.get_header("Authorization"),
            "body": body,
        })
        path = req.full_url.split("http://x", 1)[1] if req.full_url.startswith("http://x") else req.full_url
        outcome = routes[path]
        if isinstance(outcome, Exception):
            raise outcome
        return _FakeResp(outcome)
    return _fake


def _http_error(code, message):
    fp = io.BytesIO(json.dumps({"error": message}).encode("utf-8"))
    return urllib.error.HTTPError("http://x/requests", code, message, {}, fp)


def test_validation_rejects_bad_input():
    bad = [
        dict(project="", rtype="gpu", amount=16, max_price=1.0, hours=2, image="", gpus=0),
        dict(project="p", rtype="", amount=16, max_price=1.0, hours=2, image="", gpus=0),
        dict(project="p", rtype="gpu", amount=0, max_price=1.0, hours=2, image="", gpus=0),
        dict(project="p", rtype="gpu", amount=16, max_price=0.0, hours=2, image="", gpus=0),
        dict(project="p", rtype="gpu", amount=16, max_price=1.0, hours=721, image="", gpus=0),
        dict(project="p", rtype="gpu", amount=16, max_price=1.0, hours=2, image="x" * 257, gpus=0),
        dict(project="p", rtype="gpu", amount=16, max_price=1.0, hours=2, image="", gpus=17),
    ]
    for kwargs in bad:
        try:
            kc._check_request(**kwargs)
        except kc.ComputeError as exc:
            assert exc.status == 400
        else:
            raise AssertionError(f"validation acceptee a tort : {kwargs}")


def test_list_offers_forwards_bearer(monkeypatch):
    calls = []
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setenv("HELIUM_API_TOKEN", "tok123")
    monkeypatch.setattr("urllib.request.urlopen",
                        _fake_urlopen(calls, {"/offers": [{"id": "offer-1"}]}))
    assert kc.list_offers() == [{"id": "offer-1"}]
    assert calls[0]["auth"] == "Bearer tok123"
    assert calls[0]["url"].endswith("/offers")


def test_create_request_posts_requester_and_persists_queue(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setenv("HELIUM_API_TOKEN", "tok123")
    monkeypatch.setattr(kc, "QUEUE_PATH", tmp_path / "compute_queue.json")
    monkeypatch.setattr("urllib.request.urlopen",
                        _fake_urlopen(calls, {"/requests": {"id": "req-abc", "status": "open"}}))
    created = kc.create_request("openquant", image="ubuntu:22.04", gpus=1)
    assert created["request_id"] == "req-abc"
    assert calls[0]["body"]["requester"] == "kuro:openquant"
    assert calls[0]["body"]["image"] == "ubuntu:22.04"
    # La file survit au restart (relecture disque).
    reloaded = kc.queue_load()
    assert len(reloaded) == 1 and reloaded[0]["request_id"] == "req-abc"


def test_create_request_400_does_not_touch_queue(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setattr(kc, "QUEUE_PATH", tmp_path / "compute_queue.json")
    monkeypatch.setattr("urllib.request.urlopen",
                        _fake_urlopen(calls, {"/requests": _http_error(400, "amount sup")}))
    try:
        kc.create_request("openquant", amount=16)
    except kc.ComputeError as exc:
        assert exc.status == 400
    else:
        raise AssertionError("400 Helium aurait du remonter")
    assert kc.queue_load() == []


def test_template_forwarded_and_too_long_blocked(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setattr(kc, "QUEUE_PATH", tmp_path / "compute_queue.json")
    monkeypatch.setattr("urllib.request.urlopen",
                        _fake_urlopen(calls, {"/requests": {"id": "req-t", "status": "open"}}))
    created = kc.create_request("openquant", template="jupyter")
    assert created["request_id"] == "req-t"
    assert calls[0]["body"]["template"] == "jupyter"
    try:
        kc.create_request("openquant", template="t" * 65)
    except kc.ComputeError as exc:
        assert exc.status == 400
    else:
        raise AssertionError("template trop long aurait du bloquer")
    assert len(calls) == 1


def test_min_bench_forwarded_and_negative_blocked(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setattr(kc, "QUEUE_PATH", tmp_path / "compute_queue.json")
    monkeypatch.setattr("urllib.request.urlopen",
                        _fake_urlopen(calls, {"/requests": {"id": "req-b", "status": "open"}}))
    kc.create_request("openquant", min_bench=25.5)
    assert calls[0]["body"]["min_bench"] == 25.5
    try:
        kc.create_request("openquant", min_bench=-1)
    except kc.ComputeError as exc:
        assert exc.status == 400
    else:
        raise AssertionError("min_bench negatif aurait du bloquer")
    assert len(calls) == 1


def test_local_validation_blocks_before_network(monkeypatch):
    calls = []
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(calls, {}))
    try:
        kc.create_request("openquant", amount=0)
    except kc.ComputeError as exc:
        assert exc.status == 400
    else:
        raise AssertionError("validation locale aurait du bloquer")
    assert calls == []


def test_unreachable_helium_maps_502(monkeypatch):
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setattr("urllib.request.urlopen", _unreachable())
    try:
        kc.list_offers()
    except kc.ComputeError as exc:
        assert exc.status == 502
    else:
        raise AssertionError("helium injoignable aurait du lever 502")


def _unreachable():
    def _fake(req, timeout=10):
        raise urllib.error.URLError("refuse")
    return _fake


def test_file_scheme_rejected_without_network(monkeypatch):
    calls = []
    monkeypatch.setenv("HELIUM_API_URL", "file:///etc")
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(calls, {}))
    try:
        kc.list_offers()
    except kc.ComputeError as exc:
        assert exc.status == 502
    else:
        raise AssertionError("schema file:// aurait du etre refuse")
    assert calls == []


def test_get_request_status_merges_request_and_matches(monkeypatch):
    calls = []
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen(calls, {
        "/requests/req-abc": {"id": "req-abc", "status": "open"},
        "/requests/req-abc/matches": [{"id": "match-1"}],
    }))
    status = kc.get_request_status("req-abc")
    assert status["request"]["id"] == "req-abc"
    assert status["matches"] == [{"id": "match-1"}]


def test_api_compute_status_mapping():
    assert kuro_api._compute_status(kc.ComputeError(400, "x")) == 400
    assert kuro_api._compute_status(kc.ComputeError(404, "x")) == 404
    assert kuro_api._compute_status(kc.ComputeError(409, "x")) == 409
    assert kuro_api._compute_status(kc.ComputeError(429, "quota")) == 429
    assert kuro_api._compute_status(kc.ComputeError(502, "x")) == 502
    assert kuro_api._compute_status(ValueError("boom")) == 502


def test_quota_429_passthrough(monkeypatch):
    monkeypatch.setenv("HELIUM_API_URL", "http://x")
    monkeypatch.setattr("urllib.request.urlopen",
                        _fake_urlopen([], {"/requests": _http_error(429, "quota exceeded")}))
    try:
        kc.create_request("openquant", amount=16)
    except kc.ComputeError as exc:
        assert exc.status == 429
        assert "quota" in str(exc)
    else:
        raise AssertionError("429 Helium aurait du remonter")


def test_kuro_auth_gate_401_shape(monkeypatch):
    handler = SimpleNamespace(headers={})
    monkeypatch.setenv("KURO_API_TOKEN", "secret-kuro")
    assert kuro_api.Handler._auth_ok(handler) is False
    handler = SimpleNamespace(headers={"Authorization": "Bearer secret-kuro"})
    assert kuro_api.Handler._auth_ok(handler) is True
    monkeypatch.delenv("KURO_API_TOKEN")
    assert kuro_api.Handler._auth_ok(SimpleNamespace(headers={})) is True
