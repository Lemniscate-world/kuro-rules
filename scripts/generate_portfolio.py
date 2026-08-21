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

import re, sys, subprocess, os
from datetime import date
from pathlib import Path

LOCAL_EPINGLE = Path.home() / "Documents" / "kuro-rules" / "Epingle_Projets.md"
LOCAL_OUTPUT = Path.home() / "Documents" / "Lemniscate-world" / "index.html"
LOCAL_README = Path.home() / "Documents" / "Lemniscate-world" / "README.md"
# Truth enrichment: if local repo exists, append last commit to description
TRUTH_ENRICH = True

CSS = """\
  :root {
    --paper: #faf9f5; --ink: #161513; --muted: #6f6c64;
    --hair: #d9d6cc; --zebra: #f1efe8; --hover: #eae7dd;
    --serif: Georgia, 'Times New Roman', serif;
    --mono: ui-monospace, 'Cascadia Mono', 'SF Mono', Consolas, Menlo, monospace;
    --sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; border-radius: 0 !important; }
  body { background: var(--paper); color: var(--ink); font-family: var(--sans); line-height: 1.55; padding: 2.5rem 1.25rem 4rem; max-width: 1060px; margin: 0 auto; }
  .over { font-family: var(--mono); font-size: 0.68rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--muted); }
  h1 { font-family: var(--serif); font-weight: 700; font-size: clamp(2.2rem, 6vw, 3.4rem); letter-spacing: -0.01em; line-height: 1.05; margin: 0.35rem 0 0.4rem; }
  .standfirst { color: var(--muted); font-size: 0.95rem; max-width: 60ch; }
  .rule { border: 0; border-top: 2px solid var(--ink); margin: 1.2rem 0 0; }
  .rule-thin { border: 0; border-top: 1px solid var(--ink); margin-top: 3px; margin-bottom: 1.4rem; }
  .index-nav { font-family: var(--mono); font-size: 0.72rem; color: var(--muted); margin-bottom: 1.6rem; line-height: 2.1; }
  .index-nav a { color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--hair); }
  .index-nav a:hover { border-bottom-color: var(--ink); }
  .index-nav .sep { color: var(--hair); margin: 0 0.45em; }
  .toolbar { display: flex; gap: 1rem; align-items: center; justify-content: space-between; flex-wrap: wrap; margin-bottom: 0.6rem; }
  .colophon { font-family: var(--mono); font-size: 0.68rem; color: var(--muted); }
  .colophon a { color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--hair); }
  .colophon a:hover { border-bottom-color: var(--ink); }
  .filter input { width: min(340px, 100%); padding: 0.45rem 0.6rem; border: 1px solid var(--ink); background: transparent; font-family: var(--mono); font-size: 0.8rem; color: var(--ink); }
  .filter input::placeholder { color: var(--muted); }
  .stats { display: flex; flex-wrap: wrap; border-top: 1px solid var(--ink); border-bottom: 1px solid var(--ink); margin-bottom: 1rem; }
  .stat { padding: 0.7rem 1.4rem 0.7rem 0; margin-right: 1.4rem; border-right: 1px solid var(--hair); }
  .stat:last-child { border-right: 0; margin-right: 0; }
  .stat-val { font-family: var(--mono); font-size: 1.5rem; font-weight: 600; line-height: 1.15; }
  .stat-label { font-family: var(--mono); font-size: 0.62rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); }
  h2 { font-family: var(--serif); font-size: 1.35rem; margin: 2.6rem 0 0.15rem; display: flex; align-items: baseline; gap: 0.6rem; }
  h2 .no { font-family: var(--mono); font-size: 0.75rem; color: var(--muted); letter-spacing: 0.08em; }
  h2 .count { font-family: var(--mono); font-size: 0.72rem; color: var(--muted); font-weight: 400; }
  .section-theme { font-style: italic; color: var(--muted); font-size: 0.85rem; margin-bottom: 0.7rem; }
  table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
  th { font-family: var(--mono); font-weight: 500; text-align: left; font-size: 0.62rem; letter-spacing: 0.16em; text-transform: uppercase; color: var(--muted); padding: 0.45rem 0.75rem; border-bottom: 1px solid var(--ink); }
  td { padding: 0.55rem 0.75rem; border-bottom: 1px solid var(--hair); vertical-align: top; }
  tr:nth-child(even) td { background: var(--zebra); }
  tr:hover td { background: var(--hover); }
  .proj-name { white-space: nowrap; font-weight: 600; }
  .proj-name a { color: var(--ink); text-decoration: none; border-bottom: 1px solid transparent; }
  .proj-name a:hover { border-bottom-color: var(--ink); }
  .proj-desc { color: var(--muted); font-size: 0.8rem; max-width: 420px; }
  .badge { display: inline-block; font-family: var(--mono); font-size: 0.66rem; letter-spacing: 0.1em; text-transform: uppercase; border: 1px solid var(--ink); padding: 0.08rem 0.45rem; white-space: nowrap; background: transparent; color: var(--ink); }
  .bar { display: inline-block; vertical-align: middle; height: 10px; width: 90px; border: 1px solid var(--ink); position: relative; background: transparent; }
  .bar-fill { position: absolute; top: 0; left: 0; bottom: 0; background: var(--ink); }
  .pct { font-family: var(--mono); font-size: 0.72rem; margin-left: 0.5rem; color: var(--muted); }
  .notice { border: 1px solid var(--ink); padding: 1rem 1.2rem; margin-top: 3rem; display: flex; flex-wrap: wrap; gap: 0.8rem; align-items: baseline; justify-content: space-between; }
  .notice strong { font-family: var(--serif); font-size: 1.02rem; }
  .notice p { color: var(--muted); font-size: 0.82rem; max-width: 52ch; }
  .notice a { color: var(--ink); font-family: var(--mono); font-size: 0.78rem; border-bottom: 1px solid var(--ink); text-decoration: none; white-space: nowrap; }
  .footer { margin-top: 3.5rem; padding-top: 0.8rem; border-top: 1px solid var(--ink); display: flex; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; font-family: var(--mono); font-size: 0.68rem; color: var(--muted); }
  .footer a { color: var(--ink); text-decoration: none; border-bottom: 1px solid var(--hair); }
  .footer a:hover { border-bottom-color: var(--ink); }
  a { color: inherit; }
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
    docs = Path(os.environ.get("DOCS_DIR", str(Path.home() / "Documents")))
    if not docs.exists():
        print("  Truth enrich skipped: docs dir not available")
        return None
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
    """URL GitHub. Seuls les repos CONFIRMÉS publics ont un lien direct; le reste -> recherche org (pas de 404)."""
    confirmed_lambda = {"neuraldbg", "astral", "aquarium", "metatron", "sugar", "datalint", "logos", "odin"}
    confirmed_lemni = {"openquant", "charmed", "dissect", "aether", "project-dirac", "charles", "debugreg", "lifetrack", "echox", "hermes", "epure", "helium", "kuroguardian", "sagittarius", "openmind", "neurodose", "flow-regulator", "devdemeterdao", "xp_farming_system", "constant_yield"}
    key = name.lower()
    if key in confirmed_lambda:
        return f"https://github.com/LambdaSection/{name}"
    if key in confirmed_lemni:
        return f"https://github.com/Lemniscate-world/{name}"
    # Non confirmé (privé/innexist) -> recherche org, jamais un lien mort
    return f"https://github.com/search?q={name}+user%3ALemniscate-world+user%3ALambdaSection&type=repositories"


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
    n_sections = len([s for s in sections if len(s["projects"]) > 0])
    lines = []
    lines.append('<!DOCTYPE html>')
    lines.append('<html lang="fr">')
    lines.append('<head>')
    lines.append('<meta charset="UTF-8">')
    lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append(f'<title>&#955; lambda-Section — Registre des projets</title>')
    lines.append(f'<meta name="description" content="Portfolio lambda-Section — {total} projets, {n_sections} sections actives, studio AI / Quant / Biohacking. Registre auto-genere depuis Epingle_Projets.md">')
    lines.append('<meta name="theme-color" content="#faf9f5">')
    lines.append('<meta property="og:title" content="λ lambda-Section — Registre des projets">')
    lines.append(f'<meta property="og:description" content="{total} projets · {n_sections} sections actives · Registre factuel auto-genere">')
    lines.append('<meta property="og:type" content="website">')
    lines.append('<meta property="og:url" content="https://lemniscate-world.github.io/Lemniscate-world/">')
    lines.append(f'<style>{CSS}</style>')
    lines.append('</head>')
    lines.append('<body>')
    lines.append('')
    lines.append('<p class="over">Studio indépendant — AI · Quant · Biohacking</p>')
    lines.append('<h1>&#955; lambda-Section</h1>')
    lines.append(f'<p class="standfirst">Registre des projets — {total} projets en {n_sections} sections. Chaque ligne est vérifiée contre l&rsquo;activité Git réelle, pas contre des intentions.</p>')
    lines.append('')
    lines.append('<hr class="rule">')
    lines.append('<hr class="rule-thin">')
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
    lines.append(f'<p class="colophon" style="margin:0.7rem 0 1.6rem;">Relevé du {updated_date} · <a href="https://github.com/Lemniscate-world/kuro-rules/blob/master/Epingle_Projets.md">source : Epingle_Projets.md</a> · <a href="https://github.com/Lemniscate-world/Lemniscate-world">profil GitHub</a> · <a href="blog/">blog</a> · <a href="sections/">mondes</a></p>')
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
        lines.append('<nav class="index-nav">' + '<span class="sep">/</span>'.join(nav_links) + '</nav>')
        lines.append('')
    lines.append('<div class="toolbar"><div class="filter"><input type="text" id="filter" placeholder="Filtrer par nom, statut, description..." oninput="filterProjects(this.value)"></div><span class="colophon">' + str(total) + ' lignes</span></div>')
    lines.append('')

    sec_no = 0
    for sec in sections:
        if len(sec["projects"]) == 0:
            continue
        sec_no += 1
        anchor = sec.get("anchor", re.sub(r'[^a-zA-Z0-9]+', '-', sec["name"]).strip('-').lower())
        clean_sec_name = sec["name"].replace("&#955;", "λ").replace("&mdash;", "—")
        lines.append(f'<!-- {sec["name"]} -->')
        lines.append(f'<h2 id="{anchor}"><span class="no">{sec_no:02d}</span>{clean_sec_name}<span class="count">· {len(sec["projects"])}</span></h2>')
        if sec["theme"]:
            lines.append(f'<p class="section-theme">{sec["theme"]}</p>')
        lines.append('<table>')
        lines.append('<tr><th>Projet</th><th>Progression</th><th>Statut</th><th>Description</th></tr>')
        for p in sec["projects"]:
            badge_cls = status_badge(p["status"])
            url = project_url(p["name"], sec["name"])
            name_cell = f'<a href="{url}" target="_blank" rel="noopener">{p["name"]}</a>'
            if p["status"].lower().startswith("archive"):
                name_cell = f'<span style="color:var(--muted)"><a href="{url}" target="_blank" rel="noopener" style="color:var(--muted)">{p["name"]}</a></span>'
            bar_html = ""
            if p["pct"] > 0 or p["status"].lower() not in ("outil", "archive"):
                bar_html = f'<span class="bar"><span class="bar-fill" style="width:{p["pct"]}%"></span></span><span class="pct">{p["pct"]}%</span>'
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

    # Discord community block (lien réel requis — pas de placeholder)
    lines.append('<div class="notice" id="discord">')
    lines.append('  <div><strong>Communauté Discord lambda-Section</strong><br><p style="color:var(--muted);font-size:0.82rem;max-width:52ch;">Salons par projet, updates factuelles. Lien d&rsquo;invitation à configurer dans Epingle_Projets.md (clé&nbsp;: discord_invite).</p></div>')
    lines.append('</div>')
    lines.append('')
    # Filter JS
    lines.append('<script>function filterProjects(q){q=q.toLowerCase();document.querySelectorAll("tr[data-search]").forEach(function(r){r.style.display=r.getAttribute("data-search").indexOf(q)>-1?"":"none";});} </script>')
    lines.append('')
    lines.append('<div class="footer">')
    lines.append('  <p>&#955; lambda-Section &copy; 2026</p>')
    lines.append('  <p>Compilé depuis Epingle_Projets.md · <a href="https://github.com/Lemniscate-world/kuro-rules">kuro-rules</a> · <a href="https://github.com/Lemniscate-world">GitHub</a></p>')
    lines.append('</div>')
    lines.append('')
    lines.append('</body>')
    lines.append('</html>')

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Generate per-section worlds (distinct design per S-*)
    generate_section_worlds(sections, updated_date, output_path.parent)


def generate_section_worlds(sections, updated_date, base_dir: Path):
    """Genere un monde par section: sections/s-1/index.html etc. — registre monochrome."""
    taglines = {
        "1": "Reseaux de neurones, causalite, debugging",
        "2": "Trading quantitatif, modeles proba & Markov",
        "3": "Biohacking, focus, corps & esprit",
        "4": "Fintech Afrique, coordination terrain",
        "5": "Aerospatiale, propulsion, Rust",
        "7": "Blockchain Rust, libp2p, DeFi",
        "8": "Algorithmes, structures, visualisation",
        "9": "DevOps, MLOps, automatisation",
        "12": "Physique, Minkowski, maths pures",
        "14": "Beatmaking, art, NFTs",
        "15": "CAD, genie civil, biomimetisme",
        "tiers": "Missions externes & collaborations",
    }
    sections_dir = base_dir / "sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    # Index des mondes
    idx_lines = ['<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">']
    idx_lines.append('<title>lambda-Section — Mondes</title>')
    idx_lines.append(f'<style>{CSS} .world-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:0;border-top:2px solid var(--ink)}} .world-card{{display:block;text-decoration:none;padding:1.1rem 1rem;border-bottom:1px solid var(--hair);border-right:1px solid var(--hair)}}</style>')
    idx_lines.append('</head><body>')
    idx_lines.append('<p class="over">Registre des projets — Index des mondes</p>')
    idx_lines.append('<h1>Mondes</h1>')
    idx_lines.append('<p class="standfirst">Chaque section du studio, avec ses projets et son avancement reel.</p>')
    idx_lines.append('<hr class="rule"><hr class="rule-thin">')
    idx_lines.append(f'<p class="colophon" style="margin-bottom:1.4rem;">Relevé du {updated_date} · <a href="../">retour au registre</a></p>')
    idx_lines.append('<div class="world-grid">')
    for sec in sections:
        if len(sec["projects"]) == 0:
            continue
        m = re.search(r'section-(\d+)', sec["name"].lower())
        sid = m.group(1) if m else ("tiers" if "tiers" in sec["name"].lower() else "0")
        tagline = taglines.get(sid, "")
        # card for index
        proj_count = len(sec["projects"])
        avg = sum(p["pct"] for p in sec["projects"]) // proj_count if proj_count else 0
        clean_name = sec["name"].replace("&#955;", "λ").replace("&mdash;", "—")
        idx_lines.append(f'<a class="world-card" href="s-{sid}/">')
        idx_lines.append(f'  <div style="font-family:var(--mono);font-size:0.68rem;color:var(--muted);letter-spacing:0.14em;">S-{sid.upper()}</div>')
        idx_lines.append(f'  <div style="font-family:var(--serif);font-size:1.15rem;font-weight:700;margin:0.2rem 0 0.3rem;">{clean_name}</div>')
        if tagline:
            idx_lines.append(f'  <div style="color:var(--muted);font-size:0.78rem;font-style:italic;">{tagline}</div>')
        idx_lines.append(f'  <div style="margin-top:0.55rem;font-family:var(--mono);font-size:0.72rem;color:var(--ink);">{proj_count} projets · {avg}% moyen</div>')
        idx_lines.append('</a>')
    idx_lines.append('</div>')
    idx_lines.append('<div class="footer"><p>λ lambda-Section &copy; 2026</p><p><a href="../">Registre</a></p></div></body></html>')
    (sections_dir / "index.html").write_text("\n".join(idx_lines), encoding="utf-8")

    for sec in sections:
        if len(sec["projects"]) == 0:
            continue
        m = re.search(r'section-(\d+)', sec["name"].lower())
        sid = m.group(1) if m else ("tiers" if "tiers" in sec["name"].lower() else "0")
        tagline = taglines.get(sid, "")
        sec_dir = sections_dir / f"s-{sid}"
        sec_dir.mkdir(parents=True, exist_ok=True)
        # Build per-section page
        clean_name = sec["name"].replace("&#955;", "λ").replace("&mdash;", "—")
        slines = []
        slines.append('<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">')
        slines.append(f'<title>{clean_name} — Monde S-{sid}</title>')
        slines.append(f'<style>{CSS}</style>')
        slines.append('</head><body>')
        slines.append(f'<p class="over">Monde S-{sid.upper()}</p>')
        slines.append(f'<h1>{clean_name}</h1>')
        if sec["theme"]:
            slines.append(f'<p class="section-theme">{sec["theme"]}</p>')
        if tagline:
            slines.append(f'<p class="standfirst">{tagline}</p>')
        slines.append('<hr class="rule"><hr class="rule-thin">')
        # Stats for this section
        avg = sum(p["pct"] for p in sec["projects"]) // len(sec["projects"]) if sec["projects"] else 0
        slines.append(f'<div class="stats"><div class="stat"><div class="stat-val">{len(sec["projects"])}</div><div class="stat-label">Projets</div></div>')
        slines.append(f'<div class="stat"><div class="stat-val">{avg}%</div><div class="stat-label">Moyen</div></div>')
        slines.append(f'<div class="stat"><div class="stat-val">{sum(1 for p in sec["projects"] if p["pct"]>=70)}</div><div class="stat-label">70%+</div></div></div>')
        slines.append('<table><tr><th>Projet</th><th>Progression</th><th>Statut</th><th>Description</th></tr>')
        for p in sec["projects"]:
            badge_cls = status_badge(p["status"])
            url = project_url(p["name"], sec["name"])
            name_cell = f'<a href="{url}" target="_blank" rel="noopener">{p["name"]}</a>'
            bar_html = f'<span class="bar"><span class="bar-fill" style="width:{p["pct"]}%"></span></span><span class="pct">{p["pct"]}%</span>'
            searchable = f'{p["name"]} {p["status"]} {p["desc"]}'.replace('"', '&quot;')
            slines.append(f'<tr data-search="{searchable.lower()}"><td class="proj-name">{name_cell}</td><td>{bar_html}</td><td><span class="badge {badge_cls}">{p["status"]}</span></td><td class="proj-desc">{p["desc"]}</td></tr>')
        slines.append('</table>')
        slines.append(f'<p class="colophon" style="margin-top:1.6rem;">Relevé du {updated_date} · <a href="../../">registre complet</a> · <a href="../">mondes</a></p>')
        slines.append('<div class="footer"><p>λ lambda-Section &copy; 2026</p><p>Monde S-' + sid + '</p></div></body></html>')
        (sec_dir / "index.html").write_text("\n".join(slines), encoding="utf-8")
    print(f"  Mondes generes: {len([s for s in sections if len(s['projects'])>0])} sections -> sections/s-*/")


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
