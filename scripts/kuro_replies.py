#!/usr/bin/env python3
"""kuro_replies.py — file de réponses de collaboration (R96/R107/R119/R121).

Une seule vue pour répondre vite, sans rien publier :

  python scripts/kuro_replies.py                 # résumé texte, hors ligne
  python scripts/kuro_replies.py --gh            # + notifications GitHub
  python scripts/kuro_replies.py --json          # sortie machine
  python scripts/kuro_replies.py --write         # outputs/replies_queue.json
  python scripts/kuro_replies.py --strict        # exit 1 si retard

Sources lues :
  - docs/tracking/acquisition_tracker.md : commentaires GitHub "non prouvés"
    (section 1) et collabs au statut "nouveau" (section 5).
  - outputs/replies_inbox.json (optionnel) : DMs / mails / LinkedIn collectés
    à la main, au format [{"source","url","title","received_at"}].
  - `gh api notifications` uniquement avec --gh (réseau opt-in, R123).

Lecture seule : aucun post, aucune réponse envoyée automatiquement.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
TRACKER = ROOT / "docs" / "tracking" / "acquisition_tracker.md"
INBOX = ROOT / "outputs" / "replies_inbox.json"
QUEUE = ROOT / "outputs" / "replies_queue.json"
HORIZON_HOURS = 24

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kuro_paths import confine_arg  # noqa: E402

HIGH_REASONS = {"mention", "team_mention", "review_requested", "comment", "author"}
COLLAB_OPEN = {"", "nouveau", "new", "à répondre", "a repondre"}


def parse_ts(value) -> datetime | None:
    """ISO 8601 -> datetime UTC. Jamais d'exception."""
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text)
    except Exception:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_sections(text: str) -> dict[int, list[str]]:
    """Découpe le tracker en {numéro: lignes} sur les titres '## N. ...'."""
    sections: dict[int, list[str]] = {}
    current = None
    for line in text.splitlines():
        match = re.match(r"^##\s+(\d+)\.\s+(.*)$", line.strip())
        if match:
            current = int(match.group(1))
            sections[current] = []
        elif current is not None:
            sections[current].append(line)
    return sections


def parse_table(lines: list[str]) -> list[dict[str, str]]:
    """Table markdown -> list[dict]. Ignore les lignes vides et le séparateur."""
    rows = [line.strip() for line in lines if line.strip().startswith("|")]
    if len(rows) < 2:
        return []
    header = [cell.strip() for cell in rows[0].strip("|").split("|")]
    out = []
    for line in rows[2:]:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < len(header):
            cells += [""] * (len(header) - len(cells))
        row = dict(zip(header, cells))
        if any(row.values()):
            out.append(row)
    return out


def html_url(subject_type: str, api_url: str) -> str:
    """URL API GitHub -> URL publique (pull au singulier)."""
    url = (api_url or "").replace("https://api.github.com/repos/", "https://github.com/")
    if (subject_type or "").lower() == "pullrequest":
        url = url.replace("/pulls/", "/pull/")
    return url


def normalize_notification(payload: dict) -> dict:
    """Notification `gh api` -> item de file stable."""
    subject = payload.get("subject") or {}
    repo = (payload.get("repository") or {}).get("full_name", "")
    api_url = subject.get("url") or ""
    number = ""
    match = re.search(r"/(?:issues|pulls|discussions)/(\d+)", api_url)
    if match:
        number = match.group(1)
    reason = (payload.get("reason") or "").lower()
    return {
        "source": "github",
        "repo": repo,
        "number": number,
        "title": subject.get("title") or "(sans titre)",
        "url": html_url(subject.get("type", ""), api_url) or (payload.get("url") or ""),
        "reason": reason,
        "priority": "haute" if reason in HIGH_REASONS else "normale",
        "updated_at": payload.get("updated_at") or "",
    }


def normalize_inbox_item(item: dict) -> dict:
    return {
        "source": (item.get("source") or "manuel").strip(),
        "repo": "",
        "number": "",
        "title": (item.get("title") or "(sans titre)").strip(),
        "url": (item.get("url") or "").strip(),
        "reason": (item.get("reason") or "collab").strip(),
        "priority": "haute",
        "updated_at": item.get("received_at") or item.get("date") or "",
    }


def classify(items: list[dict], now: datetime | None = None,
             horizon_hours: int = HORIZON_HOURS) -> tuple[list[dict], list[dict]]:
    """Sépare (en retard, à traiter). L'âge est calculé, jamais deviné."""
    now = now or datetime.now(timezone.utc)
    late: list[dict] = []
    due: list[dict] = []
    for item in items:
        ts = parse_ts(item.get("updated_at"))
        age = None if ts is None else max(0.0, (now - ts).total_seconds() / 3600)
        enriched = {**item, "age_hours": None if age is None else round(age, 1)}
        if age is not None and age > horizon_hours:
            late.append(enriched)
        else:
            due.append(enriched)
    late.sort(key=lambda i: i.get("age_hours") or 0, reverse=True)
    due.sort(key=lambda i: i.get("updated_at") or "", reverse=True)
    return late, due


def _run_gh():
    proc = subprocess.run(
        ["gh", "api", "notifications?per_page=50"],
        capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "gh api a échoué").strip()[:200])
    return json.loads(proc.stdout or "[]")


def fetch_github_notifications(runner=None) -> list[dict]:
    """Notifications non lues. Panne gh = liste vide + avertissement."""
    try:
        payload = (runner or _run_gh)()
    except Exception as exc:
        print(f"[WARN] gh indisponible : {exc}", file=sys.stderr)
        return []
    if not isinstance(payload, list):
        return []
    return [normalize_notification(n) for n in payload if n.get("unread", True)]


def load_tracker(path: Path) -> dict[str, list]:
    """Signaux du tracker : commentaires non prouvés + collabs à traiter."""
    text = Path(path).read_text(encoding="utf-8")
    sections = parse_sections(text)
    unverified = []
    for row in parse_table(sections.get(1, [])):
        link = row.get("Lien", "")
        result = row.get("Résultat", "").lower()
        if "github.com" in link and ("non prouv" in result or "no activity" in result):
            unverified.append({
                "date": row.get("Date", ""),
                "title": row.get("Titre / message (60 car)", ""),
                "url": link,
            })
    collabs = []
    for row in parse_table(sections.get(5, [])):
        if (row.get("Statut") or "").strip().lower() in COLLAB_OPEN:
            collabs.append(row)
    return {"unverified": unverified, "collabs": collabs}


def load_inbox(path: Path) -> list[dict]:
    """Inbox manuelle JSON. Absente ou invalide = vide, jamais d'exception."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except Exception as exc:
        print(f"[WARN] inbox illisible : {exc}", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    return [normalize_inbox_item(i) for i in data if isinstance(i, dict)]


def render_text(late: list[dict], due: list[dict], unverified: list[dict],
                collabs: list[dict]) -> str:
    lines = ["File de réponses (R96 / R107 / R119 / R121)"]

    def block(title, items, fmt):
        lines.append("")
        lines.append(f"{title} ({len(items)})")
        if not items:
            lines.append("  —")
        for item in items:
            lines.append("  " + fmt(item))

    block("EN RETARD", late, lambda i: (
        f"[{i.get('age_hours')} h] {i.get('source')} {i.get('repo')}#{i.get('number')} "
        f"— {i.get('title')} ({i.get('reason')}) {i.get('url')}"
    ))
    block("À TRAITER", due, lambda i: (
        f"[{i.get('age_hours') if i.get('age_hours') is not None else '?'} h] "
        f"{i.get('source')} {i.get('repo')} — {i.get('title')} ({i.get('reason')})"
    ))
    block("À VÉRIFIER", unverified, lambda i: (
        f"{i.get('date')} — {i.get('title')} : visibilité publique non confirmée"
    ))
    block("COLLABS NON TRAITÉES", collabs, lambda i: (
        f"{i.get('Date')} — {i.get('Qui')} via {i.get('Canal')} : {i.get('Demande')}"
    ))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="File de réponses (lecture seule).")
    parser.add_argument("--gh", action="store_true", help="interroger gh api notifications")
    parser.add_argument("--json", action="store_true", help="sortie JSON")
    parser.add_argument("--write", action="store_true", help="écrire outputs/replies_queue.json")
    parser.add_argument("--strict", action="store_true", help="exit 1 si réponse en retard")
    parser.add_argument("--tracker", default="docs/tracking/acquisition_tracker.md")
    parser.add_argument("--inbox", default="outputs/replies_inbox.json")
    parser.add_argument("--horizon-hours", type=int, default=HORIZON_HOURS)
    parser.add_argument("--now", default="", help="ISO 8601, pour un run reproductible")
    args = parser.parse_args(argv)

    tracker = confine_arg(args.tracker, ROOT)
    inbox = confine_arg(args.inbox, ROOT)
    try:
        signals = load_tracker(tracker) if tracker.exists() else {"unverified": [], "collabs": []}
    except Exception as exc:
        print(f"[WARN] tracker illisible : {exc}", file=sys.stderr)
        signals = {"unverified": [], "collabs": []}

    items = load_inbox(inbox)
    if args.gh:
        items += fetch_github_notifications()

    now = parse_ts(args.now) if args.now else datetime.now(timezone.utc)
    late, due = classify(items, now, args.horizon_hours)
    payload = {
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        "horizon_hours": args.horizon_hours,
        "late": late,
        "due": due,
        "unverified": signals["unverified"],
        "collabs": signals["collabs"],
    }

    if args.write:
        QUEUE.parent.mkdir(parents=True, exist_ok=True)
        QUEUE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(late, due, signals["unverified"], signals["collabs"]))
    if args.strict and (late or signals["collabs"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
