#!/usr/bin/env python3
"""generate_portfolio.py — Generate portfolio HTML from Epingle_Projets.md.

Reads ~/Documents/kuro-rules/Epingle_Projets.md and produces index.html
for the Lemniscate-world GitHub Pages site.

Usage:
    python scripts/generate_portfolio.py [--output path/to/index.html]

The output defaults to ~/Documents/Lemniscate-world/index.html.
Run this after updating Epingle_Projets.md.
"""

import re, sys
from datetime import date
from pathlib import Path

KURORULES = Path.home() / "Documents" / "kuro-rules"
LEMNISCATE = Path.home() / "Documents" / "Lemniscate-world"
EPINGLE = KURORULES / "Epingle_Projets.md"
OUTPUT = LEMNISCATE / "index.html"

CSS = """\
  :root {
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #c9d1d9; --muted: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --yellow: #d2991d; --orange: #db6d28; --red: #f85149;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; padding: 2rem 1rem; max-width: 1100px; margin: 0 auto; }
  h1 { font-size: 1.8rem; margin-bottom: 0.25rem; }
  h2 { font-size: 1.2rem; color: var(--accent); margin: 2rem 0 0.75rem; padding-bottom: 0.4rem; border-bottom: 1px solid var(--border); }
  h3 { font-size: 0.85rem; color: var(--muted); font-weight: normal; margin-bottom: 1.5rem; }
  .subtitle { color: var(--muted); font-size: 0.9rem; margin-bottom: 0.5rem; }
  .meta { color: var(--muted); font-size: 0.75rem; margin-bottom: 2rem; }
  .section { margin-bottom: 1.5rem; }
  .section-theme { color: var(--muted); font-style: italic; font-size: 0.8rem; margin-bottom: 0.5rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; padding: 0.5rem 0.75rem; color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover { background: rgba(88,166,255,0.04); }
  .proj-name { font-weight: 600; white-space: nowrap; }
  .proj-desc { color: var(--muted); font-size: 0.8rem; max-width: 400px; }
  .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 999px; font-size: 0.7rem; font-weight: 600; }
  .badge-actif { background: rgba(63,185,80,0.15); color: var(--green); }
  .badge-validation { background: rgba(210,153,29,0.15); color: var(--yellow); }
  .badge-proto { background: rgba(88,166,255,0.12); color: var(--accent); }
  .badge-nouveau { background: rgba(139,148,158,0.12); color: var(--muted); }
  .badge-archive { background: rgba(248,81,73,0.1); color: var(--red); }
  .badge-outil { background: rgba(139,148,158,0.08); color: var(--muted); }
  .badge-recherche { background: rgba(139,148,158,0.1); color: var(--muted); }
  .bar { height: 5px; background: var(--border); border-radius: 3px; min-width: 60px; overflow: hidden; }
  .bar-fill { height: 100%; border-radius: 3px; }
  .bar-high { background: var(--green); }
  .bar-mid { background: var(--yellow); }
  .bar-low { background: var(--orange); }
  .bar-mini { background: var(--accent); }
  .stats { display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem; min-width: 100px; }
  .stat-val { font-size: 1.3rem; font-weight: 700; }
  .stat-label { font-size: 0.7rem; color: var(--muted); }
  .footer { text-align: center; color: var(--muted); font-size: 0.7rem; margin-top: 3rem; padding-top: 1rem; border-top: 1px solid var(--border); }
  a { color: var(--accent); text-decoration: none; }
  a:hover { text-decoration: underline; }
  @media (max-width: 700px) { .proj-desc { display: none; } td { padding: 0.5rem 0.4rem; } }
"""


def status_badge(status):
    status_lower = status.strip().lower()
    if "actif" in status_lower:
        return "badge-actif"
    if "validation" in status_lower:
        return "badge-validation"
    if "proto" in status_lower:
        return "badge-proto"
    if "nouveau" in status_lower:
        return "badge-nouveau"
    if "archive" in status_lower:
        return "badge-archive"
    if "outil" in status_lower:
        return "badge-outil"
    if "recherche" in status_lower or "pivot" in status_lower:
        return "badge-recherche"
    return "badge-nouveau"


def progress_class(pct):
    if pct >= 70: return "bar-high"
    if pct >= 30: return "bar-mid"
    if pct >= 10: return "bar-low"
    return "bar-mini"


def parse_epingle(path):
    """Parse Epingle_Projets.md into a list of sections."""
    text = path.read_text(encoding="utf-8")
    sections = []
    current_section = None

    for line in text.splitlines():
        # Section header: ## λ-Section-X — Name
        m = re.match(r'^##\s+(λ-Section-\d+.*)', line)
        if m:
            name = m.group(1).replace("λ", "&#955;").replace("—", "&mdash;")
            current_section = {"name": name, "theme": "", "projects": []}
            sections.append(current_section)
            continue

        # Theme line: > Thématique
        if current_section and line.startswith("> ") and not current_section["theme"]:
            current_section["theme"] = line[2:].strip()
            continue

        # Project row: | **Name** | pct% | Status | Description |
        if current_section and line.startswith("| **"):
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                name = parts[0].replace("**", "")
                # Only process named projects (skip --- and headers)
                if name and not name.startswith("-"):
                    pct_str = parts[1].replace("%", "").replace("—", "0")
                    try:
                        pct = int(pct_str)
                    except ValueError:
                        pct = 0
                    status = parts[2] if len(parts) > 2 else "N/A"
                    desc = parts[3] if len(parts) > 3 else ""
                    current_section["projects"].append({
                        "name": name, "pct": pct, "status": status, "desc": desc
                    })

    return sections


def generate(sections, output_path, updated_date):
    """Generate the portfolio HTML."""
    # Compute stats
    active = sum(1 for s in sections for p in s["projects"] if "actif" in p["status"].lower())
    validation = sum(1 for s in sections for p in s["projects"] if "validation" in p["status"].lower())
    proto = sum(1 for s in sections for p in s["projects"] if "proto" in p["status"].lower())
    archive = sum(1 for s in sections for p in s["projects"] if "archive" in p["status"].lower())
    total = sum(len(s["projects"]) for s in sections)

    lines = []
    lines.append('<!DOCTYPE html>')
    lines.append('<html lang="fr">')
    lines.append('<head>')
    lines.append('<meta charset="UTF-8">')
    lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append('<title>&#955; lambda-Section — Portfolio</title>')
    lines.append(f'<style>{CSS}</style>')
    lines.append('</head>')
    lines.append('<body>')
    lines.append('')
    lines.append('<h1>&#955; lambda-Section</h1>')
    lines.append(f'<p class="subtitle">Portfolio — {total} projets &middot; 13 sections &middot; 2026</p>')
    lines.append('')
    lines.append('<div class="stats">')
    lines.append(f'  <div class="stat"><div class="stat-val">{active}</div><div class="stat-label">Actifs</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{validation}</div><div class="stat-label">Validation</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{proto}</div><div class="stat-label">Prototypage</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{archive}</div><div class="stat-label">Archivés</div></div>')
    lines.append('</div>')
    lines.append(f'<p class="meta">Mise à jour : {updated_date} &middot; <a href="https://github.com/Lemniscate-world/kuro-rules/blob/master/Epingle_Projets.md">Source (Epingle_Projets.md)</a> &middot; Généré automatiquement</p>')
    lines.append('')

    for sec in sections:
        lines.append(f'<!-- {sec["name"]} -->')
        lines.append(f'<h2>{sec["name"]}</h2>')
        if sec["theme"]:
            lines.append(f'<p class="section-theme">{sec["theme"]}</p>')
        lines.append('<table>')
        lines.append('<tr><th>Projet</th><th>Progression</th><th>Statut</th><th>Description</th></tr>')
        for p in sec["projects"]:
            badge_cls = status_badge(p["status"])
            bar_cls = progress_class(p["pct"])
            name_cell = p["name"]
            if p["status"].lower().startswith("archive"):
                name_cell = f'<span style="color:var(--muted)">{p["name"]}</span>'
            bar_html = ""
            if p["pct"] > 0 or p["status"].lower() not in ("outil", "archive"):
                bar_html = f'<div class="bar"><div class="bar-fill {bar_cls}" style="width:{p["pct"]}%"></div></div>{p["pct"]}%'
            else:
                bar_html = "&mdash;"
            lines.append(
                f'<tr>'
                f'<td class="proj-name">{name_cell}</td>'
                f'<td>{bar_html}</td>'
                f'<td><span class="badge {badge_cls}">{p["status"]}</span></td>'
                f'<td class="proj-desc">{p["desc"]}</td>'
                f'</tr>'
            )
        lines.append('</table>')
        lines.append('')

    lines.append('<div class="footer">')
    lines.append('  <p>&#955; lambda-Section &copy; 2026 &middot; <a href="https://github.com/Lemniscate-world">GitHub</a> &middot; <a href="https://github.com/Lemniscate-world/kuro-rules/blob/master/Epingle_Projets.md">Source Markdown</a> &middot; Auto-généré</p>')
    lines.append('</div>')
    lines.append('')
    lines.append('</body>')
    lines.append('</html>')

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    output = Path(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--output" else OUTPUT

    if not EPINGLE.exists():
        print(f"ERROR: {EPINGLE} not found")
        sys.exit(1)

    print(f"Parsing {EPINGLE}...")
    sections = parse_epingle(EPINGLE)
    total = sum(len(s["projects"]) for s in sections)
    print(f"  Found {len(sections)} sections, {total} projects")

    today = date.today().strftime("%d %B %Y").replace("June", "Juin").replace("July", "Juillet")
    print(f"Generating {output}...")
    generate(sections, output, today)
    print(f"  Done — {output}")

    # Copy to Lemniscate-world repo
    if output != OUTPUT:
        print(f"  Output is not the default location. Copy manually to {OUTPUT}")
    else:
        print(f"\nNext steps:")
        print(f"  cd {LEMNISCATE}")
        print(f"  git add index.html && git commit -m 'chore: update portfolio from Epingle_Projets.md' && git push")


if __name__ == "__main__":
    main()
