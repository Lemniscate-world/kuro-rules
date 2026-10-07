#!/usr/bin/env python3
"""kit_post.py — Newsletter Kit via API v3 (gratuit 0-10k abonnes).

Auth : api_secret (Kit Settings > API -> KIT_API_SECRET).
Cle KIT_API_KEY gardee pour v4 le jour ou le compte y est eligible.

Commandes : check (compte), subscribe, tag, broadcast (draft/send best-effort).
Erreurs API affichees telles quelles (l'API repond explicitement).

Zero dependance, cross-platform (R93). Lecture seule par defaut, --apply pour agir.

Usage :
  python scripts/kit_post.py check
  python scripts/kit_post.py subscribe --email a@b.cd [--name X] [--tag prospect] --apply
  python scripts/kit_post.py broadcast --subject "..." --html-file <fichier> [--send] --apply
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

API = "https://api.convertkit.com/v3"


class KitError(Exception):
    pass


def _secret():
    s = os.environ.get("KIT_API_SECRET", "")
    if not s:
        raise KitError("KIT_API_SECRET absent (Kit Settings > API).")
    return s


def api_call(method, path, params=None):
    params = dict(params or {})
    if method == "GET":
        params["api_secret"] = _secret()
        url = API + path + "?" + urllib.parse.urlencode(params)
        data = None
    else:
        params["api_secret"] = _secret()
        url, data = API + path, json.dumps(params).encode()
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json",
                 "User-Agent": "Kuro/1.0 (lambda-Section)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        raise KitError(f"HTTP {exc.code} {body}")
    except Exception as exc:
        raise KitError(str(exc)[:200])


def check_key():
    status, data = api_call("GET", "/account")
    if not isinstance(data, dict) or not data.get("primary_email_address"):
        raise KitError(f"reponse inattendue: {json.dumps(data)[:200]}")
    return {"http": status, "plan": data.get("plan_type", "?"),
            "email": data.get("primary_email_address", "?")}


def subscribe(email, name="", tags=()):
    if "@" not in (email or ""):
        raise KitError("email invalide")
    payload = {"email_address": email}
    if name:
        payload["first_name"] = name
    if tags:
        payload["tags"] = list(tags)
    status, data = api_call("POST", "/subscribers", payload)
    sub = data.get("subscription", data)
    if not isinstance(sub, dict) or not sub.get("id"):
        raise KitError(f"reponse inattendue: {json.dumps(data)[:200]}")
    return {"id": sub["id"], "email": sub.get("email_address", email)}


def create_tag(name):
    status, data = api_call("POST", "/tags", {"tag": {"name": name}})
    tag = data.get("tag", data)
    if not isinstance(tag, dict) or not tag.get("id"):
        raise KitError(f"reponse inattendue: {json.dumps(data)[:200]}")
    return {"id": tag["id"], "name": tag.get("name", name)}


def create_broadcast(subject, html):
    if not (subject or "").strip():
        raise KitError("sujet vide")
    if not (html or "").strip():
        raise KitError("contenu vide")
    status, data = api_call("POST", "/broadcasts",
                            {"subject": subject, "content": html})
    b = data.get("broadcast", data)
    if not isinstance(b, dict) or not b.get("id"):
        raise KitError(f"reponse inattendue: {json.dumps(data)[:200]}")
    return {"id": b["id"]}


def send_broadcast(broadcast_id):
    status, data = api_call("POST", f"/broadcasts/{broadcast_id}/send", {})
    return {"http": status, "response": data}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Newsletter Kit via API (lecture par defaut)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    p_sub = sub.add_parser("subscribe")
    p_sub.add_argument("--email", required=True)
    p_sub.add_argument("--name", default="")
    p_sub.add_argument("--tag", action="append", default=[])
    p_sub.add_argument("--apply", action="store_true")
    p_tag = sub.add_parser("tag")
    p_tag.add_argument("--name", required=True)
    p_tag.add_argument("--apply", action="store_true")
    p_bc = sub.add_parser("broadcast")
    p_bc.add_argument("--subject", required=True)
    p_bc.add_argument("--html-file", default="")
    p_bc.add_argument("--html", default="")
    p_bc.add_argument("--send", action="store_true")
    p_bc.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)

    try:
        if args.cmd == "check":
            info = check_key()
            print("  [OK] HTTP {http} plan={plan}".format(**info))
            return 0
        if args.cmd == "subscribe":
            print("  {} {} tags={}".format(args.email, args.name, args.tag or "-"))
            if not args.apply:
                print("  [DRY] rien cree. --apply pour inscrire.")
                return 0
            res = subscribe(args.email, args.name, args.tag)
            print("  [OK] abonne id={}".format(res["id"]))
            return 0
        if args.cmd == "tag":
            if not args.apply:
                print(f"  [DRY] rien cree. --apply pour creer le tag '{args.name}'.")
                return 0
            res = create_tag(args.name)
            print("  [OK] tag id={}".format(res["id"]))
            return 0
        if args.cmd == "broadcast":
            html = args.html
            if args.html_file:
                html = Path(args.html_file).read_text(encoding="utf-8")
            print("  sujet: %s (%d car html)" % (args.subject, len(html or "")))
            if not args.apply:
                print("  [DRY] rien cree. --apply pour creer%s." % (" + envoyer" if args.send else " (draft)"))
                return 0
            res = create_broadcast(args.subject, html)
            print("  [OK] broadcast id={}".format(res["id"]))
            if args.send:
                sent = send_broadcast(res["id"])
                print(f"  [OK] envoi: {sent}")
            return 0
    except KitError as exc:
        print(f"[ERR] kit: {exc}")
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
