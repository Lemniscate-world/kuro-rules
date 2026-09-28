#!/usr/bin/env python3
"""post_policy.py — Decide QUOI poster sur QUEL compte X, sans humain (R94-v2 full-auto).

Politique :
  PRINCIPAL (hub, ex: LambdaSection) : 1 post/jour max = top velocite du jour.
  ANNEXE (ex: Helium) : uniquement si le projet depasse ANNEX_MIN_SCORE,
    cooldown COOLDOWN_H respecte, et commit jamais poste sur ce compte.
  Securite : memes gates que gen_x_posts (OWNED, statut, fraicheur, sanitize),
    + dedupe par hash de commit (outputs/x_posted.json) : jamais 2x le meme.

Comptes : hub = cles X_* ; annexe <slug> = cles X_<SLUG>_*
  (ex: X_HELIUM_API_KEY). Sans cles : le compte est propose en DRY, saute en apply.

Etat : outputs/x_posted.json {"hub": [{"hash","date","id","projet"}], ...}
+ outputs/x_posts_log.md (ligne par post, tracabilite R99).

Zero dependance, cross-platform (R93). Sans cles ni reseau : plan seul, exit 0.

Usage :
  python scripts/post_policy.py --dry-run [--top 3]
  python scripts/post_policy.py --apply [--hub helium] [--min-score 15] [--cooldown-h 48]
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
EPINGLE = KURORULES / "Epingle_Projets.md"
OUTPUTS = KURORULES / "outputs"
STATE_FILE = OUTPUTS / "x_posted.json"
POSTS_LOG = OUTPUTS / "x_posts_log.md"

ANNEX_MIN_SCORE = 15
COOLDOWN_H = 48
HUB_MAX_PER_DAY = 1

# Langue par compte : hub LambdaSection en anglais (audience tech), annexes en français.
ACCOUNT_LANG = {"hub": "en"}


def account_lang(account):
    return ACCOUNT_LANG.get((account or "hub").lower(), "fr")


def x_posting_enabled():
    """Plan X payant requis pour poster (le Free repond 402 credits-depleted).
    X_PLAN=basic|pro|paid -> poste ; toute autre valeur (defaut free) -> drafts seuls."""
    return os.environ.get("X_PLAN", "free").strip().lower() in ("basic", "pro", "paid")


def now_utc():
    return datetime.now(timezone.utc)


def load_state(path=STATE_FILE):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_state(state, path=STATE_FILE):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(state, indent=1, ensure_ascii=False),
                          encoding="utf-8")


def posted_hashes(state, account):
    return set(e.get("hash", "") for e in state.get(account, []) if e.get("hash"))


def last_post_time(state, account):
    latest = None
    for e in state.get(account, []):
        try:
            dt = datetime.fromisoformat(e.get("date", ""))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            if latest is None or dt > latest:
                latest = dt
        except Exception:
            continue
    return latest


def creds_prefix(account):
    return "X_" if account == "hub" else "X_%s_" % account.upper().replace("-", "_")


def has_creds(account):
    p = creds_prefix(account)
    return bool(os.environ.get(p + "API_KEY") and os.environ.get(p + "API_SECRET")
                and os.environ.get(p + "ACCESS_TOKEN") and os.environ.get(p + "ACCESS_SECRET"))


def buffer_channel_for(account):
    if (account or "hub").lower() == "hub":
        return os.environ.get("BUFFER_CHANNEL_HUB", "")
    return os.environ.get("BUFFER_CHANNEL_" + account.upper().replace("-", "_"), "")


def publish_via_buffer(text, account, lang="fr"):
    """Poste via Buffer avec heure fixee par Kuro. Si le texte porte un lien,
    thread auto : post nu + reply avec le lien (pas de penalite reach).
    Retourne l'id ou leve BufferError."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import buffer_post as bp
    import gen_x_posts as _gx
    api_key = os.environ.get("BUFFER_API_KEY", "")
    if not api_key:
        raise bp.BufferError("BUFFER_API_KEY absent")
    channel = buffer_channel_for(account)
    if not channel:
        raise bp.BufferError("canal Buffer non configure (BUFFER_CHANNEL_%s)" % account.upper())
    urls = _gx.URL_RE.findall(text or "")
    if urls and (lang or "fr").lower() == "en":
        reply = "Code & details here: %s" % urls[0]
    elif urls:
        reply = "Code et détails ici : %s" % urls[0]
    else:
        reply = ""
    if reply:
        main = _gx.URL_RE.sub("", text or "").strip()
        main = re.sub(r"\n{3,}", "\n\n", main).strip()
        return bp.create_thread(main, reply, channel, api_key,
                                mode="customScheduled", due_at=bp.next_slot_utc())["id"]
    return bp.create_post(text, channel, api_key,
                           mode="customScheduled", due_at=bp.next_slot_utc())["id"]


def numbers_and_links(text):
    """Tokens factuels inviolables : nombres + URLs (anti-hallucination)."""
    import re as _re
    nums = set(_re.findall(r"\d+(?:[.,]\d+)?", text or ""))
    urls = set(_re.findall(r"https?://\S+", text or ""))
    return nums | urls


def maybe_rewrite(project, text, themes=(), lang="fr"):
    """Rewrite LLM auto si STRICTEMENT meilleur et sûr. Sinon texte d'origine.
    Retourne (texte, True/False). Ne leve jamais."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import post_brain as _brain
        import gen_x_posts as _gx
        rep = _brain.review_draft(project, text, themes, lang=lang)
        new = (rep.get("rewrite") or "").strip()
        if not new or rep.get("score_llm") is None:
            return text, False
        if _gx.x_len(new) > 280 or _gx.lint_post(project, new):
            return text, False
        det0, _ = _brain.deterministic_score(project, text, themes, lang=lang)
        det1, _ = _brain.deterministic_score(project, new, themes, lang=lang)
        if det1 < det0:
            return text, False
        if not numbers_and_links(text) <= numbers_and_links(new):
            return text, False  # chiffre ou lien perdu/halluciné
        return new, True
    except Exception:
        return text, False


def discord_notify(project, long_path):
    """Poste la version longue dans le salon Discord du projet. True si poste."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import kuro_discord as kd
        body = Path(long_path).read_text(encoding="utf-8").strip()
        if not body:
            return False
        url = kd.webhook_for(project, kd.load_channel_map())
        if not url:
            return False
        kd.post_webhook(url, "Update %s" % project, body)
        return True
    except Exception:
        return False


def decide(projs_selected, state, hub="hub", annex_accounts=(),
           min_score=ANNEX_MIN_SCORE, cooldown_h=COOLDOWN_H, today=None):
    """Logique pure et testable. Retourne (plan, raisons).
    plan = [{"account","project","entry","reason"}]."""
    today = today or now_utc().date().isoformat()
    plan, raisons = [], []
    hub_done_today = sum(1 for e in state.get(hub, [])
                         if str(e.get("date", ""))[:10] == today)
    picked_hub = None
    for r in projs_selected:
        name = r["project"]["name"]
        slug = name.lower().replace(" ", "-")
        h = r["facts"].get("hash", "")
        worthy = bool(r["facts"].get("themes"))
        # Hub : top eligible non poste avec un vrai sujet, 1/jour
        if picked_hub is None and hub_done_today < HUB_MAX_PER_DAY:
            if h and h not in posted_hashes(state, hub) and worthy:
                picked_hub = r
                plan.append({"account": hub, "project": name, "entry": r,
                             "reason": "top-velocite hub"})
            else:
                raisons.append((name, "hub-deja-poste" if h in posted_hashes(state, hub)
                                else "hub-rien-de-publiable"))
        # Annexes : compte configure pour ce projet ?
        if slug in [a.lower() for a in annex_accounts]:
            if r["score"] < min_score:
                raisons.append((name, "annexe-score-%d<%d" % (r["score"], min_score)))
                continue
            if not worthy:
                raisons.append((name, "annexe-rien-de-publiable"))
                continue
            if h in posted_hashes(state, slug):
                raisons.append((name, "annexe-deja-poste"))
                continue
            last = last_post_time(state, slug)
            if last is not None and now_utc() - last < timedelta(hours=cooldown_h):
                raisons.append((name, "annexe-cooldown"))
                continue
            plan.append({"account": slug, "project": name, "entry": r,
                         "reason": "annexe score=%d" % r["score"]})
    return plan, raisons


def record_post(state, account, project, commit_hash, tweet_id=""):
    state.setdefault(account, []).append({
        "date": now_utc().isoformat(timespec="seconds"),
        "projet": project, "hash": commit_hash, "id": tweet_id})
    return state


def append_posts_log(account, project, text, tweet_id="", path=POSTS_LOG):
    line = "| %s | %s | %s | %.60s | %s |\n" % (
        now_utc().date().isoformat(), account, project,
        (text or "").replace("\n", " ").replace("|", "/"), tweet_id)
    p = Path(path)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("| date | compte | projet | texte | id |\n|---|---|---|---|---|\n",
                     encoding="utf-8")
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(line)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Politique full-auto principal vs annexes (R94-v2)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--hub", default="hub")
    ap.add_argument("--annex", action="append", default=[],
                    help="Projet avec compte annexe (repetable, ex: --annex Helium).")
    ap.add_argument("--min-score", type=int, default=ANNEX_MIN_SCORE)
    ap.add_argument("--cooldown-h", type=int, default=COOLDOWN_H)
    ap.add_argument("--discord", action="store_true",
                    help="Poste aussi la version longue dans le salon Discord du projet (webhooks, gratuit).")
    ap.add_argument("--via", choices=["x", "buffer"], default=os.environ.get("X_VIA", "x"),
                    help="Canal de publication X : direct API (payant) ou Buffer gratuit.")
    ap.add_argument("--no-rewrite", action="store_true",
                    help="Desactive la reecriture LLM (draft deterministe seul).")
    ap.add_argument("--epingle", default=str(EPINGLE))
    ap.add_argument("--docs", default=str(DOCS))
    ap.add_argument("--outputs", default=str(OUTPUTS))
    args = ap.parse_args(argv)
    dry = not args.apply

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        import gen_x_posts as gx
        import x_post as xp
    except Exception as exc:
        print("[ERR] imports: %s" % exc)
        return 2
    try:
        projs = gx.load_projects(args.epingle)
    except RuntimeError as exc:
        print("[ERR] %s" % exc)
        return 2
    selected, skipped = gx.select_top(projs, max(1, args.top or 5), docs_dir=args.docs)
    if args.annex:
        # Les annexes sont toujours evaluees, meme hors top-N.
        forced, skipped_only = gx.select_only(projs, args.annex, docs_dir=args.docs)
        have = set(r["project"]["name"].lower() for r in selected)
        for r in forced:
            if r["project"]["name"].lower() not in have:
                selected.append(r)
        skipped.extend(skipped_only)
        selected.sort(key=lambda r: (r["score"], r["facts"]["c7"]), reverse=True)
    state = load_state()
    plan, raisons = decide(selected, state, hub=args.hub, annex_accounts=args.annex,
                           min_score=args.min_score, cooldown_h=args.cooldown_h)

    print("=== post_policy (hub=%s, annexes=%s, via=%s) ===" % (
        args.hub, args.annex or "aucune", args.via))
    for item in plan:
        r = item["entry"]
        if args.via == "buffer":
            ready = bool(os.environ.get("BUFFER_API_KEY") and buffer_channel_for(item["account"]))
        else:
            ready = has_creds(item["account"])
        tag = "OK-cles" if ready else "SANS-CLES"
        print(gx.ascii_log("  [PLAN] @%-10s %-16s score=%d %s (%s) [%s]" % (
            item["account"], item["project"], r["score"],
            r["facts"].get("hash", ""), item["reason"], tag)))
    for name, reason in raisons:
        print(gx.ascii_log("  [SKIP] %-16s %s" % (name, reason)))
    if dry:
        print("  [DRY] rien poste. --apply pour executer (cles requises par compte).")
        return 0

    ok, ko = 0, 0
    need_x_credits = (args.via == "x")
    can_post = (not need_x_credits) or x_posting_enabled()
    if need_x_credits and not can_post:
        print("  [SKIP] X_PLAN=%s : pas de credits API -> drafts + Discord seuls (voir R94-v2)."
              % os.environ.get("X_PLAN", "free"))
    # Batches par langue (hub EN, annexes FR) : le menage stale ne doit pas
    # effacer les picks d'une autre langue. Discord recoit les tops actifs FR.
    by_lang = {}
    for it in plan:
        by_lang.setdefault(account_lang(it["account"]), []).append(it["entry"])
    fr_extra = []
    if args.discord:
        in_plan = set(it["project"] for it in plan)
        for r in selected:
            if r["project"]["name"] not in in_plan:
                fr_extra.append(r)
    batch = []
    by_project = {}
    hub_projects = set(it["project"] for it in plan if it["account"] == args.hub)
    for lang, entries in [("en", by_lang.get("en", [])), ("fr", by_lang.get("fr", []) + fr_extra)]:
        if not entries:
            continue
        for proj_name, ppath, ptext in gx.write_drafts(
                entries, Path(args.outputs),
                write_hub=any(e["project"]["name"] in hub_projects for e in entries)):
            if proj_name == "HUB":
                by_project["HUB:" + lang] = (ppath, ptext)
            elif proj_name not in by_project:
                by_project[proj_name] = (ppath, ptext)
    if args.discord:
        for proj_name in sorted(by_project):
            last = None
            for e in state.get("discord", []):
                if e.get("projet") == proj_name:
                    try:
                        dt = datetime.fromisoformat(e.get("date", ""))
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if last is None or dt > last:
                            last = dt
                    except Exception:
                        continue
            if last is not None and now_utc() - last < timedelta(hours=args.cooldown_h):
                print("  [SKIP] discord #%s : cooldown." % proj_name)
                continue
            ppath = by_project[proj_name][0]
            long_path = str(Path(ppath).with_name(
                Path(ppath).stem.replace("x_post_", "x_long_", 1) + ".md"))
            if Path(long_path).exists() and discord_notify(proj_name, long_path):
                print(gx.ascii_log("  [OK] discord #%s" % proj_name))
                record_post(state, "discord", proj_name, "")
            else:
                print("  [SKIP] discord #%s : pas de webhook." % proj_name)
    for item in plan:
        slug = item["account"]
        r = item["entry"]
        path, text = by_project.get(item["project"], ("", ""))
        if not path:
            print("  [SKIP] @%s %s : draft bloque au lint, rien a poster." % (slug, item["project"]))
            continue
        if not can_post:
            print("  [SKIP] @%s %s : plan X free, pas de post X." % (slug, item["project"]))
            continue
        if not has_creds(slug):
            print("  [SKIP] @%s sans cles %s* — draft seul." % (slug, creds_prefix(slug)))
            continue
        if not text:
            print("  [ERR] draft vide pour %s" % item["project"])
            ko += 1
            continue
        leaks = gx.lint_post(item["project"], text)
        if leaks:
            print("  [LINT-BLOCK] @%s %s : termes sensibles %s — post refuse."
                  % (slug, item["project"], leaks))
            ko += 1
            continue
        if not args.no_rewrite:
            new_text, rewritten = maybe_rewrite(
                item["project"], text, r["facts"].get("themes", []),
                lang=account_lang(slug))
            if rewritten:
                text = new_text
                print(gx.ascii_log("  [BRAIN-REWRITE] @%s version LLM garde-fous OK" % slug))
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from post_brain import deterministic_score as _score, append_history as _hist
            det, det_issues = _score(item["project"], text, r["facts"].get("themes", []),
                                     lang=account_lang(slug))
            print("  [BRAIN] @%s score %d/100%s" % (
                slug, det, (" (" + "; ".join(det_issues[:2]) + ")") if det_issues else ""))
            _hist({"date": now_utc().date().isoformat(), "projet": item["project"],
                   "score_det": det, "issues": det_issues, "score_llm": None,
                   "rewrite": None, "score": det})
        except Exception as exc:
            print("  [WARN] brain indisponible: %s" % str(exc)[:100])
        if args.via == "buffer":
            try:
                tid = publish_via_buffer(text, slug, lang=account_lang(slug))
                record_post(state, slug, item["project"], r["facts"].get("hash", ""), tid)
                append_posts_log(slug, item["project"], text, tid)
                print(gx.ascii_log("  [OK] buffer @%s %s id=%s" % (slug, item["project"], tid)))
                ok += 1
            except Exception as exc:
                print("  [ERR] buffer @%s %s: %s" % (slug, item["project"], str(exc)[:200]))
                ko += 1
            continue
        if not has_creds(slug):
            print("  [SKIP] @%s sans cles %s* — draft seul." % (slug, creds_prefix(slug)))
            continue
        creds = {"api_key": os.environ[creds_prefix(slug) + "API_KEY"],
                 "api_secret": os.environ[creds_prefix(slug) + "API_SECRET"],
                 "access_token": os.environ[creds_prefix(slug) + "ACCESS_TOKEN"],
                 "access_secret": os.environ[creds_prefix(slug) + "ACCESS_SECRET"]}
        try:
            status, data = xp.post_tweet(text, creds)
            tid = (data.get("data") or {}).get("id", "")
            record_post(state, slug, item["project"], r["facts"].get("hash", ""), tid)
            append_posts_log(slug, item["project"], text, tid)
            print(gx.ascii_log("  [OK] @%s %s HTTP %s id=%s" % (
                slug, item["project"], status, tid)))
            ok += 1
        except Exception as exc:
            detail = str(exc)[:200]
            try:
                import urllib.error as _ue
                if isinstance(exc, _ue.HTTPError):
                    detail = "HTTP %s %s" % (exc.code, exc.read().decode("utf-8", errors="replace")[:300])
            except Exception:
                pass
            print("  [ERR] @%s %s: %s" % (slug, item["project"], detail))
            ko += 1
    save_state(state)
    print("  [OK] postes=%d echecs=%d. R99 : reporter dans acquisition_tracker.md." % (ok, ko))
    return 0 if ko == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
