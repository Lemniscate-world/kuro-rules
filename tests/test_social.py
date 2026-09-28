"""Tests kuro_discord + x_post — logique pure, zero reseau."""

import sys
from pathlib import Path

import kuro_discord as kd
import x_post as xp


def test_slug_ascii():
    assert kd.slug("Helium Chain") == "helium-chain"
    assert kd.slug("G&S Solutions") == "g-s-solutions"
    assert kd.slug("λ-Section-7 — Helium Chain").startswith("section-7")


def test_channel_name():
    assert kd.channel_name("Helium") == "proj-helium"
    assert kd.channel_name("Horcruxe Labs") == "proj-horcruxe-labs"


def test_category_name_unescape():
    assert kd.category_name("&#955;-Section-7 &mdash; Helium Chain", 0) == "SEC 07 - Helium Chain"
    assert kd.category_name("Laboratoire", 9) == "SEC LAB - Laboratoire"


def test_build_plan_filtre_statuts_et_externes():
    projs = [
        {"name": "A", "pct": 10, "status": "Actif", "desc": "d", "external_section": False, "section": "S1"},
        {"name": "B", "pct": 10, "status": "En Pause", "desc": "d", "external_section": False, "section": "S1"},
        {"name": "C", "pct": 10, "status": "Actif", "desc": "d", "external_section": True, "section": "Ext"},
    ]
    plan = kd.build_plan(projs)
    chans = [c for _, ch in plan for c, _, _ in ch]
    assert chans == ["proj-a"]


def test_webhook_for_routage():
    cmap = {"channels": {"helium": "https://wh/helium", "default": "https://wh/def"}}
    assert kd.webhook_for("Helium", cmap["channels"]) == "https://wh/helium"
    assert kd.webhook_for("Inconnu", cmap["channels"]) == "https://wh/def"


def test_webhook_for_absent(monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL", raising=False)
    assert kd.webhook_for("X", {}) == ""


def test_x_percent_encode_rfc3986():
    assert xp.percent_encode("Ladies + Gentlemen") == "Ladies%20%2B%20Gentlemen"
    assert xp.percent_encode("~tilde~") == "~tilde~"


def test_x_base_string_vecteur_rfc5849():
    # RFC 5849 §3.4.1.1 — vecteur officiel.
    params = [("file", "vacation.jpg"), ("size", "original"),
              ("oauth_consumer_key", "dpf43f3p2l4k3l03"),
              ("oauth_nonce", "kllo9940pd9333jh"),
              ("oauth_signature_method", "HMAC-SHA1"),
              ("oauth_timestamp", "1191242096"),
              ("oauth_token", "nnch734d00sl2jdk"),
              ("oauth_version", "1.0")]
    assert xp.base_string("GET", "http://photos.example.net/photos", params) == (
        "GET&http%3A%2F%2Fphotos.example.net%2Fphotos&"
        "file%3Dvacation.jpg%26oauth_consumer_key%3Ddpf43f3p2l4k3l03%26"
        "oauth_nonce%3Dkllo9940pd9333jh%26oauth_signature_method%3DHMAC-SHA1%26"
        "oauth_timestamp%3D1191242096%26oauth_token%3Dnnch734d00sl2jdk%26"
        "oauth_version%3D1.0%26size%3Doriginal")


def test_x_signature_vecteur_rfc5849():
    base = ("GET&http%3A%2F%2Fphotos.example.net%2Fphotos&file%3Dvacation.jpg"
            "%26oauth_consumer_key%3Ddpf43f3p2l4k3l03%26oauth_nonce%3Dkllo9940pd9333jh"
            "%26oauth_signature_method%3DHMAC-SHA1%26oauth_timestamp%3D1191242096"
            "%26oauth_token%3Dnnch734d00sl2jdk%26oauth_version%3D1.0%26size%3Doriginal")
    assert xp.sign(base, "kd94hf93k423kf44", "pfkkdhi9sl3r4s00") == "tR3+Ty81lMeYAr/Fid0kMTYa/WM="


def test_x_validate():
    ok, err = xp.validate("  hello  ")
    assert (ok, err) == ("hello", "")
    assert xp.validate("")[1] == "texte vide"
    assert "trop long" in xp.validate("x" * 281)[1]
    assert xp.validate("x" * 280)[1] == ""


def test_x_account_prefix():
    assert xp.account_prefix("hub") == "X_"
    assert xp.account_prefix("Helium") == "X_HELIUM_"
    assert xp.account_prefix("") == "X_"


def test_x_build_auth_deterministe():
    creds = {"api_key": "k", "api_secret": "cs", "access_token": "t", "access_secret": "ts"}
    h1 = xp.build_auth("GET", xp.ME_URL, [], creds, nonce="n", timestamp="1")
    h2 = xp.build_auth("GET", xp.ME_URL, [], creds, nonce="n", timestamp="1")
    assert h1 == h2
    assert h1.startswith("OAuth ") and 'oauth_signature="' in h1


def test_discord_save_channel_map_fusion(tmp_path):
    f = tmp_path / "ch.json"
    f.write_text('{"investors": "https://wh/i", "channels": {"a": "https://wh/a"}}',
                 encoding="utf-8")
    added, repointed, kept = kd.save_channel_map(
        {"a": "https://wh/a2", "b": "https://wh/b", "c": "https://wh/a"}, path=f)
    assert added == ["b", "c"] and repointed == ["a"] and kept == []
    import json
    data = json.loads(f.read_text(encoding="utf-8"))
    assert data["investors"] == "https://wh/i"
    assert data["channels"] == {"a": "https://wh/a2", "b": "https://wh/b", "c": "https://wh/a"}


def test_discord_channel_name_map_prioritaire():
    assert kd.channel_name("Helium", {"channels": {"Helium": "#helium"}}) == "helium"
    assert kd.channel_name("Helium", {}) == "proj-helium"
    assert kd.category_name("S", 1, {"categories": {"S": "Ma Cat"}}) == "Ma Cat"


def test_discord_auto_adopt_exact_et_ambigu():
    guild = [{"name": "helium", "type": 0}, {"name": "helium-dev", "type": 0},
             {"name": "λ-7 Helium Chain", "type": 4}]
    projs = [{"name": "Helium", "pct": 1, "status": "Actif", "desc": "",
              "external_section": False, "section": "S7"}]
    adopted, ambiguous, catmap = kd.auto_adopt(projs, guild)
    assert adopted == {"Helium": "#helium"}
    assert ambiguous == []


def test_discord_ensure_webhooks_reutilise(monkeypatch):
    calls = []

    def fake_api(method, path, token, payload=None):
        calls.append((method, path))
        if path.endswith("/webhooks") and method == "GET":
            return 200, [{"name": "Kuro", "url": "https://wh/existant"}]
        return 500, {}
    monkeypatch.setattr(kd, "api_call", fake_api)
    out = kd.ensure_webhooks("tok", {"proj-helium": ("123", "helium")}, dry=False)
    assert out == {"helium": "https://wh/existant"}
    assert not any(m == "POST" for m, _ in calls)


def test_discord_ensure_webhooks_403_stop(monkeypatch):
    monkeypatch.setattr(kd, "api_call", lambda *a, **k: (403, {"error": "x"}))
    out = kd.ensure_webhooks("tok", {"proj-a": ("1", "a")}, dry=False)
    assert out == {}


def test_kit_subscribe_ok(monkeypatch):
    import kit_post as kp
    import urllib.request
    monkeypatch.setenv("KIT_API_SECRET", "s")
    monkeypatch.setattr(urllib.request, "urlopen",
                        _fake_urlopen_factory({"subscription": {"id": "s1", "email_address": "a@b.cd"}}))
    res = kp.subscribe("a@b.cd", "A", ["prospect"])
    assert res["id"] == "s1"
    try:
        kp.subscribe("pas-un-email", "", [])
    except kp.KitError:
        pass
    else:
        raise AssertionError("KitError attendue")


def test_kit_broadcast_create_et_send(monkeypatch):
    import kit_post as kp
    import urllib.request
    monkeypatch.setenv("KIT_API_SECRET", "s")
    monkeypatch.setattr(urllib.request, "urlopen",
                        _fake_urlopen_factory({"broadcast": {"id": "b1"}}))
    res = kp.create_broadcast("Sujet", "<p>html</p>")
    assert res["id"] == "b1"
    monkeypatch.setattr(urllib.request, "urlopen",
                        _fake_urlopen_factory({"sent": True}))
    assert kp.send_broadcast("b1")["http"] == 200
    try:
        kp.create_broadcast("  ", "<p>x</p>")
    except kp.KitError:
        pass
    else:
        raise AssertionError("KitError attendue")


def test_kit_http_error_claire(monkeypatch):
    import kit_post as kp
    import urllib.request
    import urllib.error
    import io

    def _boom(req, timeout=30):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized",
                                     {}, io.BytesIO(b'{"message":"bad key"}'))
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    monkeypatch.setenv("KIT_API_SECRET", "bad")
    try:
        kp.check_key()
    except kp.KitError as exc:
        assert "401" in str(exc)
        return
    raise AssertionError("KitError attendue")


def test_kit_sync_md_et_sujets(tmp_path):
    import kit_sync as ks
    assert ks.subject_of("# Titre X\ncorps", "fb") == "Titre X"
    assert ks.subject_of("sans titre", "fb") == "fb"
    html = ks.md_to_html("# T\n**gras** et texte\n- item\n> citation")
    assert "<h1>T</h1>" in html and "<strong>gras</strong>" in html
    assert "•" not in html or "item" in html
    (tmp_path / "issue-99-x.md").write_text("# Coucou\nCorps", encoding="utf-8")
    (tmp_path / ".kit_ids.json").write_text('{"issue-99-x.md": "123"}', encoding="utf-8")
    assert ks.main(["--dir", str(tmp_path)]) == 0


def test_kit_sync_send_next(monkeypatch, tmp_path):
    import sys
    import types
    import json
    import kit_sync as ks
    (tmp_path / "issue-01-a.md").write_text("# A\nx", encoding="utf-8")
    (tmp_path / ".kit_ids.json").write_text('{"issue-01-a.md": "b1"}', encoding="utf-8")
    fake = types.ModuleType("kit_post")
    sent = []
    fake.send_broadcast = lambda bid: sent.append(bid) or {"http": 200}
    monkeypatch.setitem(sys.modules, "kit_post", fake)
    assert ks.main(["--dir", str(tmp_path), "--send-next"]) == 0  # dry : rien
    assert sent == []
    assert ks.main(["--dir", str(tmp_path), "--send-next", "--apply"]) == 0
    assert sent == ["b1"]
    state = json.loads((tmp_path / ".kit_ids.json").read_text(encoding="utf-8"))
    assert state["_sent"] == ["b1"]
    assert ks.main(["--dir", str(tmp_path), "--send-next", "--apply"]) == 0  # plus rien
    assert sent == ["b1"]


class _FakeResp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        import json
        return json.dumps(self._payload).encode()


def _fake_urlopen_factory(payload):
    def _fake(req, timeout=30):
        return _FakeResp(payload)
    return _fake


def test_buffer_create_post_ok(monkeypatch):
    import buffer_post as bp
    import urllib.request
    payload = {"data": {"createPost": {"post": {"id": "p1", "text": "hi", "dueAt": "d"}}}}
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen_factory(payload))
    res = bp.create_post("hi", "ch1", "key")
    assert res["id"] == "p1" and res["queued"] is True


def test_buffer_mutation_error_queue(monkeypatch):
    import buffer_post as bp
    import urllib.request
    payload = {"data": {"createPost": {"message": "Queue limit reached"}}}
    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen_factory(payload))
    try:
        bp.create_post("hi", "ch1", "key")
    except bp.BufferError as exc:
        assert "Queue" in str(exc)
        return
    raise AssertionError("BufferError attendue")


def test_buffer_list_channels(monkeypatch):
    import buffer_post as bp
    import urllib.request
    calls = []

    def _fake(req, timeout=30):
        body = req.data.decode()
        calls.append(body)
        if "GetOrganizations" in body:
            return _FakeResp({"data": {"account": {"organizations": [{"id": "o1", "name": "Org"}]}}})
        return _FakeResp({"data": {"channels": [{"id": "c1", "name": "X hub", "service": "twitter"},
                                                {"name": "sans-id"}]}})
    monkeypatch.setattr(urllib.request, "urlopen", _fake)
    assert bp.list_channels("key") == [{"id": "c1", "name": "X hub", "service": "twitter", "org": "Org"}]
    assert len(calls) == 2


def test_buffer_validate_long_et_vide():
    import buffer_post as bp
    try:
        bp.create_post("", "c", "k")
    except bp.BufferError as exc:
        assert "vide" in str(exc)
    else:
        raise AssertionError("BufferError attendue")
    try:
        bp.create_post("x" * 281, "c", "k")
    except bp.BufferError as exc:
        assert "trop long" in str(exc)
    else:
        raise AssertionError("BufferError attendue")
    # URL compte 23 (t.co) : 260 + 45 URL = 283 brut mais 260+23 accepté si mocké.
    import urllib.request
    seen = {}

    class _Cap:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            import json as _j
            return _j.dumps({"data": {"createPost": {"post": {"id": "p9"}}}}).encode()
    monkeypatch_urlopen = _Cap
    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=30: monkeypatch_urlopen()
    try:
        res = bp.create_post("y" * 250 + " https://github.com/a/b", "c", "k")
    finally:
        urllib.request.urlopen = orig
    assert res["id"] == "p9"

def test_buffer_create_thread(monkeypatch):
    import buffer_post as bp
    import urllib.request
    seen = {}

    class _Cap(_FakeResp):
        def __init__(self, payload):
            self._payload = payload
            self.status = 200

    def _fake(req, timeout=30):
        seen["body"] = req.data.decode()
        return _Cap({"data": {"createPost": {"post": {"id": "t1"}}}})
    monkeypatch.setattr(urllib.request, "urlopen", _fake)
    res = bp.create_thread("Post nu ici", "Code ici : https://github.com/a/b",
                           "c", "k", mode="customScheduled", due_at="2026-01-01T20:00:00.000Z")
    assert res["id"] == "t1"
    assert "thread" in seen["body"] and "customScheduled" in seen["body"]
    try:
        bp.create_thread("", "x", "c", "k")
    except bp.BufferError:
        pass
    else:
        raise AssertionError("BufferError attendue")
