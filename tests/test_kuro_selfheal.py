"""Tests self-healing Kuro — logique pure, sans reseau ni process reel."""


import kuro_autodebug as AD  # noqa: N812 - alias courts, convention de ce module
import kuro_doctor as DOC  # noqa: N812 - alias courts, convention de ce module
import kuro_supervisor as SUP  # noqa: N812 - alias courts, convention de ce module

# ---------- superviseur : decide ----------

def test_decide_healthy():
    assert SUP.decide(4.0, [])[0] == "healthy"


def test_decide_no_db():
    assert SUP.decide(None, [])[0] == "no_db"


def test_decide_restart_quand_stale():
    assert SUP.decide(60.0, [])[0] == "restart"


def test_decide_cooldown_apres_restart_recent():
    h = [{"action": "restart",
          "ts": SUP.now_utc().isoformat(timespec="seconds")}]
    assert SUP.decide(60.0, h)[0] == "cooldown"


def test_decide_escalate_apres_trop_de_restarts():
    today = SUP.now_utc().date().isoformat()
    h = [{"action": "restart", "ts": f"{today}T00:0{i}:00+00:00"}
         for i in range(SUP.MAX_RESTARTS_PER_DAY)]
    assert SUP.decide(60.0, h)[0] == "escalate"


def test_restarts_today_ne_compte_que_aujourdhui():
    h = [{"action": "restart", "ts": "2000-01-01T00:00:00+00:00"},
         {"action": "restart",
          "ts": SUP.now_utc().isoformat(timespec="seconds")}]
    assert SUP.restarts_today(h) == 1


# ---------- doctor : persistance + recidive ----------

def test_persist_verdict_detecte_recidive(tmp_path, monkeypatch):
    hist = tmp_path / "doctor_history.jsonl"
    monkeypatch.setattr(DOC, "DOCTOR_HISTORY", hist)
    for _ in range(DOC.RECURRENCE_WINDOW - 1):
        assert DOC.persist_verdict_and_find_recurring(["API locale 8767"]) == []
    rec = DOC.persist_verdict_and_find_recurring(["API locale 8767"])
    assert rec == ["API locale 8767"]
    assert hist.exists()


def test_persist_verdict_pas_de_recidive_si_resolu(tmp_path, monkeypatch):
    hist = tmp_path / "doctor_history.jsonl"
    monkeypatch.setattr(DOC, "DOCTOR_HISTORY", hist)
    DOC.persist_verdict_and_find_recurring(["API locale 8767"])
    DOC.persist_verdict_and_find_recurring(["API locale 8767"])
    assert DOC.persist_verdict_and_find_recurring([]) == []


# ---------- autodebug : sanitize ----------

def test_sanitize_redige_cles_et_montants():
    sale = "key=sk-abcdefgh123456 et $1,250.00 puis token: mpg-xyz987654"
    propre = AD.sanitize(sale)
    assert "sk-abcdefgh123456" not in propre
    assert "1,250" not in propre
    assert "mpg-xyz987654" not in propre
    assert AD.sanitize(propre) == propre  # idempotent


def test_sanitize_texte_sain_inchange():
    txt = "heartbeat il y a 4 min, 63 projets, tests verts"
    assert AD.sanitize(txt) == txt


# ---------- autodebug : chemins ----------

def test_allowed_scripts_ok(tmp_path, monkeypatch):
    f = tmp_path / "scripts" / "x.py"
    f.parent.mkdir(parents=True)
    f.write_text("a", encoding="utf-8")
    monkeypatch.setattr(AD, "KURO_ROOT", tmp_path)
    assert AD.is_allowed_path("scripts/x.py")[0] is True


def test_bloque_local_json_et_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(AD, "KURO_ROOT", tmp_path)
    assert AD.is_allowed_path("finances.local.json")[0] is False
    assert AD.is_allowed_path("../kuro/daemon.py")[0] is False
    assert AD.is_allowed_path("SESSION_SUMMARY.md")[0] is False
    assert AD.is_allowed_path("scripts/.env")[0] is False


# ---------- autodebug : diff ----------

SAMPLE_DIFF = """--- a/scripts/demo.py
+++ b/scripts/demo.py
@@ -1,3 +1,3 @@
 line1
-old
+new
 line3
"""


def test_extract_diff_et_cibles():
    reply = "CAUSE: x\nPATCH:\n```diff\n" + SAMPLE_DIFF + "```"
    d = AD.extract_diff(reply)
    assert d is not None and "new" in d
    assert AD.diff_targets(d) == ["scripts/demo.py"]


def test_extract_diff_aucun():
    assert AD.extract_diff("PATCH: AUCUN, L1 suffit") is None


def test_apply_unified_ok_et_mismatch():
    ok, out = AD.apply_unified_to_text("line1\nold\nline3\n", SAMPLE_DIFF,
                                       "scripts/demo.py")
    assert ok and "new" in out and "old" not in out.splitlines()
    bad = SAMPLE_DIFF.replace(" line1", " CHANGED")
    ok2, _ = AD.apply_unified_to_text("line1\nold\nline3\n", bad,
                                      "scripts/demo.py")
    assert ok2 is False


def test_rollback_restaure(tmp_path, monkeypatch):
    f = tmp_path / "scripts" / "r.py"
    f.parent.mkdir(parents=True)
    f.write_text("v1", encoding="utf-8")
    monkeypatch.setattr(AD, "KURO_ROOT", tmp_path)
    monkeypatch.setattr(AD, "BACKUP_DIR", tmp_path / "bk")
    f.write_text("v2", encoding="utf-8")
    AD.rollback({"scripts/r.py": "v1"})
    assert f.read_text(encoding="utf-8") == "v1"


# ---------- autodebug : diagnose sans cerveau ----------

def test_diagnose_sans_cerveau_deterministe(monkeypatch):
    monkeypatch.setattr(AD, "load_recent_fails", lambda limit=3: ["X"])
    monkeypatch.setattr(AD, "collect_log_tails", lambda: {})
    rc, out = AD.diagnose(ask_fn=lambda *a, **k: None)
    assert rc == 3 and "deterministe" in out
