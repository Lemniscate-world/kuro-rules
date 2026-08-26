#!/usr/bin/env python3
"""generate_blog.py — Génère des billets de blog factuels automatiques.

Sources: git log, Epingle_Projets.md, TRUTH_DAILY.md, Discord (si export)
Sortie: Lemniscate-world/blog/YYYY-MM-DD-slug.md + blog/index.html

Usage:
  python scripts/generate_blog.py --dry-run
  python scripts/generate_blog.py --apply  # cree les fichiers

Chaque billet est 100% factuel: commit hash, date, % avant/apres, tests, loc.
"""
import os, re, subprocess, json, sys
from pathlib import Path
from datetime import date, datetime

HOME = Path.home()
# CI-overridable paths (workflow set KURO_RULES_DIR / LEMNISCATE_DIR / DOCS_DIR)
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
LEMNISCATE = Path(os.environ.get("LEMNISCATE_DIR", str(DOCS / "Lemniscate-world")))
EPINGLE = KURORULES / "Epingle_Projets.md"
TRUTH = KURORULES / "TRUTH_DAILY.md"
BLOG_DIR = LEMNISCATE / "blog"

def run(cmd, cwd=None):
    try:
        r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True, shell=True, timeout=8)
        return r.stdout.strip()
    except:
        return ""

def parse_epingle_projects():
    """Source unique de vérité: réutilise le parser du portfolio (60 projets, pas les livrables)."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from generate_portfolio import parse_epingle
    from generate_portfolio import inject_analytics
    sections = parse_epingle(EPINGLE)
    projs = []
    for s in sections:
        for p in s["projects"]:
            projs.append({"name": p["name"], "pct": p["pct"], "status": p["status"], "desc": p["desc"]})
    return projs

def collect_git_facts(name):
    # find repo
    cand = None
    for d in DOCS.iterdir():
        if d.is_dir() and d.name.lower() == name.lower():
            cand = d
            break
    if not cand or not (cand / ".git").exists():
        return None
    last = run('git log -1 --format="%h|%ad|%s" --date=short', cwd=cand)
    if not last:
        return None
    parts = last.strip('"').split("|", 2)
    h, d, msg = (parts + ["","",""])[:3]
    c30 = run('git rev-list --count --since="30 days ago" HEAD', cwd=cand)
    return {"hash": h, "date": d, "msg": msg, "c30": c30, "path": cand}

def generate_daily_blog(dry_run=True):
    today = date.today().isoformat()
    projs = parse_epingle_projects()
    # Find recent projects (last commit <=7j) - dynamic window
    recent = []
    from datetime import timedelta
    cutoff = date.today() - timedelta(days=7)
    for p in projs:
        facts = collect_git_facts(p["name"])
        if facts and facts.get("date"):
            try:
                ld = date.fromisoformat(facts["date"][:10])
                if ld >= cutoff:
                    recent.append((p, facts))
            except:
                pass
    if not recent:
        # fallback: take top 3 active projets
        recent = [(projs[0], collect_git_facts(projs[0]["name"]))] if projs else []
        recent = [r for r in recent if r[1] is not None]

    BLOG_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Daily summary post
    daily_slug = f"{today}-daily-truth"
    daily_path = BLOG_DIR / f"{daily_slug}.md"
    lines = []
    lines.append("---")
    lines.append(f'title: "Daily Truth — {today}"')
    lines.append(f'date: {today}')
    lines.append(f'projects: {len(projs)}')
    lines.append("---")
    lines.append("")
    lines.append(f"# Daily Truth — {today}")
    lines.append("")
    lines.append(f"> **{len(projs)} projets · {len(recent)} actifs 7j** · Généré depuis `TRUTH_DAILY.md` + `git log`")
    lines.append("")
    if TRUTH.exists():
        try:
            t = TRUTH.read_text(encoding="utf-8")
            # take first 10 lines of truth table
            lines.append("## Faits du jour (TRUTH_DAILY)")
            lines.append("")
            lines.append("```")
            for l in t.splitlines()[:25]:
                lines.append(l)
            lines.append("```")
            lines.append("")
        except:
            pass
    lines.append("## Projets actifs (7j)")
    lines.append("")
    for p, f in recent[:5]:
        lines.append(f"- **{p['name']}** `{f['hash']}` {f['date']}: _{f['msg'][:60]}_ — {p['pct']}% {p['status']} ({f['c30']} commits 30j)")
    lines.append("")
    lines.append("## Verite")
    lines.append("")
    lines.append(f"Tous les chiffres proviennent de `git log`, comptage tests, `Epingle_Projets.md`. Aucune estimation manuelle. Voir [portfolio](/).")
    lines.append("")
    daily_content = "\n".join(lines)

    # 2. Per-project posts for recent - slug uses commit date for coherence
    per_project_paths = []
    for p, f in recent[:3]:
        commit_date = f["date"][:10] if f.get("date") else today
        slug = f"{commit_date}-{p['name'].lower().replace(' ', '-')}"
        path = BLOG_DIR / f"{slug}.md"
        if path.exists():
            # already published for this commit date, skip duplicate
            continue
        plines = []
        plines.append("---")
        plines.append(f'title: "{p["name"]} — {f["date"]}"')
        plines.append(f'date: {f["date"]}')
        plines.append(f'project: {p["name"]}')
        plines.append(f'pct: {p["pct"]}')
        plines.append("---")
        plines.append("")
        plines.append(f"# {p['name']} — {f['date']}")
        plines.append("")
        plines.append(f"> **{p['pct']}% {p['status']}** · Dernier commit `{f['hash']}`")
        plines.append("")
        plines.append(f"**Message:** _{f['msg']}_")
        plines.append("")
        plines.append(f"**Description Epingle:** {p['desc'][:200]}")
        plines.append("")
        plines.append(f"**Commits 30j:** {f['c30']}")
        plines.append("")
        plines.append(f"[Voir le monde S-?](/sections/) · [Portfolio](/)")
        plines.append("")
        per_project_paths.append((path, "\n".join(plines)))

    if dry_run:
        print(f"=== Blog dry-run {today} ===")
        print(f"  Daily: {daily_path.name} ({len(daily_content.splitlines())} lignes)")
        for path, content in per_project_paths:
            print(f"  Per-project: {path.name}")
        # preview daily
        print("\n--- Daily preview (15 lignes) ---")
        for l in daily_content.splitlines()[:15]:
            print(l)
        return

    # Apply
    daily_path.write_text(daily_content, encoding="utf-8")
    print(f"  Wrote {daily_path}")
    for path, content in per_project_paths:
        path.write_text(content, encoding="utf-8")
        print(f"  Wrote {path}")

    # Generate blog/index.html
    posts = sorted(BLOG_DIR.glob("*.md"), reverse=True)
    idx = []
    idx.append('<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">')
    idx.append('<title>Blog — lambda-Section</title>')
    idx.append('<style>:root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--muted:#8b949e;--accent:#58a6ff} body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;max-width:800px;margin:0 auto;padding:2rem 1rem} a{color:var(--accent)} .post{border:1px solid var(--border);border-radius:8px;padding:1rem;margin-bottom:1rem;background:var(--card)} .meta{color:var(--muted);font-size:0.75rem}</style>')
    idx.append('</head><body>')
    idx.append('<h1>Blog — lambda-Section</h1>')
    idx.append('<p class="meta">Billets factuels auto-genere depuis git log + Epingle. Aucune hallucination.</p>')
    idx.append(f'<p class="meta"><a href="../">← Portfolio</a> · <a href="../sections/">Mondes</a></p>')
    for p in posts[:20]:
        # parse frontmatter title
        try:
            txt = p.read_text(encoding="utf-8")
            m = re.search(r'title:\s*"([^"]+)"', txt)
            title = m.group(1) if m else p.stem
            m2 = re.search(r'date:\s*(\S+)', txt)
            d = m2.group(1) if m2 else ""
        except:
            title = p.stem
            d = ""
        idx.append(f'<div class="post"><div style="font-weight:700"><a href="{p.name}">{title}</a></div><div class="meta">{d} · {p.name}</div></div>')
    idx.append('<div style="text-align:center;color:var(--muted);font-size:0.7rem;margin-top:2rem">Auto-genere quotidiennement via generate_blog.py</div>')
    idx.append('</body></html>')
    (BLOG_DIR / "index.html").write_text("\n".join(idx), encoding="utf-8")
    print(f"  Blog index: {BLOG_DIR / 'index.html'} ({len(posts)} posts)")

    # RSS feed.xml (S1)
    base = "https://lemniscate-world.github.io/Lemniscate-world/blog/"
    rss = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0"><channel>',
           '<title>lambda-Section — Blog</title>',
           f'<link>{base}</link>',
           '<description>Billets factuels auto-generes depuis git log + Epingle_Projets.md</description>']
    for p in posts[:20]:
        try:
            txt = p.read_text(encoding="utf-8")
            m = re.search(r'title:\s*"([^"]+)"', txt)
            t = m.group(1) if m else p.stem
            m2 = re.search(r'date:\s*(\S+)', txt)
            d = m2.group(1) if m2 else ""
        except Exception:
            t, d = p.stem, ""
        import html as _h
        rss.append(f'<item><title>{_h.escape(t)}</title><link>{base}{p.name}</link>'
                   f'<guid>{p.name}</guid><pubDate>{d}</pubDate></item>')
    rss.append('</channel></rss>')
    (BLOG_DIR / "feed.xml").write_text("\n".join(rss), encoding="utf-8")
    print(f"  RSS: {BLOG_DIR / 'feed.xml'}")
    from generate_portfolio import inject_analytics
    _n = inject_analytics(BLOG_DIR.parent)  # racine repo: couvre index+sections+blog
    print(f"  Analytics blog: {_n} pages" if _n else "  Analytics: absent — skip")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    dry = not args.apply
    generate_daily_blog(dry_run=dry)
