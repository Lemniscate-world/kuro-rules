#!/usr/bin/env python3
"""buffer_post.py — Publie via Buffer (gratuit : 3 canaux, 10 posts en file/canal).

Cle perso : Buffer Settings > API -> BUFFER_API_KEY (header Bearer).
Canaux : `buffer_post.py channels` liste les IDs (connecter les profils X d'abord).

Modes : addToQueue (defaut, respecte le planning Buffer), shareNow (--now),
customScheduled (--at ISO-UTC). File pleine (free) -> MutationError claire,
jamais de crash.

Zero dependance, cross-platform (R93). --dry-run par defaut.

Usage :
  python scripts/buffer_post.py channels
  python scripts/buffer_post.py post --channel ID --from-file <draft> [--now] [--apply]
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_paths import confine_arg  # noqa: E402

API = "https://api.buffer.com"
MAX_LEN = 280
POST_HOUR_UTC = 20  # heure de publication auto (modifiable via POST_HOUR_UTC)


def next_slot_utc(hour=None, now=None):
    """Prochain passage 20h UTC (ou heure donnee). Format ISO UTC pour dueAt."""
    from datetime import datetime, timedelta, timezone
    now = now or datetime.now(timezone.utc)
    h = int(hour if hour is not None else os.environ.get("POST_HOUR_UTC", POST_HOUR_UTC))
    slot = now.replace(hour=h % 24, minute=0, second=0, microsecond=0)
    if slot <= now:
        slot += timedelta(days=1)
    return slot.strftime("%Y-%m-%dT%H:%M:%S.000Z")


class BufferError(Exception):
    pass


def gql(query_text, api_key):
    req = urllib.request.Request(
        API, data=json.dumps({"query": query_text}).encode(), method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json",
                 "User-Agent": "Kuro/1.0 (lambda-Section)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        raise BufferError("HTTP {} {}".format(exc.code, exc.read().decode("utf-8", errors="replace")[:300]))
    except Exception as exc:
        raise BufferError(str(exc)[:200])
    if isinstance(data, dict) and data.get("errors"):
        raise BufferError("; ".join(str(e.get("message", e)) for e in data["errors"])[:300])
    return data.get("data", {}) or {}


def list_organizations(api_key):
    data = gql("query GetOrganizations { account { organizations { id name } } }", api_key)
    orgs = ((data.get("account") or {}).get("organizations", [])) or []
    return [{"id": o.get("id", ""), "name": o.get("name", "")} for o in orgs if o.get("id")]


def list_channels(api_key):
    out = []
    for org in list_organizations(api_key):
        data = gql('query GetChannels {{ channels(input: {{ organizationId: "{}" }}) {{ id name service }} }}'.format(org["id"]), api_key)
        for c in data.get("channels", []) or []:
            if c.get("id"):
                out.append({"id": c["id"], "name": c.get("name", ""),
                            "service": c.get("service", ""), "org": org["name"]})
    return out


def create_post(text, channel_id, api_key, mode="addToQueue", due_at=""):
    t = (text or "").strip()
    if not t:
        raise BufferError("texte vide")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from gen_x_posts import x_len
        size = x_len(t)
    except Exception:
        size = len(t)
    if size > MAX_LEN:
        raise BufferError("trop long: %d/%d" % (size, MAX_LEN))
    due = f', dueAt: "{due_at}"' if mode == "customScheduled" and due_at else ""
    query = (f"mutation CreatePost {{ createPost(input: {{ text: {json.dumps(t)}, channelId: \"{channel_id}\", "
             f"schedulingType: automatic, mode: {mode}{due} }}) {{ ... on PostActionSuccess {{ post {{ id text dueAt }} }} "
             "... on MutationError { message } } }")
    data = gql(query, api_key)
    node = (data.get("createPost") or {})
    post = node.get("post") or {}
    if post.get("id"):
        return {"id": post["id"], "dueAt": post.get("dueAt", ""), "queued": mode != "shareNow"}
    raise BufferError(node.get("message") or f"reponse inattendue: {json.dumps(data)[:200]}")


def create_thread(main_text, reply_text, channel_id, api_key, mode="customScheduled", due_at=""):
    """Thread X : post nu + reply (le lien vit dans le reply, pas dans le post
    -> pas de penalite reach des liens externes). Retourne comme create_post."""
    main = (main_text or "").strip()
    reply = (reply_text or "").strip()
    if not main or not reply:
        raise BufferError("thread incomplet")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from gen_x_posts import x_len
        sizes = (x_len(main), x_len(reply))
    except Exception:
        sizes = (len(main), len(reply))
    if max(sizes) > MAX_LEN:
        raise BufferError("thread trop long: %s/%d" % (sizes, MAX_LEN))
    due = f', dueAt: "{due_at}"' if mode == "customScheduled" and due_at else ""
    query = (f"mutation CreateThreadedPost {{ createPost(input: {{ text: {json.dumps(main)}, channelId: \"{channel_id}\", "
             f"schedulingType: automatic, mode: {mode}{due}, metadata: {{ twitter: {{ thread: [ "
             f"{{ text: {json.dumps(main)} }}, {{ text: {json.dumps(reply)} }} ] }} }} }}) {{ ... on PostActionSuccess {{ post {{ id dueAt }} }} "
             "... on MutationError { message } } }")
    data = gql(query, api_key)
    node = (data.get("createPost") or {})
    post = node.get("post") or {}
    if post.get("id"):
        return {"id": post["id"], "dueAt": post.get("dueAt", ""), "queued": mode != "shareNow"}
    raise BufferError(node.get("message") or f"reponse inattendue: {json.dumps(data)[:200]}")


def _delete_mutation(post_id, field):
    return (f"mutation DeletePost {{ deletePost(input: {{ {field}: \"{post_id}\" }}) {{ __typename "
            "... on MutationError { message } } }")


def delete_post(post_id, api_key):
    data = gql(_delete_mutation(post_id, "id"), api_key)
    node = data.get("deletePost") or {}
    if node.get("__typename") in ("DeletePostPayload", "DeletePostSuccess"):
        return True
    raise BufferError(node.get("message") or f"suppression impossible: {json.dumps(data)[:200]}")


def list_scheduled(api_key, org_id=""):
    if not org_id:
        orgs = list_organizations(api_key)
        if not orgs:
            raise BufferError("aucune organisation")
        org_id = orgs[0]["id"]
    query = (f"query GetScheduledPosts {{ posts(input: {{ organizationId: \"{org_id}\", "
             "filter: { status: [scheduled] } }) { edges { node { id text createdAt } } } }")
    data = gql(query, api_key)
    out = []
    for e in (data.get("posts") or {}).get("edges", []) or []:
        node = e.get("node") or {}
        if node.get("id"):
            out.append({"id": node["id"], "text": (node.get("text") or "")[:80],
                        "createdAt": node.get("createdAt", "")})
    return out


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Poste via Buffer (dry-run par defaut)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("channels")
    p = sub.add_parser("post")
    p.add_argument("--channel", required=True)
    p.add_argument("--text", default="")
    p.add_argument("--from-file", default="")
    p.add_argument("--now", action="store_true", help="shareNow (sinon file d'attente).")
    p.add_argument("--at", default="", help="ISO UTC pour customScheduled.")
    p.add_argument("--apply", action="store_true")
    d = sub.add_parser("delete")
    d.add_argument("--id", required=True, help="ID du post Buffer a retirer de la file.")
    d.add_argument("--apply", action="store_true")
    q = sub.add_parser("queue")
    q.add_argument("--org", default="", help="ID d'organisation (defaut: la premiere).")
    args = ap.parse_args(argv)

    api_key = os.environ.get("BUFFER_API_KEY", "")
    if not api_key:
        print("[ERR] BUFFER_API_KEY absent (Buffer Settings > API).")
        return 2
    try:
        if args.cmd == "channels":
            for c in list_channels(api_key):
                print("  {}  {} [{}]".format(c["id"], c["name"], c.get("service", "?")))
            return 0
        if args.cmd == "delete":
            print(f"  suppression post {args.id} ...")
            if not args.apply:
                print("  [DRY] rien supprime. --apply pour retirer vraiment de la file.")
                return 0
            delete_post(args.id, api_key)
            print("  [OK] post retire de la file Buffer.")
            return 0
        if args.cmd == "queue":
            for p in list_scheduled(api_key, args.org):
                print("  {}  {} | {}".format(p["id"], p["createdAt"][:16], p["text"]))
            return 0
        text = args.text
        if args.from_file:
            try:
                text = confine_arg(args.from_file, ROOT).read_text(encoding="utf-8")
            except SystemExit:
                raise
            except Exception as exc:
                print(f"[ERR] draft illisible: {exc}")
                return 2
        text = (text or "").strip()
        mode = "shareNow" if args.now else ("customScheduled" if args.at else "addToQueue")
        print("  {}".format(text.replace("\n", " / ")[:160]))
        print("  %d/%d caracteres -> canal %s [%s]" % (len(text), MAX_LEN, args.channel, mode))
        if not args.apply:
            print("  [DRY] rien envoye. --apply pour mettre en file.")
            return 0
        res = create_post(text, args.channel, api_key, mode=mode, due_at=args.at)
        print("  [OK] id={} dueAt={}".format(res["id"], res.get("dueAt", "?")))
        print("  Rappel R99 : logger dans docs/tracking/acquisition_tracker.md sous 5 min.")
        return 0
    except BufferError as exc:
        print(f"[ERR] buffer: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
