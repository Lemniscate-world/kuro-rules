#!/usr/bin/env python3
"""x_post.py — Publie un draft R94 sur X (API v2, OAuth 1.0a user-context).

Secrets (JAMAIS commites, .env gitignore) :
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET
  (https://developer.x.com -> projet+app -> User authentication -> Read+Write,
   cles du compte DU PROJET concerne — 1 compte X = 1 jeu de cles)

Securite :
- --dry-run par defaut (valide + affiche, ne poste rien).
- Refuse >280 caracteres et texte vide.
- Le draft doit venir de gen_x_posts.py (deja sanitize R94).

Zero dependance (hmac/hashlib/urllib), cross-platform (R93).

Usage :
  python scripts/x_post.py --from-file outputs/x_post_2026-09-21-helium.md --dry-run
  python scripts/x_post.py --from-file <draft> --apply
  python scripts/x_post.py --text "..." --apply
"""
import base64
import hmac
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_paths import confine_arg  # noqa: E402

TWEETS_URL = "https://api.x.com/2/tweets"
ME_URL = "https://api.x.com/2/users/me"
MAX_LEN = 280


def percent_encode(value):
    """RFC 3986 §2.1 : tout sauf [A-Za-z0-9-._~], hex MAJUSCULES."""
    return urllib.parse.quote(str(value), safe="~")


def base_string(method, url, params):
    """Base string OAuth 1.0a (RFC 5849 §3.4.1). params = [(k, v)]."""
    parts = urllib.parse.urlparse(url)
    norm_url = "{}://{}{}".format(parts.scheme.lower(), parts.netloc.lower(),
                              parts.path or "/")
    encoded = sorted((percent_encode(k), percent_encode(v)) for k, v in params)
    norm_params = "&".join(f"{k}={v}" for k, v in encoded)
    return "&".join([method.upper(), percent_encode(norm_url),
                     percent_encode(norm_params)])


def sign(base, consumer_secret, token_secret):
    # OAuth 1.0a (RFC 5849 §3.4.2) IMPOSE HMAC-SHA1 : ce n est pas du hash
    # de mot de passe (faux positif CodeQL "weak password hashing").
    # hmac.digest() = API moderne recommandee, meme octets sur le fil.
    key = "{}&{}".format(percent_encode(consumer_secret), percent_encode(token_secret or ""))
    mac = hmac.digest(key.encode(), base.encode(), "sha1")
    return base64.b64encode(mac).decode()


def auth_header(oauth_params):
    items = ", ".join(f'{percent_encode(k)}="{percent_encode(v)}"'
                      for k, v in sorted(oauth_params.items()))
    return "OAuth " + items


def build_auth(method, url, body_params, creds, nonce=None, timestamp=None):
    """Construit le header Authorization OAuth 1.0a."""
    oauth = {
        "oauth_consumer_key": creds["api_key"],
        "oauth_nonce": nonce or base64.urlsafe_b64encode(os.urandom(24)).decode().rstrip("="),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp or str(int(time.time())),
        "oauth_token": creds["access_token"],
        "oauth_version": "1.0",
    }
    sig_base = base_string(method, url, list(oauth.items()) + list(body_params or []))
    oauth["oauth_signature"] = sign(sig_base, creds["api_secret"], creds["access_secret"])
    return auth_header(oauth)


def validate(text):
    t = (text or "").strip()
    if not t:
        return None, "texte vide"
    if len(t) > MAX_LEN:
        return None, "trop long: %d/%d" % (len(t), MAX_LEN)
    return t, ""


def account_prefix(account):
    if (account or "hub").lower() == "hub":
        return "X_"
    return "X_{}_".format(account.upper().replace("-", "_"))


def post_tweet(text, creds):
    body = json.dumps({"text": text}).encode()
    header = build_auth("POST", TWEETS_URL, [], creds)
    req = urllib.request.Request(
        TWEETS_URL, data=body, method="POST",
        headers={"Authorization": header, "Content-Type": "application/json",
                 "User-Agent": "Kuro/1.0 (lambda-Section)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8") or "{}")


def verify_creds(creds):
    """GET users/me : valide les cles SANS poster. Retourne (status, data)."""
    header = build_auth("GET", ME_URL, [], creds)
    req = urllib.request.Request(
        ME_URL, method="GET",
        headers={"Authorization": header, "User-Agent": "Kuro/1.0 (lambda-Section)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8") or "{}")


def load_creds(prefix="X_"):
    creds = {"api_key": os.environ.get(prefix + "API_KEY", ""),
             "api_secret": os.environ.get(prefix + "API_SECRET", ""),
             "access_token": os.environ.get(prefix + "ACCESS_TOKEN", ""),
             "access_secret": os.environ.get(prefix + "ACCESS_SECRET", "")}
    missing = [k for k, v in creds.items() if not v]
    return creds, missing


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Poste un draft R94 sur X (dry-run par defaut)")
    ap.add_argument("--text", default="")
    ap.add_argument("--from-file", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="Valide les cles (GET users/me) SANS poster.")
    ap.add_argument("--account", default="hub",
                    help="Compte cible : hub (cles X_*) ou annexe (cles X_<SLUG>_*, ex: --account helium).")
    ap.add_argument("--dry-run", action="store_true",
                    help="Explicite le defaut (valide + affiche, ne poste rien).")
    args = ap.parse_args(argv)

    print("=== x_post (X API v2) ===")
    print(f"  compte: @{args.account}")
    if args.verify:
        creds, missing = load_creds(account_prefix(args.account))
        if missing:
            print("[ERR] cles manquantes: {}.".format(", ".join(missing)))
            return 2
        try:
            status, data = verify_creds(creds)
            user = (data.get("data") or {})
            print("  [OK] HTTP {} -> @{} ({})".format(status, user.get("username", "?"), user.get("name", "?")))
        except Exception as exc:
            print(f"[ERR] verify: {str(exc)[:300]}")
            return 1
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
    text, err = validate(text)
    if err:
        print(f"[ERR] draft invalide: {err}")
        return 2

    print("=== x_post (X API v2) ===")
    print(f"  compte: @{args.account}")
    print("  {}".format(text.replace("\n", " / ")))
    print("  %d/%d caracteres" % (len(text), MAX_LEN))
    if not args.apply:
        print(f"  [DRY] rien poste. Relance avec --apply (+ cles {account_prefix(args.account)}*).")
        return 0

    creds, missing = load_creds(account_prefix(args.account))
    if missing:
        print("[ERR] cles manquantes: {} (voir docstring, 1 jeu par compte X).".format(", ".join(missing)))
        return 2
    try:
        status, data = post_tweet(text, creds)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:500]
        print(f"[ERR] post: HTTP {exc.code} {body}")
        return 1
    except Exception as exc:
        print(f"[ERR] post: {str(exc)[:300]}")
        return 1
    tid = (data.get("data") or {}).get("id", "?")
    print(f"  [OK] HTTP {status} id={tid}")
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from post_policy import append_posts_log, load_state, record_post, save_state
        save_state(record_post(load_state(), args.account, "", tid))
        append_posts_log(args.account, Path(args.from_file).stem if args.from_file else "", text, tid)
    except Exception as exc:
        print(f"  [WARN] log local impossible: {str(exc)[:120]}")
    print("  Rappel R99 : logger dans docs/tracking/acquisition_tracker.md sous 5 min.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
