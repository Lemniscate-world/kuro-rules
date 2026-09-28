#!/usr/bin/env python3
"""kit_sync.py — Pousse les numeros .md vers Kit en drafts (jamais d'envoi auto).

Etat : <dossier>/.kit_ids.json {fichier: broadcast_id} — ne recree jamais.
Converti MD->HTML minimal. Sujets depuis le 1er H1.

Usage :
  python scripts/kit_sync.py --dir ../OpenQuant/research/newsletter [--apply]
"""
import html
import json
import os
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def md_to_html(text):
    out = []
    for line in (text or "").splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("# "):
            out.append("<h1>%s</h1>" % html.escape(s[2:]))
        elif s.startswith("## "):
            out.append("<h2>%s</h2>" % html.escape(s[3:]))
        elif re.match(r"^\d+\.\s", s):
            out.append("<p><strong>%s</strong></p>" % html.escape(s))
        elif s.startswith(("- ", "* ")):
            out.append("<p>%s</p>" % html.escape(s[2:]))
        elif s.startswith(">"):
            out.append("<blockquote>%s</blockquote>" % html.escape(s[1:].strip()))
        elif s.startswith("*") and s.endswith("*"):
            out.append("<p><em>%s</em></p>" % html.escape(s.strip("*")))
        else:
            out.append("<p>%s</p>" % html.escape(s))
    body = "\n".join(out)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)


def subject_of(md_text, fallback):
    m = re.search(r"^#\s+(.+)$", md_text or "", re.MULTILINE)
    return m.group(1).strip() if m else fallback


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Sync numeros .md -> drafts Kit")
    ap.add_argument("--dir", default="")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--send-next", action="store_true",
                    help="Envoie le plus vieux draft non envoye (revue humaine d'abord).")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import kit_post as kp

    base = Path(args.dir) if args.dir else Path.home() / "Documents" / "OpenQuant" / "research" / "newsletter"
    if not base.is_dir():
        print("[ERR] dossier introuvable: %s" % base)
        return 2
    state_path = base / ".kit_ids.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    except Exception:
        state = {}
    files = sorted(base.glob("issue-*.md"))
    if not files:
        print("[SKIP] aucun issue-*.md.")
        return 0
    changed = False
    for path in files:
        if path.name in state:
            print("  [SKIP] %s deja en draft (%s)" % (path.name, state[path.name]))
            continue
        md = path.read_text(encoding="utf-8")
        subject = subject_of(md, path.stem)
        print("  %s -> '%s'" % (path.name, subject[:50]))
        if not args.apply:
            continue
        try:
            res = kp.create_broadcast(subject, md_to_html(md))
            state[path.name] = res["id"]
            changed = True
            print("  [OK] draft id=%s" % res["id"])
        except Exception as exc:
            print("  [ERR] %s: %s" % (path.name, str(exc)[:200]))
            return 1
    if changed and args.apply:
        state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
    if not args.apply:
        print("  [DRY] --apply pour creer les drafts.")
    if args.send_next:
        import kit_post as kp
        sent = state.get("_sent", [])
        todo = sorted(f for f in files if f.name in state and state[f.name] not in sent
                      and isinstance(state[f.name], str))
        if not todo:
            print("  [SKIP] rien a envoyer (tous envoyes ou aucun draft).")
            return 0
        target = todo[0]
        bid = state[target.name]
        print("  envoi draft %s (%s) ..." % (target.name, bid))
        if not args.apply:
            print("  [DRY] --apply pour envoyer vraiment (irreversible, audience reelle).")
            return 0
        try:
            print("  [OK] envoye: %s" % kp.send_broadcast(bid))
            sent.append(bid)
            state["_sent"] = sent
            state_path.write_text(json.dumps(state, indent=1, ensure_ascii=False), encoding="utf-8")
        except Exception as exc:
            print("  [ERR] envoi: %s" % str(exc)[:200])
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
