#!/usr/bin/env python3
"""generate_portfolio.py — Generate portfolio HTML from Epingle_Projets.md.

Reads Epingle_Projets.md and produces index.html for the Lemniscate-world site.

Usage:
    python scripts/generate_portfolio.py [--epingle path/to/Epingle_Projets.md] [--output path/to/index.html]

Defaults (local workstation):
    --epingle ~/Documents/kuro-rules/Epingle_Projets.md
    --output  ~/Documents/Lemniscate-world/index.html

On CI (GitHub Actions), paths are relative to checkout directories.
"""

import re, sys, subprocess
from datetime import date
from pathlib import Path

LOCAL_EPINGLE = Path.home() / "Documents" / "kuro-rules" / "Epingle_Projets.md"
LOCAL_OUTPUT = Path.home() / "Documents" / "Lemniscate-world" / "index.html"
LOCAL_README = Path.home() / "Documents" / "Lemniscate-world" / "README.md"
# Truth enrichment: if local repo exists, append last commit to description
TRUTH_ENRICH = True

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
  .meta { color: var(--muted); font-size: 0.75rem; margin-bottom: 1rem; }
  .nav { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1rem; }
  .nav a { font-size: 0.7rem; padding: 0.2rem 0.5rem; border: 1px solid var(--border); border-radius: 999px; color: var(--muted); text-decoration: none; }
  .nav a:hover { border-color: var(--accent); color: var(--accent); }
  .filter-wrap { margin-bottom: 1.2rem; }
  .filter-wrap input { width: 100%; max-width: 340px; padding: 0.5rem 0.7rem; border-radius: 6px; border: 1px solid var(--border); background: var(--card); color: var(--text); font-size: 0.85rem; }
  .filter-wrap input::placeholder { color: var(--muted); }
  .section { margin-bottom: 1.5rem; }
  .section-theme { color: var(--muted); font-style: italic; font-size: 0.8rem; margin-bottom: 0.5rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; padding: 0.5rem 0.75rem; color: var(--muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  td { padding: 0.6rem 0.75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }
  tr:hover { background: rgba(88,166,255,0.04); }
  .proj-name { font-weight: 600; white-space: nowrap; }
  .proj-name a { color: var(--text); text-decoration: none; }
  .proj-name a:hover { color: var(--accent); text-decoration: underline; }
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
  .stats { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .stat { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 0.75rem 1rem; min-width: 90px; text-align: center; }
  .stat-val { font-size: 1.3rem; font-weight: 700; }
  .stat-label { font-size: 0.7rem; color: var(--muted); }
  .discord { background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-top: 2rem; display: flex; flex-wrap: wrap; gap: 1rem; align-items: center; justify-content: space-between; }
  .discord a.btn { background: #5865F2; color: white; padding: 0.5rem 1rem; border-radius: 6px; font-weight: 600; font-size: 0.85rem; text-decoration: none; }
  .discord a.btn:hover { background: #4752C4; }
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
    # Track external section separately
    external_section = None

    for line in text.splitlines():
        # Section header: ## λ-Section-X — Name OR ## Projets Tiers / Externes
        m = re.match(r'^##\s+(λ-Section-\d+.*)', line)
        if m:
            name = m.group(1).replace("λ", "&#955;").replace("—", "&mdash;")
            current_section = {"name": name, "theme": "", "projects": []}
            sections.append(current_section)
            continue
        # External projects header
        if line.strip().startswith("##") and "Projets Tiers" in line:
            external_section = {"name": "Projets Tiers &mdash; Externes (Demeter Labs)", "theme": "Missions externes, non-proprietaire", "projects": []}
            sections.append(external_section)
            current_section = external_section
            continue
        # Skip other H2 (like Livrables, Liens, Reflexion) - reset but don't create section
        if line.startswith("## "):
            current_section = None
            continue

        # Theme line: > Thématique (only for lambda sections)
        if current_section and line.startswith("> ") and not current_section["theme"]:
            # Don't capture blockquotes that are not themes (e.g. R90 note)
            if len(line) < 120:
                current_section["theme"] = line[2:].strip()
            continue

        # Project row: | Name | pct% | Status | Description |  (with or without **)
        if current_section and line.startswith("| "):
            # Skip separator lines
            if re.match(r'^\|\s*-+\s*\|', line):
                continue
            if "| ---" in line or "|---" in line:
                continue
            parts = [p.strip() for p in line.split("|")[1:-1]]
            if len(parts) >= 3:
                name_raw = parts[0].replace("**", "").strip()
                pct_raw = parts[1].strip()
                status_raw = parts[2].strip() if len(parts) > 2 else "N/A"
                # Filter livrables table: pct is like " ?-2" or "Externe" (no % and not dash)
                if not name_raw or name_raw.startswith("-") or name_raw.lower() in ("projet", "section"):
                    continue
                # Must have a valid pct or status indicates project
                is_project = False
                if "%" in pct_raw or pct_raw in ("—", "-", "0", "0%"):
                    is_project = True
                elif pct_raw.isdigit():
                    is_project = True
                else:
                    # External rows have pct like "35%" - already handled, livrables have "?-2" skip
                    # Also handle rows without pct but with status Prototypage/Recherche
                    if status_raw.lower() in ("actif", "validation", "prototypage", "nouveau", "archive", "recherche", "pivot", "outil", "externe"):
                        # For XCAD Epure/Mori without %, still count
                        if name_raw.lower() in ("epure", "mori", "pofs", "bloomdb", "algoritmi", "console"):
                            is_project = True
                if not is_project:
                    continue
                name = name_raw
                pct_str = pct_raw.replace("%", "").replace("—", "0").replace("-", "0").strip()
                # Extract first number
                m_pct = re.search(r'(\d+)', pct_str)
                pct = int(m_pct.group(1)) if m_pct else 0
                status = status_raw if len(parts) > 2 else "N/A"
                desc = parts[3] if len(parts) > 3 else ""
                current_section["projects"].append({
                    "name": name, "pct": pct, "status": status, "desc": desc
                })

    return sections

def truth_enrich(sections):
    """Enrich each project's desc with last commit事实 if local repo exists. Returns dict for footer."""
    if not TRUTH_ENRICH:
        return None
    docs = Path.home() / "Documents"
    enriched = 0
    truth_map = {}
    for sec in sections:
        for p in sec["projects"]:
            proj_path = docs / p["name"]
            # Try case-insensitive find (e.g. NeuralDBG vs neuraldbg)
            if not proj_path.exists():
                # search case-insensitive
                candidates = [d for d in docs.iterdir() if d.is_dir() and d.name.lower() == p["name"].lower()]
                if candidates:
                    proj_path = candidates[0]
                else:
                    continue
            if not (proj_path / ".git").exists():
                continue
            try:
                out = subprocess.run('git log -1 --format="%h|%ad|%s" --date=short', cwd=str(proj_path), capture_output=True, text=True, shell=True, timeout=5)
                if out.returncode == 0 and out.stdout.strip():
                    parts = out.stdout.strip().strip('"').split("|", 2)
                    h, d, msg = (parts + ["", "", ""])[:3]
                    # append factual footer to desc if not already present
                    fact = f" [git:{d} {h} \"{msg[:40]}...\"]"
                    if "git:" not in p["desc"]:
                        p["desc"] = (p["desc"] + fact) if p["desc"] else fact.strip()
                    truth_map[p["name"]] = f"{d} {h}"
                    enriched += 1
            except Exception:
                pass
    return {"enriched": enriched, "map": truth_map}


def project_url(name, section_name=""):
    """Return GitHub URL for a project. Heuristic: S-1* -> LambdaSection, else Lemniscate-world."""
    # External projects -> Demeter or generic
    if "Tiers" in section_name or "Externe" in section_name:
        return f"https://github.com/search?q={name}+org%3ALemniscate-world"
    if "&#955;-Section-1" in section_name or "Section-1" in section_name:
        return f"https://github.com/LambdaSection/{name}"
    # Known LambdaSection projects
    lambda_names = {"neuraldbg", "neuraldbg-engine", "neural-agent", "aladin", "astral", "datalint", "odin", "aquarium", "damon", "metatron", "tokenwise", "prompt2model", "automatons", "onlook", "verbose", "neurodose"}
    if name.lower() in lambda_names:
        return f"https://github.com/LambdaSection/{name}"
    return f"https://github.com/Lemniscate-world/{name}"


def generate(sections, output_path, updated_date):
    """Generate the portfolio HTML."""
    # Compute stats
    total = sum(len(s["projects"]) for s in sections)
    active = sum(1 for s in sections for p in s["projects"] if "actif" in p["status"].lower())
    validation = sum(1 for s in sections for p in s["projects"] if "validation" in p["status"].lower())
    proto = sum(1 for s in sections for p in s["projects"] if "proto" in p["status"].lower())
    archive = sum(1 for s in sections for p in s["projects"] if "archive" in p["status"].lower())
    nouveau = sum(1 for s in sections for p in s["projects"] if "nouveau" in p["status"].lower())
    recherche = sum(1 for s in sections for p in s["projects"] if "recherche" in p["status"].lower() or "pivot" in p["status"].lower())
    # Autres = total - counted (externe/outil etc.)
    autres = total - (active + validation + proto + archive + nouveau + recherche)
    lines = []
    lines.append('<!DOCTYPE html>')
    lines.append('<html lang="fr">')
    lines.append('<head>')
    lines.append('<meta charset="UTF-8">')
    lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append(f'<title>&#955; lambda-Section — Portfolio</title>')
    lines.append(f'<meta name="description" content="Portfolio lambda-Section — {total} projets, {len([s for s in sections if len(s["projects"])>0])} sections actives, studio AI / Quant / Biohacking. Dashboard auto-genere depuis Epingle_Projets.md">')
    lines.append('<meta name="theme-color" content="#0d1117">')
    lines.append('<meta property="og:title" content="λ lambda-Section — Portfolio">')
    lines.append(f'<meta property="og:description" content="{total} projets · {len([s for s in sections if len(s["projects"])>0])} sections actives · Dashboard sombre auto-genere">')
    lines.append('<meta property="og:type" content="website">')
    lines.append('<meta property="og:url" content="https://lemniscate-world.github.io/Lemniscate-world/">')
    lines.append(f'<style>{CSS}</style>')
    lines.append('</head>')
    lines.append('<body>')
    lines.append('')
    lines.append('<h1>&#955; lambda-Section</h1>')
    lines.append(f'<p class="subtitle">Portfolio — {total} projets &middot; {len([s for s in sections if len(s["projects"])>0])} sections actives &middot; 2026</p>')
    lines.append('')
    lines.append('<div class="stats">')
    lines.append(f'  <div class="stat"><div class="stat-val">{active}</div><div class="stat-label">Actifs</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{validation}</div><div class="stat-label">Validation</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{proto}</div><div class="stat-label">Prototypage</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{recherche}</div><div class="stat-label">Recherche</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{nouveau}</div><div class="stat-label">Nouveau</div></div>')
    lines.append(f'  <div class="stat"><div class="stat-val">{archive}</div><div class="stat-label">Archives</div></div>')
    if autres > 0:
        lines.append(f'  <div class="stat"><div class="stat-val">{autres}</div><div class="stat-label">Autres</div></div>')
    lines.append('</div>')
    lines.append(f'<p class="meta">Mise à jour : {updated_date} &middot; <a href="https://github.com/Lemniscate-world/kuro-rules/blob/master/Epingle_Projets.md">Source (Epingle_Projets.md)</a> &middot; Généré automatiquement &middot; <a href="https://github.com/Lemniscate-world/Lemniscate-world">Profil</a></p>')
    lines.append('')
    # Filter + nav
    # Build nav anchors
    nav_links = []
    for sec in sections:
        if len(sec["projects"]) == 0:
            continue
        # anchor id from section name
        anchor = re.sub(r'[^a-zA-Z0-9]+', '-', sec["name"]).strip('-').lower().replace('955-', 'lambda-')
        # Keep original but add id
        sec["anchor"] = anchor
        nav_links.append(f'<a href="#{anchor}">{sec["name"].replace("&#955;", "λ").replace("&mdash;", "—")}</a>')
    if nav_links:
        lines.append('<nav class="nav">' + "".join(nav_links) + '</nav>')
        lines.append('')
    lines.append('<div class="filter-wrap"><input type="text" id="filter" placeholder="Filtrer par nom, statut, description..." oninput="filterProjects(this.value)"></div>')
    lines.append('')

    for sec in sections:
        if len(sec["projects"]) == 0:
            continue
        anchor = sec.get("anchor", re.sub(r'[^a-zA-Z0-9]+', '-', sec["name"]).strip('-').lower())
        lines.append(f'<!-- {sec["name"]} -->')
        lines.append(f'<h2 id="{anchor}">{sec["name"]}</h2>')
        if sec["theme"]:
            lines.append(f'<p class="section-theme">{sec["theme"]}</p>')
        lines.append('<table>')
        lines.append('<tr><th>Projet</th><th>Progression</th><th>Statut</th><th>Description</th></tr>')
        for p in sec["projects"]:
            badge_cls = status_badge(p["status"])
            bar_cls = progress_class(p["pct"])
            url = project_url(p["name"], sec["name"])
            name_cell = f'<a href="{url}" target="_blank" rel="noopener">{p["name"]}</a>'
            if p["status"].lower().startswith("archive"):
                name_cell = f'<span style="color:var(--muted)"><a href="{url}" target="_blank" rel="noopener" style="color:var(--muted)">{p["name"]}</a></span>'
            bar_html = ""
            if p["pct"] > 0 or p["status"].lower() not in ("outil", "archive"):
                bar_html = f'<div class="bar"><div class="bar-fill {bar_cls}" style="width:{p["pct"]}%"></div></div>{p["pct"]}%'
            else:
                bar_html = "&mdash;"
            # Row searchable text
            searchable = f'{p["name"]} {p["status"]} {p["desc"]}'.replace('"', '&quot;')
            lines.append(
                f'<tr data-search="{searchable.lower()}">'
                f'<td class="proj-name">{name_cell}</td>'
                f'<td>{bar_html}</td>'
                f'<td><span class="badge {badge_cls}">{p["status"]}</span></td>'
                f'<td class="proj-desc">{p["desc"]}</td>'
                f'</tr>'
            )
        lines.append('</table>')
        lines.append('')

    # Discord community block
    lines.append('<div class="discord" id="discord">')
    lines.append('  <div><strong>Communaute Discord lambda-Section</strong><br><span style="color:var(--muted);font-size:0.8rem;">Messages par projet, updates, entraide. Tes messages Discord peuvent alimenter Epingle -> portfolio auto.</span></div>')
    lines.append('  <a class="btn" href="https://discord.gg/lambda-section" target="_blank" rel="noopener">Rejoindre Discord</a>')
    lines.append('</div>')
    lines.append('<p style="color:var(--muted);font-size:0.75rem;margin-top:0.5rem;">Astuce: Exporte tes messages Discord (par salon/projet) -> colle dans <code>Epingle_Projets.md</code> -> <code>generate_portfolio.py</code> sync auto README + portfolio.</p>')
    lines.append('')
    # Filter JS
    lines.append('<script>function filterProjects(q){q=q.toLowerCase();document.querySelectorAll("tr[data-search]").forEach(function(r){r.style.display=r.getAttribute("data-search").indexOf(q)>-1?"":"none";});} </script>')
    lines.append('')
    lines.append('<div class="footer">')
    lines.append('  <p>&#955; lambda-Section &copy; 2026 &middot; <a href="https://github.com/Lemniscate-world">GitHub</a> &middot; <a href="https://github.com/Lemniscate-world/kuro-rules/blob/master/Epingle_Projets.md">Source Markdown</a> &middot; Auto-généré</p>')
    lines.append('</div>')
    lines.append('')
    lines.append('</body>')
    lines.append('</html>')

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def sync_readme(sections):
    """Auto-sync README.md profile header + percentages from Epingle (R51/R80).

    - Header: 31 projets / 15 sections counts
    - Architecture table: every 'Name (X%)' replaced with Epingle pct if name exists
    - Focus badges: '**[X% - Status]**' updated per project
    Preserves curation (does not add/remove projects), only updates numbers.
    """
    readme_path = LOCAL_README
    if not readme_path.exists():
        print(f"  README not found: {readme_path} — skipping")
        return
    text = readme_path.read_text(encoding="utf-8")
    original = text
    total = sum(len(s["projects"]) for s in sections)
    num_sections = len(sections)

    # Active sections for header (match portfolio)
    active_sections = len([s for s in sections if len(s["projects"]) > 0])
    # Build global map (max pct) for Focus badges, and per-section maps for Architecture
    proj_map = {}
    section_maps = {}  # key: normalized section id -> {project_lower -> pct}
    for s in sections:
        sec_key = s["name"].lower()
        # Extract section number e.g. "1", "4", "15", "tiers"
        m_sec = re.search(r'section-(\d+)', sec_key)
        sec_id = m_sec.group(1) if m_sec else ("tiers" if "tiers" in sec_key else sec_key)
        if sec_id not in section_maps:
            section_maps[sec_id] = {}
        for p in s["projects"]:
            key = p["name"].lower().strip()
            existing = proj_map.get(key)
            if existing is None or p["pct"] > existing[0]:
                proj_map[key] = (p["pct"], p["status"])
            # per-section
            sec_existing = section_maps[sec_id].get(key)
            if sec_existing is None or p["pct"] > sec_existing[0]:
                section_maps[sec_id][key] = (p["pct"], p["status"])
    # Map README S-1b/c -> S-1, S-15 etc.
    def sec_id_for_readme_line(line):
        m = re.search(r'\*\*S-(\d+)([a-z]?)', line)
        if m:
            base = m.group(1)
            # S-1b/c -> S-1
            if base == "1":
                return "1"
            return base
        if "Tiers" in line or "Externe" in line:
            return "tiers"
        return None

    # 1. Header counts: > **31 projets · 15 sections -> use active_sections
    text = re.sub(
        r'> \*\*\d+\s+projets\s+·\s+\d+\s+sections',
        f'> **{total} projets \u00b7 {active_sections} sections',
        text
    )

    # 2. Architecture table + any 'Name (X% ...)' occurrence - per-section aware for Epure duplicate
    # Process line-by-line to keep section context
    arch_lines = text.splitlines()
    new_arch_lines = []
    for line in arch_lines:
        if line.startswith("| **S-") and "(" in line and "%" in line:
            sec_id = sec_id_for_readme_line(line)
            sec_map = section_maps.get(sec_id, proj_map) if sec_id else proj_map
            def repl_arch_per(m):
                name = m.group(1)
                key = name.lower()
                # Prefer per-section map, fallback global
                entry = sec_map.get(key) or proj_map.get(key)
                if entry:
                    pct, _ = entry
                    suffix = m.group(3)
                    return f'{name} ({pct}%{suffix})'
                return m.group(0)
            line = re.sub(r'([A-Za-z0-9/_-]+)\s*\((\d+)%([^)]*)\)', repl_arch_per, line)
        new_arch_lines.append(line)
    text = "\n".join(new_arch_lines)
    # Also handle any remaining Name (X%) outside architecture table (fallback global)
    def repl_arch_global(m):
        name = m.group(1)
        key = name.lower()
        if key in proj_map:
            pct, _ = proj_map[key]
            suffix = m.group(3)
            return f'{name} ({pct}%{suffix})'
        return m.group(0)
    # Only for lines not already processed? Apply to whole text but per-section already handled, this is safe fallback for other occurrences
    # We skip to avoid double-processing architecture lines, so only apply to lines not starting with | **S-
    final_lines = []
    for line in text.splitlines():
        if not line.startswith("| **S-"):
            line = re.sub(r'([A-Za-z0-9/_-]+)\s*\((\d+)%([^)]*)\)', repl_arch_global, line)
        final_lines.append(line)
    text = "\n".join(final_lines)

    # 3. Focus badges: line-by-line to avoid DOTALL cross-section bug (AEther -> OpenQuant)
    lines = text.splitlines()
    fixed_lines = []
    for line in lines:
        if '](' in line and '% -' in line and '**[' in line:
            m_proj = re.search(r'\[([^\]]+)\]\(https://github\.com', line)
            if m_proj:
                key = m_proj.group(1).lower().strip()
                if key in proj_map:
                    pct, _ = proj_map[key]
                    # Replace only the badge percentage on this line (first occurrence)
                    line = re.sub(r'\[\d+%\s*-\s*', f'[{pct}% - ', line, count=1)
        fixed_lines.append(line)
    text = "\n".join(fixed_lines)

    if text != original:
        readme_path.write_text(text, encoding="utf-8")
        print(f"  README synced: {total} projets, {num_sections} sections, {len(proj_map)} projects mapped")
    else:
        print(f"  README already in sync")


def main():
    args = sys.argv[1:]
    epingle = LOCAL_EPINGLE
    output = LOCAL_OUTPUT

    i = 0
    while i < len(args):
        if args[i] == "--epingle" and i + 1 < len(args):
            epingle = Path(args[i + 1])
            i += 2
        elif args[i] == "--output" and i + 1 < len(args):
            output = Path(args[i + 1])
            i += 2
        else:
            i += 1

    if not epingle.exists():
        print(f"ERROR: {epingle} not found")
        print("  Usage: python generate_portfolio.py [--epingle path] [--output path]")
        sys.exit(1)

    print(f"Parsing {epingle}...")
    sections = parse_epingle(epingle)
    total = sum(len(s["projects"]) for s in sections)
    print(f"  Found {len(sections)} sections, {total} projects")

    # Truth enrichment before generation (facts from git log)
    truth_info = truth_enrich(sections)
    if truth_info:
        print(f"  Truth enriched: {truth_info['enriched']} projets avec git fact")

    today = date.today().strftime("%d %B %Y").replace("January","Janvier").replace("February","Fevrier").replace("March","Mars").replace("April","Avril").replace("May","Mai").replace("June", "Juin").replace("July", "Juillet").replace("August","Aout").replace("September","Septembre").replace("October","Octobre").replace("November","Novembre").replace("December","Decembre")
    print(f"Generating {output}...")
    generate(sections, output, today)
    print(f"  Done — {output}")

    # Auto-sync profile README (R51/R80) if using default paths
    if output == LOCAL_OUTPUT:
        print(f"Syncing {LOCAL_README} from Epingle...")
        sync_readme(sections)

    if output == LOCAL_OUTPUT:
        print(f"\nNext: cd ~/Documents/Lemniscate-world && git add index.html README.md && git commit -m 'sync' && git push")


if __name__ == "__main__":
    main()
