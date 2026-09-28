#!/usr/bin/env python3
"""kuro_discord.py — Le Discord suit Epingle, pas l'inverse (R80/R83).

Commandes :
  plan   : affiche categories + salons proposes depuis Epingle (zero reseau).
  sync   : cree categories/salons manquants + corrige noms/topics (Bot requis).
  post   : publie un message dans le salon d'un projet (webhook par salon).

Auth :
  sync -> DISCORD_BOT_TOKEN + DISCORD_GUILD_ID (gerer les salons = Bot,
          un webhook seul ne peut que poster).
  post -> kuro_discord_channels.local.json {"channels": {"helium": "https://..."}}
          sinon repli sur DISCORD_WEBHOOK_URL.

Convention de nommage (idempotent, ASCII) :
  categorie : "SEC 01 - AI" (theme Epingle, sans accents pour la stabilite)
  salon     : "proj-helium" (un par projet Actif/Validation + "hub-kuro")

Zero dependance, cross-platform (R93). Sans token : plan/post-degrades, exit 0.
Jamais de secret en log.

Usage :
  python scripts/kuro_discord.py plan [--epingle ...]
  python scripts/kuro_discord.py sync [--guild ID] [--apply]
  python scripts/kuro_discord.py post --project Helium --message-file outputs/x_post_2026-09-21-helium.md
"""
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.request
import urllib.error
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
EPINGLE = KURORULES / "Epingle_Projets.md"
CHANNELS_FILE = KURORULES / "kuro_discord_channels.local.json"
STRUCT_MAP_FILE = KURORULES / "kuro_discord_map.local.json"

API = "https://discord.com/api/v10"
TRACKED_STATUS = ("actif", "validation")


def ascii_console(text):
    out = []
    for c in text or "":
        o = ord(c)
        if 0xD800 <= o <= 0xDFFF or o > 0xFFFF:
            continue
        out.append(c)
    return "".join(out)


def slug(text):
    """translitere + slugifie pour noms de salons Discord (minuscules, tirets)."""
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t or "divers"


def channel_name(project, struct_map=None):
    """Nom du salon : map adoptee d'abord (structure existante de l'utilisateur),
    sinon convention proj-<slug>."""
    if struct_map:
        hit = (struct_map.get("channels", {}) or {}).get(project)
        if hit:
            return hit.lstrip("#")
    return "proj-%s" % slug(project)[:90]


def category_name(section_raw, fallback_num, struct_map=None):
    """Nom de categorie : map adoptee d'abord, sinon 'SEC NN - Theme'."""
    if struct_map:
        hit = (struct_map.get("categories", {}) or {}).get(section_raw or "")
        if hit:
            return hit
    raw = html.unescape(section_raw or "")
    m = re.search(r"section-(\d+)", raw.lower())
    num = m.group(1).zfill(2) if m else "%02d" % fallback_num
    if "laboratoire" in raw.lower():
        return "SEC LAB - Laboratoire"
    theme_parts = re.split(r"[—–]", raw)
    theme = theme_parts[-1].strip() if len(theme_parts) > 1 else re.sub(
        r"(?i)^\s*λ?\s*-?\s*section-?\d*\s*-?\s*", "", raw).strip()
    theme = unicodedata.normalize("NFKD", theme).encode("ascii", "ignore").decode("ascii")
    theme = re.sub(r"\s+", " ", theme).strip()[:40] or "Divers"
    return "SEC %s - %s" % (num, theme)


def load_projects(epingle_path):
    """Reutilise le loader gen_x_posts (parser unique + supplement Laboratoire)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from gen_x_posts import load_projects as _load
    return _load(Path(epingle_path))


def load_struct_map(path=None):
    """Map d'adoption {channels: {Projet: '#salon'}, categories: {SectionEpingle: 'Cat'}}."""
    try:
        data = json.loads(Path(path or STRUCT_MAP_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def build_plan(projects, struct_map=None):
    """Plan desire : [(categorie, [(salon, topic, projet), ...])].
    Uniquement Actif/Validation NON-externes (R87/R105 : les Externes Demeter
    n'ont pas de salon auto). struct_map = structure existante adoptee."""
    struct_map = struct_map or {}
    cats = {}
    order = []
    for i, p in enumerate(projects or []):
        if p.get("external_section"):
            continue
        if (p.get("status") or "").lower() not in TRACKED_STATUS:
            continue
        cat = category_name(p.get("section", ""), len(order), struct_map)
        if cat not in cats:
            cats[cat] = []
            order.append(cat)
        topic = ("%d%% %s — %s" % (p.get("pct", 0), p.get("status"), p.get("desc")))[:1024]
        cats[cat].append((channel_name(p["name"], struct_map), topic, p["name"]))
    return [(c, cats[c]) for c in order]


def auto_adopt(projects, guild_channels):
    """Matching non-destructif : ({Projet: '#salon-existant'}, ambigus, {Section: 'Cat'}).
    Auto uniquement sur match exact de slug ; le reste va en 'ambigus' (humain)."""
    texts = [c for c in guild_channels if isinstance(c, dict) and c.get("type") == 0]
    cats = [c for c in guild_channels if isinstance(c, dict) and c.get("type") == 4]
    # Ignore notre propre structure parallele (SEC*/proj-*) : jamais adopter nos doublons.
    existing = set(c.get("name", "") for c in texts
                   if not c.get("name", "").startswith("proj-"))
    adopted, ambiguous = {}, []
    for p in projects or []:
        if p.get("external_section"):
            continue
        if (p.get("status") or "").lower() not in TRACKED_STATUS:
            continue
        s = slug(p["name"])
        if s in existing:
            adopted[p["name"]] = "#" + s
            continue
        cands = sorted(n for n in existing if s in n or n in s)
        ambiguous.append((p["name"], cands[:4]))
    catmap = {}
    existing_cats = [c.get("name", "") for c in cats
                     if not c.get("name", "").startswith("SEC ")]
    for sec in {p.get("section", "") for p in projects or []}:
        if "laboratoire" in html.unescape(sec or "").lower():
            continue  # pas de categorie labo cote serveur -> on garde SEC LAB
        theme_words = set(w for w in re.findall(r"[a-z]{4,}", html.unescape(sec or "").lower())
                          if w not in ("section", "lambda"))
        best, best_score = "", 0
        for cat in existing_cats:
            low = cat.lower()
            score = sum(1 for w in theme_words if w in low)
            if score > best_score:
                best, best_score = cat, score
        if best_score > 0:
            catmap[sec] = best
            continue
        # Repli numero (ex: Charles -> λ-14 SOUND VISUAL) : la numerotation
        # serveur peut differer d'Epingle, donc numero UNIQUEMENT sans theme.
        m = re.search(r"section-(\d+)", html.unescape(sec or "").lower())
        if m:
            num = m.group(1)
            hits = [c for c in existing_cats
                    if re.search(r"(λ-?0*%s\b|[^0-9]0*%s\b)" % (num, num), c)]
            if len(hits) == 1:
                catmap[sec] = hits[0]
    return adopted, ambiguous, catmap


# ---------- Bot API (sync) ----------

def api_call(method, path, token, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": "Bot %s" % token,
                 "Content-Type": "application/json",
                 "User-Agent": "Kuro/1.0 (lambda-Section)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        if exc.code == 429:
            try:
                wait = float(json.loads(body).get("retry_after", 1.0)) + 0.5
            except Exception:
                wait = 2.0
            time.sleep(wait)
            return api_call(method, path, token, payload)
        return exc.code, {"error": body}
    except Exception as exc:
        return 0, {"error": str(exc)[:200]}


def sync_guild(guild_id, token, plan, dry=True):
    """Idempotent : cree ce qui manque, corrige topic/nom sinon. Retourne stats."""
    status, channels = api_call("GET", "/guilds/%s/channels" % guild_id, token)
    if status != 200:
        print("[ERR] lecture salons: %s %s" % (status, channels))
        return {"error": True}
    by_name = {c.get("name", ""): c for c in channels if isinstance(c, dict)}
    cats = {c.get("name", ""): c.get("id") for c in channels
            if isinstance(c, dict) and c.get("type") == 4}
    stats = {"cat_create": 0, "chan_create": 0, "topic_fix": 0, "ok": 0}
    for cat, chans in plan:
        cat_id = cats.get(cat)
        if cat_id is None:
            if dry:
                print(ascii_console("  [DRY] categorie+ %s" % cat))
            else:
                status, created = api_call("POST", "/guilds/%s/channels" % guild_id,
                                           token, {"name": cat, "type": 4})
                if status in (200, 201):
                    cat_id = created.get("id")
                    cats[cat] = cat_id
                    stats["cat_create"] += 1
                    time.sleep(0.6)
                else:
                    print("[ERR] categorie %s: %s %s" % (cat, status, created))
                    continue
        for chan, topic, proj in chans:
            cur = by_name.get(chan)
            if cur is None:
                if dry:
                    print(ascii_console("  [DRY] salon+ #%s (%s)" % (chan, proj)))
                else:
                    status, created = api_call(
                        "POST", "/guilds/%s/channels" % guild_id, token,
                        {"name": chan, "type": 0, "parent_id": cat_id, "topic": topic})
                    if status in (200, 201):
                        stats["chan_create"] += 1
                        by_name[chan] = created
                    else:
                        print("[ERR] salon %s: %s %s" % (chan, status, created))
                    time.sleep(0.6)
            elif (cur.get("topic") or "") != topic or cur.get("parent_id") != cat_id:
                if dry:
                    print(ascii_console("  [DRY] corrige #%s (topic/parent)" % chan))
                else:
                    status, _ = api_call("PATCH", "/channels/%s" % cur.get("id"),
                                         token, {"topic": topic, "parent_id": cat_id})
                    if status == 200:
                        stats["topic_fix"] += 1
                    else:
                        print("[ERR] patch %s: %s" % (chan, status))
                    time.sleep(0.6)
            else:
                stats["ok"] += 1
    return stats


# ---------- Webhook post ----------

def collect_channel_ids(guild_id, token, wanted):
    """{nom_salon: id} frais depuis le guild. wanted = set de noms."""
    status, channels = api_call("GET", "/guilds/%s/channels" % guild_id, token)
    if status != 200:
        return {}
    return {c.get("name", ""): c.get("id") for c in channels
            if isinstance(c, dict) and c.get("name") in wanted and c.get("id")}


def audit_guild(guild_id, token, plan):
    """Lecture seule : affiche TOUT le serveur, tagge gere/non-gere/doublon potentiel."""
    status, channels = api_call("GET", "/guilds/%s/channels" % guild_id, token)
    if status != 200:
        print("[ERR] lecture salons: %s %s" % (status, channels))
        return 2
    managed = set()
    for _cat, chans in plan:
        for chan, _t, _p in chans:
            managed.add(chan)
    managed_cats = set(cat for cat, _ in plan)
    print("=== audit Discord (lecture seule) ===")
    for c in channels:
        if not isinstance(c, dict):
            continue
        name, typ = c.get("name", ""), c.get("type")
        kind = "CAT" if typ == 4 else "salon"
        if typ == 4:
            tag = "GERE" if name in managed_cats else "EXISTANT (non gere, touche a rien)"
        else:
            tag = "GERE" if name in managed else "EXISTANT (non gere, touche a rien)"
        print(ascii_console("  [%s] %-8s #%s" % (tag, kind, name)))
    print("  Regle merge : match par nom exact -> topic/parent corriges, jamais supprime.")
    return 0


def ensure_webhooks(token, chan_ids, dry=True):
    """{slug_projet: webhook_url}. Reutilise le webhook 'Kuro' existant sinon cree.
    chan_ids = {nom_salon: (id_salon, slug_projet)}. 403 -> permission Manage Webhooks."""
    out = {}
    for chan, (cid, pslug) in sorted(chan_ids.items()):
        if dry:
            print(ascii_console("  [DRY] webhook+ #%s" % chan))
            continue
        status, hooks = api_call("GET", "/channels/%s/webhooks" % cid, token)
        if status == 403:
            print("[ERR] Manage Webhooks manquant sur #%s — portail dev -> Bot -> "
                  "permissions : cocher Manage Webhooks puis reinviter le bot." % chan)
            return out
        reused = ""
        if status == 200:
            for h in hooks if isinstance(hooks, list) else []:
                if h.get("name") == "Kuro" and h.get("url"):
                    reused = h["url"]
                    break
        if reused:
            out[pslug] = reused
            continue
        status, created = api_call("POST", "/channels/%s/webhooks" % cid, token,
                                   {"name": "Kuro"})
        if status in (200, 201) and created.get("url"):
            out[pslug] = created["url"]
            print(ascii_console("  [OK] webhook #%s" % chan))
        else:
            print("[ERR] webhook #%s: %s %s" % (chan, status, created))
        time.sleep(0.6)
    return out


def save_channel_map(new_channels, path=None):
    """Fusionne : ajoute les nouveaux, repointe les URL changees. Retourne (ajoutes, repointees, gardees)."""
    path = Path(path or CHANNELS_FILE)
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    chans = dict(data.get("channels", {}) or {})
    added, repointed, kept = [], [], []
    for slug, url in (new_channels or {}).items():
        if not url:
            continue
        if chans.get(slug) == url:
            kept.append(slug)
        elif chans.get(slug):
            chans[slug] = url
            repointed.append(slug)
        else:
            chans[slug] = url
            added.append(slug)
    data["channels"] = chans
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added, repointed, kept

def load_channel_map():
    """Fusionne channels{} + default racine (compat kuro_investor_digest)."""
    try:
        data = json.loads(CHANNELS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}
    cmap = dict(data.get("channels", {}) or {})
    if data.get("default") and "default" not in cmap:
        cmap["default"] = data["default"]
    return cmap


def webhook_for(project, channel_map):
    key = slug(project or "")
    for k, url in channel_map.items():
        if slug(k) == key and url:
            return url
    if project:
        for k, url in channel_map.items():
            if url and (slug(k) in key or key in slug(k)):
                return url
    return channel_map.get("default") or os.environ.get("DISCORD_WEBHOOK_URL") or ""


def post_webhook(url, title, body):
    payload = {"username": "Kuro",
               "embeds": [{"title": title[:256], "description": body[:1900],
                           "color": 3066993}]}
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": "Kuro/1.0 (lambda-Section)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Discord suit Epingle (plan/sync/post)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--epingle", default=str(EPINGLE))
    p_sync = sub.add_parser("sync")
    p_sync.add_argument("--epingle", default=str(EPINGLE))
    p_sync.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID", ""))
    p_sync.add_argument("--apply", action="store_true")
    p_sync.add_argument("--webhooks", action="store_true",
                        help="Cree aussi 1 webhook 'Kuro' par salon et l'enregistre "
                             "dans kuro_discord_channels.local.json (requiert Manage Webhooks).")
    p_post = sub.add_parser("post")
    p_post.add_argument("--project", required=True)
    p_post.add_argument("--message", default="")
    p_post.add_argument("--message-file", default="")
    p_post.add_argument("--title", default="")
    p_ann = sub.add_parser("announce", help="Poste via Bot dans #salon puis épingle (R83).")
    p_ann.add_argument("--channel", required=True, help="Nom du salon sans # (ex: sybil)")
    p_ann.add_argument("--message", default="")
    p_ann.add_argument("--message-file", default="")
    p_ann.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID", ""))
    p_ann.add_argument("--no-pin", action="store_true", help="Poste sans épingler")
    sub.add_parser("audit").add_argument("--epingle", default=str(EPINGLE))
    p_adopt = sub.add_parser("adopt")
    p_adopt.add_argument("--epingle", default=str(EPINGLE))
    p_adopt.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID", ""))
    p_adopt.add_argument("--apply", action="store_true",
                         help="Ecrit kuro_discord_map.local.json (ambigus exclus, a trancher a la main).")
    p_retire = sub.add_parser("retire-ours")
    p_retire.add_argument("--epingle", default=str(EPINGLE))
    p_retire.add_argument("--guild", default=os.environ.get("DISCORD_GUILD_ID", ""))
    p_retire.add_argument("--apply", action="store_true",
                         help="SUPPRIME nos SEC*/proj-* paralleles. Irreversible, dry-run par defaut.")
    args = ap.parse_args(argv)

    struct_map = load_struct_map()

    if args.cmd == "plan":
        try:
            plan = build_plan(load_projects(args.epingle), struct_map)
        except Exception as exc:
            print("[ERR] Epingle illisible: %s" % exc)
            return 2
        print("=== plan Discord (depuis Epingle) ===")
        for cat, chans in plan:
            print(ascii_console("  [%s] %d salon(s)" % (cat, len(chans))))
            for chan, _topic, proj in chans:
                print(ascii_console("    #%s <- %s" % (chan, proj)))
        print("  Total: %d categories, %d salons" % (len(plan), sum(len(c) for _, c in plan)))
        return 0

    if args.cmd == "audit":
        token = os.environ.get("DISCORD_BOT_TOKEN", "")
        guild = os.environ.get("DISCORD_GUILD_ID", "")
        if not token or not guild:
            print("[ERR] DISCORD_BOT_TOKEN / DISCORD_GUILD_ID requis.")
            return 2
        try:
            plan = build_plan(load_projects(args.epingle), struct_map)
        except Exception as exc:
            print("[ERR] Epingle illisible: %s" % exc)
            return 2
        return audit_guild(guild, token, plan)

    if args.cmd == "adopt":
        token = os.environ.get("DISCORD_BOT_TOKEN", "")
        if not token:
            print("[ERR] DISCORD_BOT_TOKEN absent.")
            return 2
        if not args.guild:
            print("[ERR] --guild requis.")
            return 2
        try:
            projs = load_projects(args.epingle)
        except Exception as exc:
            print("[ERR] Epingle illisible: %s" % exc)
            return 2
        status, guild_channels = api_call("GET", "/guilds/%s/channels" % args.guild, token)
        if status != 200:
            print("[ERR] lecture salons: %s" % status)
            return 1
        adopted, ambiguous, catmap = auto_adopt(projs, guild_channels)
        print("=== adopt (ta structure gagne, zero destruction) ===")
        for proj, chan in sorted(adopted.items()):
            print(ascii_console("  [ADOPTE] %-18s -> #%s" % (proj, chan.lstrip("#"))))
        for proj, cands in sorted(ambiguous):
            print(ascii_console("  [AMBIGU] %-18s candidats: %s" % (proj, cands or "aucun — sera cree")))
        for sec, cat in sorted(catmap.items()):
            print(ascii_console("  [CAT] %-40s -> %s" % (sec[:40], cat)))
        if not args.apply:
            print("  [DRY] --apply pour ecrire %s" % STRUCT_MAP_FILE.name)
            return 0
        STRUCT_MAP_FILE.write_text(json.dumps(
            {"channels": adopted, "categories": catmap,
             "_note": "Ambiguites a trancher a la main (voir sortie adopt)."},
            indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("  [OK] %s ecrit (%d salons, %d categories). Relance plan/sync pour voir l'effet."
              % (STRUCT_MAP_FILE.name, len(adopted), len(catmap)))
        return 0

    if args.cmd == "retire-ours":
        token = os.environ.get("DISCORD_BOT_TOKEN", "")
        if not token:
            print("[ERR] DISCORD_BOT_TOKEN absent.")
            return 2
        if not args.guild:
            print("[ERR] --guild requis.")
            return 2
        status, guild_channels = api_call("GET", "/guilds/%s/channels" % args.guild, token)
        if status != 200:
            print("[ERR] lecture salons: %s" % status)
            return 1
        try:
            in_plan = set()
            for _cat, chans in build_plan(load_projects(args.epingle), load_struct_map()):
                in_plan.add(_cat)
                for chan, _t, _p in chans:
                    in_plan.add(chan)
        except Exception:
            in_plan = set()
        ours = [c for c in guild_channels if isinstance(c, dict) and (
            c.get("name", "").startswith("proj-") or c.get("name", "").startswith("SEC "))
            and c.get("name", "") not in in_plan]
        print("=== retire-ours (SUPPRESSION de notre structure parallele) ===")
        print("  Exclus (encore utilises par le plan) : tout SEC*/proj-* present ci-dessus est garde.")
        for c in ours:
            print(ascii_console("  [%s] #%s" % ("SUPPRIME" if args.apply else "DRY-supprime", c.get("name"))))
        if not args.apply:
            print("  [DRY] %d objets. --apply pour supprimer vraiment." % len(ours))
            return 0
        gone = 0
        for c in ours:
            st, _ = api_call("DELETE", "/channels/%s" % c.get("id"), token)
            if st == 200:
                gone += 1
            else:
                print("[ERR] suppression #%s: HTTP %s" % (c.get("name"), st))
            time.sleep(0.6)
        print("  [OK] %d/%d supprimes." % (gone, len(ours)))
        return 0

    if args.cmd == "sync":
        token = os.environ.get("DISCORD_BOT_TOKEN", "")
        if not token:
            print("[ERR] DISCORD_BOT_TOKEN absent — voir .env (etapes 1-5). plan reste dispo.")
            return 2
        if not args.guild:
            print("[ERR] --guild ID_DU_SERVEUR requis (clic droit serveur -> Copier l'identifiant).")
            return 2
        try:
            plan = build_plan(load_projects(args.epingle), struct_map)
        except Exception as exc:
            print("[ERR] Epingle illisible: %s" % exc)
            return 2
        stats = sync_guild(args.guild, token, plan, dry=not args.apply)
        print("  stats: %s" % stats)
        if stats.get("error"):
            return 1
        if args.webhooks:
            wanted = {}
            for _cat, chans in plan:
                for chan, _topic, proj in chans:
                    wanted[chan] = (None, slug(proj))
            if not args.apply:
                ensure_webhooks(token, {c: (None, s) for c, (_, s) in wanted.items()}, dry=True)
                return 0
            ids = collect_channel_ids(args.guild, token, set(wanted))
            full = {c: (ids.get(c), s) for c, (_, s) in wanted.items() if ids.get(c)}
            missing = sorted(set(wanted) - set(ids))
            if missing:
                print("[ERR] salons introuvables APRES sync (ne devrait pas arriver): %s" % missing)
                return 1
            created = ensure_webhooks(token, full, dry=False)
            added, repointed, kept = save_channel_map(created)
            print("  webhooks: %d ajoutes, %d repointees, %d gardes (%s)"
                  % (len(added), len(repointed), len(kept), CHANNELS_FILE.name))
        return 0

    if args.cmd == "post":
        body = args.message
        if args.message_file:
            try:
                body = Path(args.message_file).read_text(encoding="utf-8")
            except Exception as exc:
                print("[ERR] fichier illisible: %s" % exc)
        body = (body or "").strip()
        if not body:
            print("[ERR] message vide.")
            return 2
        url = webhook_for(args.project, load_channel_map())
        if not url:
            print("[ERR] aucun webhook pour '%s' (kuro_discord_channels.local.json / DISCORD_WEBHOOK_URL)." % args.project)
            return 2
        title = args.title or ("Update %s" % args.project)
        try:
            status = post_webhook(url, title, body)
            print(ascii_console("  [OK] post '%s' -> HTTP %s" % (args.project, status)))
        except Exception as exc:
            print("[ERR] post: %s" % str(exc)[:200])
            return 1
        return 0
    if args.cmd == "announce":
        token = os.environ.get("DISCORD_BOT_TOKEN", "")
        if not token:
            print("[ERR] DISCORD_BOT_TOKEN absent.")
            return 2
        if not args.guild:
            print("[ERR] --guild requis (ou DISCORD_GUILD_ID).")
            return 2
        body = args.message
        if args.message_file:
            try:
                body = Path(args.message_file).read_text(encoding="utf-8")
            except Exception as exc:
                print("[ERR] fichier illisible: %s" % exc)
                return 2
        body = (body or "").strip()
        if not body:
            print("[ERR] message vide.")
            return 2
        want = args.channel.lstrip("#")
        status, channels = api_call("GET", "/guilds/%s/channels" % args.guild, token)
        if status != 200:
            print("[ERR] lecture salons: %s" % status)
            return 1
        target = next((c for c in channels if isinstance(c, dict)
                       and c.get("type") == 0 and c.get("name") == want), None)
        if not target:
            print("[ERR] salon #%s introuvable." % want)
            return 1
        status, posted = api_call("POST", "/channels/%s/messages" % target.get("id"),
                                  token, {"content": body[:2000]})
        if status not in (200, 201) or not posted.get("id"):
            print("[ERR] post #%s: HTTP %s %s" % (want, status, str(posted)[:150]))
            return 1
        mid = posted["id"]
        print(ascii_console("  [OK] post #%s id=%s" % (want, mid)))
        if args.no_pin:
            return 0
        status, _ = api_call("PUT", "/channels/%s/pins/%s" % (target.get("id"), mid), token)
        if status in (200, 201, 204):
            print(ascii_console("  [OK] épingle #%s" % want))
            return 0
        print("[ERR] pin #%s: HTTP %s (droit Manage Messages requis)" % (want, status))
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
