#!/usr/bin/env python3
"""notify_discord.py — poste un message sur un webhook Discord (zéro dépendance).

Usage:
    python scripts/notify_discord.py --title "..." [--description "..."] [--level info|warn|alert]

Webhook lu depuis $DISCORD_WEBHOOK_URL. Si absent : no-op silencieux (le workflow
ne doit jamais échouer faute de webhook).
"""

import argparse
import json
import os
import sys
import urllib.request

COLORS = {"info": 3447003, "warn": 16098851, "alert": 15158332}
MARKERS = {"info": "[INFO]", "warn": "[ATTENTION]", "alert": "[ALERTE]"}


def send(url: str, payload: dict) -> int:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Kuro/1.0 (lambda-Section bot)",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.status


def main() -> int:
    parser = argparse.ArgumentParser(description="Notification Discord")
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--level", choices=["info", "warn", "alert"], default="info")
    args = parser.parse_args()

    url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not url:
        print("DISCORD_WEBHOOK_URL absent - notification ignoree")
        return 0

    payload = {
        "username": "Kuro",
        "embeds": [
            {
                "title": f"{MARKERS[args.level]} {args.title}",
                "description": args.description[:1900],
                "color": COLORS[args.level],
            }
        ],
    }
    try:
        status = send(url, payload)
        print(f"Discord: HTTP {status}")
    except Exception as exc:
        print(f"Discord erreur: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
