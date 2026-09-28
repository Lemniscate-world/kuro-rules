#!/usr/bin/env python3
"""gen_x_posts.py — Drafts X quotidiens top-velocite, OWNED-only (R94-v2).

Pipeline Kuro (fait partie du robot unique kuro.yml, pas un 2e workflow) :
  Epingle (parser unique generate_portfolio.parse_epingle + supplement Laboratoire)
  + git log 7j/30j (velocite) + git remote -v (ownership R87)
  -> outputs/x_post_YYYY-MM-DD-{projet}.md (drafts, DRY-RUN par defaut)
  -> outputs/x_post_YYYY-MM-DD.md (hub, compatible R94 historique)

Regles :
- Zero dependance (stdlib uniquement), cross-platform (pathlib, R93).
- Logs console ASCII-safe (emojis supprimes, accents gardes) — R93 + R9.
- Un seul parser Epingle, jamais de regex maison sur les sections λ (vision Kuro).
- EXTERNAL / UNKNOWN / statuts non Actif-Validation : jamais de compte dedie.
- Draft <= 280 caracteres, 1 metrique chiffree, 1 livrable concret,
  jamais de promesse future, ton technique factuel (R94).
- Ne poste RIEN : full-auto = ecriture du draft + commit Kuro uniquement.
  La publication X reste manuelle tant que 0 leak sur 14j (R94-v2 gate).
- CI-safe : docs absents, Epingle vide ou zero eligible -> exit 0, jamais de crash.

Usage :
  python scripts/gen_x_posts.py --dry-run [--top 3]
  python scripts/gen_x_posts.py --apply [--top 3] [--epingle ...] [--docs ...]
"""
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
EPINGLE = KURORULES / "Epingle_Projets.md"
OUTPUTS = KURORULES / "outputs"

GIT_TIMEOUT = 15
FRESH_DAYS = 30  # dernier commit au-dela -> pas de post auto

OWNED_MARKERS = (
    "github.com/Lemniscate-world/",
    "github.com/Lemniscate-SHA-256/",
    "github.com/pbakaus/",
    "github.com/LambdaSection/",
    # Orgs satellites lambda-Section (un repo = une org par section) :
    # quantifiees via `git remote -v` sur ~/Documents le 2026-09-21.
    "github.com/Quant-Search/",  # λ-2 OpenQuant, Console
    "github.com/AI8-Algorithm-Intelligence-Section-8/",  # λ-8 Dissect, BloomDB
    "github.com/Hackin-Life-X/",  # λ-3 LifeTrack eco, EchoX
    "github.com/N-Hypatia/",  # λ-12 AEther, Project-Dirac
    "github.com/EpureCAD/",  # λ-15 Epure
    "github.com/HeliumXChain/",  # λ-7 Helium
    "github.com/Rare-Sagittarius/",  # λ-9 Sagittarius
)
EXTERNAL_MARKERS = ("github.com/Demeter-Financial-Labs/",)

ELIGIBLE_STATUS = ("actif", "validation")

# --- Stratégies de post (R94-v2) : que révéler / ne JAMAIS révéler ---
# "never" = termes bloquants (lint, insensible à la casse, mots entiers).
# generic_fallback = True -> draft générique auto (type + chiffres process uniquement).
# Couche 1 (universelle, TOUS projets) : voir UNIVERSAL_PATTERNS ci-dessous.
POSTING_STRATEGIES = {
    # Trading : processus OK, alpha/edges/stats jamais (l'edge, c'est le business).
    "openquant": {
        "reveal": ["commits", "tests", "gates", "coverage", "processus"],
        "never": ["edge", "alpha", "signal", "sharpe", "sortino", "calmar",
                  "drawdown", "pnl", "p&l", "profit", "harvey", "leverage",
                  "sizing", "weight", "threshold", "t-stat", "z-score",
                  "p-value", "hit-rate", "win-rate", "cagr", "backtest",
                  "contrefactuel", "contrefactuelle", "counterfactual",
                  "sidak", "bonferroni", "holm", "hochberg", "fdr",
                  "benjamini", "white", "hansen", "reality check",
                  "deflated sharpe", "probabilistic sharpe", "haircut",
                  "overfit", "data mining", "data-mining", "p-hacking",
                  "p-hack", "walk-forward", "walk forward", "in-sample",
                  "oos", "bootstrap", "bootstrapping", "seuil"],
        "generic_fallback": True,
    },
    # Moteur proprio (R94 §1 : heuristiques causales et implémentation jamais).
    "neuraldbg-engine": {
        "reveal": ["tests", "contrats", "versions"],
        "never": ["heuristique", "propriétaire", "pondération", "seuil interne"],
        "generic_fallback": True,
    },
    # Données clients assurance : jamais de dossier, personne ou montant.
    "forma": {
        "reveal": ["version", "tests", "commits"],
        "never": ["assuré", "assure", "bénéficiaire", "indemnisation",
                  "indemnité", "dossier n", "sinistre n"],
        "generic_fallback": True,
    },
    # Données de santé personnelles : jamais de mesure ni traitement.
    "lifetrack": {
        "reveal": ["version", "tests", "fonctionnalités"],
        "never": ["ordonnance", "médicament", "médicaments", "dose",
                  "thérapie", "diagnostic", "traitement"],
        "generic_fallback": True,
    },
    # Clés et secrets chaines : jamais.
    "helium": {
        "reveal": ["version", "tests", "docs", "releases"],
        "never": ["seed", "mnemonic", "clé privée", "cle privee",
                  "keystore", "passphrase"],
        "generic_fallback": True,
    },
    # Recherche non publiée : jamais de piste de publication.
    "horcruxe labs": {
        "reveal": ["commits", "tests", "progrès"],
        "never": ["soumission", "manuscrit", "relecteur", "confidentiel"],
        "generic_fallback": True,
    },
}
DEFAULT_STRATEGY = {"reveal": ["commits", "tests", "livrables"],
                    "never": [], "generic_fallback": True}

# Couche universelle : motifs techniques interdits dans TOUT post, tout projet.
UNIVERSAL_PATTERNS = [
    ("email", r"[\w.+-]+@[\w-]+\.[\w.]+"),
    ("secret", r"(?i)(api[_-]?key|token|secret|password|passwd|pwd)\s*[:=]\s*\S+"),
    ("chemin-local", r"(?:[A-Za-z]:\\|/home/|/Users/)[^\s]*"),
    ("blob-secret", r"\b[a-f0-9]{32,}\b"),
    ("telephone", r"\+\d{2,3}(?:[\s.\-]?\d){6,}"),
    ("montant", r"(?:[$€]\s?\d[\d\s.,]*\d|\d[\d\s.,]*\s?[$€])"),
    ("ip-privee", r"\b(?:10|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b"),
]

# Termes muselés à chaud via `post_brain.py flag` (additif, jamais destructif).
try:
    from post_brain import apply_overrides as _apply_overrides
    _apply_overrides(POSTING_STRATEGIES)
except Exception:
    pass

TYPE_WORDS = {"feat": "fonctionnalités", "fix": "correctifs", "test": "tests",
              "docs": "documentation", "ci": "CI", "build": "build",
              "chore": "maintenance", "refactor": "refactorisation",
              "perf": "optimisations"}

# Verbes d'annonce : un post explique, il ne recopie pas un commit.
TYPE_VERBS = {"feat": "Nouveau", "fix": "Correctif", "test": "Tests",
              "docs": "Docs", "ci": "CI", "build": "Build",
              "chore": "Maintenance", "refactor": "Refonte", "perf": "Perf"}

# Contexte une-ligne par projet (ce que le lecteur doit comprendre d'emblée).
TAGLINES = {
    "neuraldbg": "debug causal PyTorch",
    "neuraldbg-engine": "moteur causal",
    "neural-agent": "agent auto-correcteur",
    "neuralprune": "diagnostic de pruning",
    "aladin": "recherche LLM",
    "prompt2model": "génération de modèles",
    "metatron-clean": "debugger IA",
    "oblivion": "IDE à 0 FCFA",
    "openquant": "trading quantitatif",
    "flow-regulator": "productivité",
    "lifetrack": "tracker d'habitudes",
    "hermes": "livraisons à Lomé",
    "g&s solutions": "fintech",
    "epure": "ingénierie augmentée IA",
    "forma": "assurance sinistres",
    "helium": "blockchain Rust",
    "sagittarius": "MLOps",
    "kuroguardian": "surveillance Kuro",
    "openmind": "journaling IA",
    "horcruxe labs": "labo de recherche",
    "russel-agent": "agent à mémoire",
    "solaris": "critique physique",
    "galt-flatcoin-concept": "flatcoin DeFi",
    "neurodose": "santé cognitive",
    "saasx": "SaaS",
    "opencmo": "marketing IA",
    "devipro": "devis artisans",
    "bodydouble": "focus à deux",
    "driftscape": "soundscape adaptatif",
    "dissect": "audit d'agents IA",
}


# Commits sans valeur publique : jamais la base d'un post (ni X ni Discord).
TRIVIA_PATTERNS = [
    r"(?i)^chore(\(pre-commit\)|: fix pre-commit)",
    r"(?i)^merge\b",
    r"(?i)\bbump\b",
    r"(?i)^v?\d+\.\d+(\.\d+)?\s*:?\s*$",
    r"(?i)^(fix|docs|style)(\([^)]*\))?:\s*(typo|orthographe|faute)",
    r"(?i)(au lieu de|instead of)",
]
# Types porteurs de sens public. fix/docs/test seuls = cas par cas via trivia.
MEANINGFUL_TYPES = ("feat", "perf", "refactor", "release")

# Verbes d'action anglais : un post EN raconte avec des verbes forts.
EN_ACTION_VERBS = {"feat": "Shipped", "fix": "Fixed", "perf": "Sped up",
                   "refactor": "Reworked", "release": "Released"}

# Marqueurs de français (anti-franglais dans les posts EN).
FRENCH_MARKERS = re.compile(
    r"[àâäéèêëîïôöùûüç]|"
    r"\b(les|des|une|avec|dans|notre|votre|leurs|cette|aux|sont|pas|voici|chez)\b",
    re.IGNORECASE)


def looks_french(text):
    return bool(FRENCH_MARKERS.search(text or ""))


def collect_week_subjects(project_path, days=7, limit=30):
    """Sujets de commits des N derniers jours (git log, jamais de crash)."""
    if not (project_path / ".git").is_dir():
        return []
    out = run('git log --since="%d days ago" --format="%%s"' % days, cwd=project_path)
    return [l.strip() for l in (out or "").splitlines() if l.strip()][:limit]


def is_trivia(subject):
    return any(re.search(p, subject or "") for p in TRIVIA_PATTERNS)


# Liens repo vérifiés vivants via `gh api repos/<org>/<nom>` le 2026-09-21.
# Pas de ligne = pas de lien (jamais de lien mort ou deviné).
# Note coûts : lien = 0,20 $/post en API X directe, 0 $ via Buffer (forfait).
PROJECT_LINKS = {
    "neuraldbg": "https://github.com/LambdaSection/NeuralDBG",
    "neuraldbg-engine": "https://github.com/LambdaSection/NeuralDBG",
    "neural-agent": "https://github.com/LambdaSection/Neural-Agent",
    "neuralprune": "https://github.com/LambdaSection/NeuralPrune",
    "lifetrack": "https://github.com/Lemniscate-world/LifeTrack",
    "openquant": "https://github.com/Quant-Search/OpenQuant",
    "helium": "https://github.com/HeliumXChain/Helium",
    "horcruxe labs": "https://github.com/Lemniscate-world/Horcruxe-Labs",
    "forma": "https://github.com/Lemniscate-world/forma",
    "epure": "https://github.com/EpureCAD/Epure-Architectural",
    "metatron-clean": "https://github.com/LambdaSection/Metatron",
    "solaris": "https://github.com/Lemniscate-world/SOLARIS",
    "dissect": "https://github.com/AI8-Algorithm-Intelligence-Section-8/Dissect",
    "neurodose": "https://github.com/LambdaSection/NeuroDose",
    "sagittarius": "https://github.com/Rare-Sagittarius/Sagittarius",
    "aquarium": "https://github.com/LambdaSection/Aquarium",
    "astral": "https://github.com/LambdaSection/Astral",
    "tokenwise": "https://github.com/LambdaSection/TokenWise",
    "echox": "https://github.com/AI8-Algorithm-Intelligence-Section-8/EchoX",
}

URL_RE = re.compile(r"https?://\S+")


def project_link(name):
    url = PROJECT_LINKS.get((name or "").lower(), "")
    if url.startswith("https://github.com/"):
        return url
    return ""


def x_len(text):
    """Longueur façon X : chaque URL compte 23 car (t.co)."""
    return len(URL_RE.sub("X" * 23, text or ""))


# Présentations une-ligne (français formel, accessible non-expert).
# Source : MARKETING_MEMORY/helium-post-format-formel.md + Epingle.
# Repli : première phrase de la description Epingle.
PRESENTATIONS = {
    "helium": "réseau privé de partage de ressources de calcul (GPU/RAM) pour l'IA",
    "openquant": "recherche quantitative : des systèmes de trading validés statistiquement",
    "lifetrack": "suivi d'habitudes sur desktop, 100 % local et privé",
    "neuraldbg": "débogueur qui explique les échecs d'entraînement PyTorch",
    "neuraldbg-engine": "moteur d'analyse causale pour l'entraînement",
    "forma": "traitement automatisé des dossiers sinistres pour l'assurance",
    "horcruxe labs": "laboratoire de recherche personnelle",
    "oblivion": "environnement de développement sobre en ressources",
    "epure": "ingénierie assistée par IA",
    "neural-agent": "agent qui corrige les entraînements tout seul",
    "metatron-clean": "débogueur qui explique les erreurs en langage clair",
}

# Présentations anglaises (compte hub LambdaSection : audience tech anglophone).
PRESENTATIONS_EN = {
    "helium": "private GPU/RAM sharing network for AI",
    "openquant": "statistically validated quant trading research",
    "lifetrack": "private, local-first habit tracker",
    "neuraldbg": "causal debugger for PyTorch training",
    "neuraldbg-engine": "causal analysis engine for training",
    "forma": "AI-powered insurance claims processing",
    "horcruxe labs": "personal research lab",
    "oblivion": "resource-light dev environment",
    "epure": "AI-augmented engineering",
    "neural-agent": "self-correcting training agent",
    "metatron-clean": "debugger that explains errors in plain English",
}

STATUS_EN = {"actif": "Active", "en pause": "Paused", "prototypage": "Prototyping",
             "validation": "Validating", "recherche": "Researching", "archive": "Archived",
             "nouveau": "New", "pivot": "Pivoted", "outil": "Tooling", "externe": "External"}

TYPE_VERBS_EN = {"feat": "New", "fix": "Fixed", "test": "Tests", "docs": "Docs",
                 "ci": "CI", "build": "Build", "chore": "Maintenance",
                 "refactor": "Refactor", "perf": "Perf"}


def presentation_for(name, desc="", lang="fr"):
    if lang == "en":
        hit = PRESENTATIONS_EN.get((name or "").lower(), "")
        if hit:
            return hit
        d = (desc or "").strip()
        if d:
            first = re.split(r"[.!?…]\s", d, maxsplit=1)[0][:90]
            return first[0].lower() + first[1:] if first else ""
        return "studio project"
    hit = PRESENTATIONS.get((name or "").lower(), "")
    if hit:
        return hit
    d = (desc or "").strip()
    if d:
        first = re.split(r"[.!?…]\s", d, maxsplit=1)[0][:90]
        return first[0].lower() + first[1:] if first else ""
    return "projet du studio"


def next_step(repo_path):
    """Prochaine étape depuis SESSION_SUMMARY (1re puce trouvée), sinon repli honnête."""
    try:
        if not repo_path:
            return "Poursuite des travaux en cours."
        text = (Path(repo_path) / "SESSION_SUMMARY.md").read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return "Poursuite des travaux en cours."
    in_next = False
    for line in text.splitlines():
        low = line.lower()
        if re.match(r"^#{1,4}\s*(prochaine|next|à faire|todo)", low):
            in_next = True
            continue
        if in_next:
            m = re.match(r"\s*[-*]\s+(.+)", line)
            if m and len(m.group(1).strip()) > 10:
                return sanitize(m.group(1).strip())[:140]
            if line.startswith("#"):
                break
    return "Poursuite des travaux en cours."


def tagline_for(name):
    return TAGLINES.get((name or "").lower(), "")


def _iter_themes(project_path, days=7, limit=3):
    """Générateur interne : (type_conventional, sujet_humanisé)."""
    seen = set()
    count = 0
    for subj in collect_week_subjects(project_path, days=days):
        if is_trivia(subj):
            continue
        m = re.match(r"\s*([a-z]+)(?:\([^)]*\))?\s*:\s*(.+)", subj, re.DOTALL)
        if m:
            kind, subject = m.group(1).lower(), m.group(2).strip()
            if kind in ("docs", "test", "ci", "build", "chore", "style"):
                continue  # process interne, pas une annonce
            if kind not in MEANINGFUL_TYPES and kind != "fix":
                continue
        else:
            kind, subject = "", subj.strip()
            if len(subject) < 40:
                continue
        key = subject.lower()
        if key in seen:
            continue
        seen.add(key)
        count += 1
        yield kind, _capitalize(subject[:80])
        if count >= limit:
            break


def week_themes(project_path, days=7, limit=3):
    """0-3 thèmes publiables de la semaine (humanisés). Vide = rien à annoncer."""
    return [s for _, s in _iter_themes(project_path, days, limit)]


def theme_verbs(project_path, days=7, limit=3):
    """Verbes d'action EN parallèles aux thèmes (même sélection, même ordre)."""
    return [EN_ACTION_VERBS.get(kind, "") for kind, _ in _iter_themes(project_path, days, limit)]


def split_conventional(msg, lang="fr"):
    """'feat(scope): sujet' -> ('Nouveau'/'New', 'sujet'). Sans prefixe -> (None, msg)."""
    m = re.match(r"\s*([a-z]+)(?:\([^)]*\))?\s*:\s*(.+)", msg or "", re.DOTALL)
    if not m:
        return None, (msg or "").strip()
    verbs = TYPE_VERBS_EN if (lang or "fr").lower() == "en" else TYPE_VERBS
    return verbs.get(m.group(1).lower()), m.group(2).strip()


def _capitalize(subject):
    subject = re.sub(r"\s+", " ", subject or "").strip().rstrip(".")
    if not subject:
        return "Avancées"
    return subject[0].upper() + subject[1:]


def strategy_for(name):
    return POSTING_STRATEGIES.get((name or "").lower(), DEFAULT_STRATEGY)


def lint_post(name, text):
    """Couche 1 universelle + couche 2 stratégie projet. Liste des problèmes (vide = OK)."""
    found = []
    for label, pattern in UNIVERSAL_PATTERNS:
        if re.search(pattern, text or ""):
            found.append(label)
    for term in strategy_for(name).get("never", []):
        if re.search(r"(?i)(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(term), text or ""):
            if term not in found:
                found.append(term)
    return found


def generic_type_word(msg):
    m = re.match(r"\s*([a-z]+)", (msg or "").lower())
    return TYPE_WORDS.get(m.group(1) if m else "", "avancées")


def format_post_safe(name, pct, status, facts, lang="fr"):
    """Draft sûr : garde le max de thèmes qui passent le lint, générique sinon, None si inaffichable."""
    en = (lang or "fr").lower() == "en"
    clean = dict(facts)
    clean["themes"] = [t for t in (facts.get("themes") or [])
                       if not lint_post(name, t)]
    if clean["themes"]:
        normal = format_post(name, pct, status, clean, lang=lang)
        if not lint_post(name, normal):
            return normal
    elif not (facts.get("themes") or []):
        normal = format_post(name, pct, status, facts, lang=lang)
        if not lint_post(name, normal):
            return normal
    if not strategy_for(name).get("generic_fallback", True):
        return None
    tags = tags_for(name)
    if en:
        metric = "%d commits (30d), %d (7d)" % (facts.get("c30", 0), facts.get("c7", 0))
        status_out, ongoing = STATUS_EN.get((status or "").lower(), status), "in progress"
    else:
        metric = "%d commits 30j, %d à 7j" % (facts.get("c30", 0), facts.get("c7", 0))
        status_out, ongoing = status, "en cours"
    try:
        pct_n = int(pct)
    except Exception:
        pct_n = 0
    ctx = presentation_for(name, (facts.get("project_desc") or ""), lang="en" if en else "fr")
    action = generic_type_word(facts.get("msg", ""))
    link = project_link(name)
    if ctx:
        line1 = "%s (%s): %s %s." % (name, ctx, action, ongoing)
    else:
        line1 = "%s: %s %s." % (name, action, ongoing)
    parts = ["%s\n\n%s, %d%% %s." % (line1, metric, pct_n, status_out)]
    if link:
        parts.append(link)
    parts.append(" ".join(tags[:3]))
    post = "\n\n".join(parts)
    if x_len(post) > 280:
        parts = ["%s\n\n%s, %d%% %s." % (line1, metric, pct_n, status_out)]
        parts.append(" ".join(tags[:3]))
        post = "\n\n".join(parts)
    if lint_post(name, post):
        return None
    return post


def format_long(name, pct, status, facts, desc=""):
    """Version détaillée façon fiche MARKETING (présentation + travaux + étape + caption).
    Jamais d'étape future inventée : SESSION_SUMMARY ou repli honnête. ≤1900 car."""
    short = format_post_safe(name, pct, status, facts) or "Contenu sensible — diffusion restreinte."
    presentation = presentation_for(name, desc or facts.get("project_desc", ""))
    lines = ["**%s** — %s%% %s" % (name, pct, status)]
    lines.append("%s est %s." % (name, presentation))
    lines.append("")
    lines.append("Travaux réalisés :")
    themes = [t for t in (facts.get("themes") or []) if t]
    if themes:
        for i, t in enumerate(themes[:5], 1):
            lines.append("%d. %s." % (i, t.rstrip(".")))
    else:
        lines.append("1. %s." % (_capitalize(
            sanitize(facts.get("msg", "maintenance")) or "maintenance").rstrip(".")))
    lines.append("")
    lines.append("Prochaine étape : %s" % (facts.get("next") or "Poursuite des travaux en cours."))
    lines.append("")
    link = project_link(name)
    if link:
        lines.append("Repo : %s" % link)
    lines.append("Caption X :")
    lines.append(short)
    return "\n".join(lines)[:1900]

# Dossiers dont le nom differe de l'entree Epingle (ne PAS dupliquer la ligne).
REPO_ALIASES = {
    "kuroguardian": ["kuro"],  # daemon local ~/Documents/kuro
}

HASHTAGS = {
    "neuraldbg": ("#NeuralDBG", "#ML", "#DeepLearning"),
    "neuraldbg-engine": ("#NeuralDBG", "#ML", "#Inference"),
    "neural-agent": ("#NeuralAgent", "#LLM", "#Agents"),
    "neuralprune": ("#NeuralPrune", "#ML", "#Pruning"),
    "lifetrack": ("#LifeTrack", "#Tauri", "#Health"),
    "openquant": ("#OpenQuant", "#Quant", "#Trading"),
    "helium": ("#Helium", "#Rust", "#Blockchain"),
    "horcruxe labs": ("#HorcruxeLabs", "#Research", "#Memory"),
    "russel-agent": ("#RusselAgent", "#Agents", "#Memory"),
    "forma": ("#Forma", "#InsurTech", "#AI"),
    "epure": ("#Epure", "#CAD", "#Engineering"),
    "metatron-clean": ("#Metatron", "#Debug", "#DevTools"),
    "solaris": ("#SOLARIS", "#Physics", "#ML"),
    "galt-flatcoin-concept": ("#GALT", "#DeFi", "#Stablecoin"),
    "oblivion": ("#Oblivion", "#IDE", "#AI"),
    "haki": ("#Haki", "#IDE", "#AI"),
    "knowledgeos": ("#KnowledgeOS", "#PKM", "#AI"),
    "devispro": ("#DevisPro", "#FinTech", "#Artisans"),
    "opencmo": ("#OpenCMO", "#Marketing", "#AI"),
    "bodydouble": ("#BodyDouble", "#Focus", "#ADHD"),
    "driftscape": ("#Driftscape", "#Audio", "#Generative"),
    "lifestack": ("#LifeStack", "#BuildInPublic", "#Dev"),
}


def run(cmd, cwd=None, timeout=GIT_TIMEOUT):
    """Un appel git ne fait jamais crasher le script (CI-safe)."""
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd) if cwd else None,
            capture_output=True, text=True, shell=True, timeout=timeout,
        )
        if r.returncode != 0:
            return ""
        return r.stdout.strip()
    except Exception:
        return ""


def ascii_log(text):
    """Console Windows-safe (R93) : garde les accents, supprime emojis/surrogates."""
    out = []
    for c in text or "":
        o = ord(c)
        if 0xD800 <= o <= 0xDFFF:
            continue
        if o > 0xFFFF:
            continue
        out.append(c)
    return "".join(out)


def classify_ownership(remote_text):
    """OWNED > EXTERNAL > UNKNOWN (miroir KuroUtils.psm1 Get-KuroProjectOwnership)."""
    low = (remote_text or "").lower()
    for m in OWNED_MARKERS:
        if m.lower() in low:
            return "OWNED"
    for m in EXTERNAL_MARKERS:
        if m.lower() in low:
            return "EXTERNAL"
    return "UNKNOWN"


def get_ownership(project_path):
    if not (project_path / ".git").is_dir():
        return "UNKNOWN"
    remotes = run("git remote -v", cwd=project_path)
    if not remotes:
        return "UNKNOWN"
    return classify_ownership(remotes)


def _to_int(value):
    try:
        v = (value or "").strip()
        return int(v) if v.isdigit() else 0
    except Exception:
        return 0


def collect_velocity(project_path):
    """Faits git : dernier commit, commits 7j/30j, branche, dirty. None si pas de git."""
    if not (project_path / ".git").is_dir():
        return None
    last = run('git log -1 --format="%h|%ad|%s" --date=short', cwd=project_path)
    if not last:
        return None
    parts = last.strip('"').split("|", 2)
    h, d, msg = (parts + ["", "", ""])[:3]
    c30 = _to_int(run('git rev-list --count --since="30 days ago" HEAD', cwd=project_path))
    c7 = _to_int(run('git rev-list --count --since="7 days ago" HEAD', cwd=project_path))
    branch = run("git branch --show-current", cwd=project_path) or "-"
    dirty = bool(run("git status --porcelain", cwd=project_path))
    return {"hash": h, "date": d, "msg": msg[:80], "c30": c30, "c7": c7,
            "branch": branch, "dirty": dirty}


def days_since(date_str):
    try:
        if date_str and len(date_str) >= 10:
            return (date.today() - date.fromisoformat(date_str[:10])).days
    except Exception:
        pass
    return 999


def velocity_score(facts):
    """Score Kuro : c30*3 (cap 30) + recence 7j/30j/60j/90j. Meme base que compute_progress.py."""
    if not facts:
        return -999
    score = min(30, facts.get("c30", 0) * 3)
    days = days_since(facts.get("date", ""))
    if days <= 7:
        score += 10
    elif days <= 30:
        score += 7
    elif days <= 60:
        score += 3
    elif days <= 90:
        score -= 5
    else:
        score -= 15
    return score


def is_eligible(status, ownership):
    """Compte dedie : statut Actif/Validation + OWNED uniquement (R87 + R94-v2)."""
    if ownership != "OWNED":
        return False
    return (status or "").lower() in ELIGIBLE_STATUS


def build_repo_index(docs_dir):
    """Index {nom_minuscule: Path} construit UNE fois. Dir absent -> {} (jamais de crash)."""
    index = {}
    try:
        base = Path(docs_dir)
        if not base.is_dir():
            return index
        for d in base.iterdir():
            if d.is_dir() and (d / ".git").is_dir():
                index.setdefault(d.name.lower(), d)
    except Exception:
        return index
    return index


def find_repo(name, index):
    """Resolu via l'index (+ alias R116). None si absent (ex: CI partiel)."""
    if not name or not index:
        return None
    hit = index.get(name.lower())
    if hit is not None and hit.is_dir():
        return hit
    for alias in REPO_ALIASES.get((name or "").lower(), []):
        hit = index.get(alias.lower())
        if hit is not None and hit.is_dir():
            return hit
    return None


def is_tracked(name, epingle_names):
    """True si le nom ou son dossier alias est une ligne Epingle (anti-duplicat R80)."""
    low = (name or "").lower()
    if low in epingle_names:
        return True
    for canon, aliases in REPO_ALIASES.items():
        if canon.lower() in epingle_names and low in [a.lower() for a in aliases]:
            return True
    return False


def load_projects(epingle_path):
    """Parser unique Epingle + supplement Laboratoire. Leve RuntimeError explicite si KO."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from generate_portfolio import parse_epingle
    except Exception as exc:
        raise RuntimeError("import generate_portfolio.parse_epingle impossible: %s" % exc)
    try:
        sections = parse_epingle(Path(epingle_path))
    except Exception as exc:
        raise RuntimeError("parse Epingle impossible (%s): %s" % (epingle_path, exc))
    projs = []
    for s in sections:
        name_low = s["name"].lower()
        is_external_section = "externes" in name_low or "tiers" in name_low
        for p in s["projects"]:
            projs.append({"name": p["name"], "pct": p["pct"], "status": p["status"],
                          "desc": p["desc"], "external_section": is_external_section,
                          "section": s["name"]})
    # Supplement : parse_epingle ignore la section ## Laboratoire (Horcruxe Labs,
    # russel-agent) — or ce sont des projets OWNED actifs a forte velocite.
    # Meme format de ligne, jamais de regex divergente sur les sections λ.
    try:
        text = Path(epingle_path).read_text(encoding="utf-8")
    except Exception:
        return projs
    known = set(p["name"].lower() for p in projs)
    in_labo = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_labo = "laboratoire" in line.lower()
            continue
        if not in_labo or not line.startswith("| "):
            continue
        if re.match(r"^\|\s*-+\s*\|", line) or "| ---" in line or "|---" in line:
            continue
        parts = [p.strip() for p in line.split("|")[1:-1]]
        if len(parts) < 3:
            continue
        name_raw = parts[0].replace("**", "").strip()
        if not name_raw or name_raw.startswith("-") or name_raw.lower() in ("projet", "section"):
            continue
        if name_raw.lower() in known:
            continue
        pct_raw = parts[1].strip()
        status_raw = parts[2].strip()
        if "%" not in pct_raw and not pct_raw.isdigit() and status_raw.lower() not in (
                "actif", "validation", "prototypage", "nouveau", "archive", "recherche", "pivot", "outil"):
            continue
        m_pct = re.search(r"(\d+)", pct_raw)
        projs.append({"name": name_raw, "pct": int(m_pct.group(1)) if m_pct else 0,
                      "status": status_raw, "desc": parts[3] if len(parts) > 3 else "",
                      "external_section": False, "section": "Laboratoire"})
        known.add(name_raw.lower())
    return projs


def tags_for(name):
    key = (name or "").lower()
    if key in HASHTAGS:
        return HASHTAGS[key]
    first = (name.split()[0] if name and name.split() else "Kuro")
    base = "#" + re.sub(r"[^A-Za-z0-9]", "", first)
    return ((base[:30] or "#Kuro"), "#BuildInPublic")


def sanitize(text):
    """Anti-leak R94 : jamais de chemin secret, cle, token, heuristique proprio."""
    t = text or ""
    t = re.sub(r"(?i)(api[_-]?key|token|secret|password)\s*[:=]\s*\S+", "[redacted]", t)
    t = re.sub(r"[A-Za-z]:\\[^\s]*", "[path]", t)
    t = re.sub(r"/home/[^\s]*", "[path]", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _cut_words(text, budget):
    """Coupe au mot près (jamais en plein mot), avec … si coupé."""
    text = (text or "").strip()
    if len(text) <= budget or budget < 8:
        return text[:budget] if len(text) > budget else text
    cut = text[: budget - 3].rsplit(" ", 1)[0] or text[: budget - 3]
    return cut + "..."


def flesch_ease(text):
    """Lisibilité Flesch 0-100 (R. Flesch 1948), heuristique FR/EN : groupes de
    voyelles ≈ syllabes. 60+ = clair, <30 = lourd."""
    words = re.findall(r"[A-Za-zÀ-ÿ']+", text or "")
    sentences = [s for s in re.split(r"[.!?…]+", text or "") if s.strip()]
    if not words or not sentences:
        return 0.0
    syll = 0
    for w in words:
        groups = re.findall(r"[aeiouyàâäéèêëîïôöùûüAEIOUY]+", w)
        n = len(groups)
        if n > 1 and re.search(r"(?i)e[ds]?$", w) and not re.search(r"(?i)[éèêë]$", w):
            n -= 1  # e final souvent muet
        syll += max(1, n)
    wps, spw = len(words) / len(sentences), syll / len(words)
    return max(0.0, min(100.0, 206.835 - 1.015 * wps - 84.6 * spw))


# 4 voix en rotation (frameworks d'écriture : build-log, leçon, chiffre, question).
# Noms courts : log, lecon, chiffre, question.
def voice_for(name, today=None):
    day = (today or date.today()).toordinal()
    h = sum(ord(c) for c in (name or "").lower())
    return ("log", "lecon", "chiffre", "question")[(day + h) % 4]


def voice_line1(name, presentation, themes, metric_short, voice, lang="fr"):
    t1 = themes[0] if themes else ("Progress" if lang == "en" else "Avancées")
    ctx = presentation or ""
    if lang == "en":
        if voice == "lecon":
            head = "What we learned on %s: %s" % (name, t1)
        elif voice == "chiffre":
            head = "%s: %s — %s" % (name, metric_short, t1)
        elif voice == "question":
            if ctx:
                head = "%s (%s): %s — how do you handle this" % (name, ctx, t1)
            else:
                head = "%s: %s — how do you handle this" % (name, t1)
        else:
            clean = [t for t in themes if t]
            t1b = clean[0]
            rest = clean[1:]
            body = t1b if len(clean) == 1 else ", ".join([t1b] + rest[:-1]) + " and " + rest[-1] if rest else t1b
            if ctx:
                return "%s (%s): %s." % (name, ctx, body)
            return "%s: %s." % (name, body)
        return head + "."
    if voice == "lecon":
        head = "Ce qu'on a appris sur %s : %s" % (name, t1)
    elif voice == "chiffre":
        head = "%s : %s — %s" % (name, metric_short, t1)
    elif voice == "question":
        if ctx:
            head = "%s (%s) : %s — et vous, vous gérez ça comment" % (name, ctx, t1)
        else:
            head = "%s : %s — et vous, vous gérez ça comment" % (name, t1)
    else:
        clean = [t for t in themes if t]
        t1b = clean[0]
        rest = [(t[0].lower() + t[1:]) if t[:1].isupper() else t for t in clean[1:]]
        body = t1b if len(clean) == 1 else ", ".join([t1b] + rest[:-1]) + " et " + rest[-1] if rest else t1b
        if ctx:
            return "%s (%s) : %s." % (name, ctx, body)
        return "%s : %s." % (name, body)
    return head + "."


def format_post(name, pct, status, facts, lang="fr"):
    """Post explicatif R94 : voix du jour + métrique + lien + hashtags, <=280 car (t.co).
    lang fr (défaut, annexes) ou en (hub LambdaSection). Raconte la SEMAINE,
    jamais un commit isolé. Zéro promesse future."""
    en = (lang or "fr").lower() == "en"
    ctx = presentation_for(name, (facts.get("project_desc") or ""), lang="en" if en else "fr")
    link = project_link(name)
    themes = [t for t in (facts.get("themes") or []) if t]
    if en:
        # Anglais technique : chaque thème porte son verbe d'action.
        verbs = list(facts.get("theme_verbs") or [])
        actioned = []
        for i, t in enumerate(themes):
            v = verbs[i] if i < len(verbs) else ""
            actioned.append(("%s %s" % (v, t[0].lower() + t[1:])).strip() if v else t)
        themes = actioned
    if not themes:
        # Repli : dernier commit humanisé (mieux que rien, souvent filtré en amont).
        raw = sanitize(facts.get("msg", "maintenance"))
        verb, subject = split_conventional(raw, lang="en" if en else "fr")
        subject = _capitalize(subject[:90])
        themes = [("%s: %s" % (verb, subject)) if verb else subject]
    # Miniscule médiane pour la fluidité (« A, b et c » / « A, b and c »).
    flow = [themes[0]] + [(t[0].lower() + t[1:]) if t[:1].isupper() else t
                          for t in themes[1:3]]
    try:
        pct_n = int(pct)
    except Exception:
        pct_n = 0
    if en:
        metric = "%d commits (30d), %d (7d)" % (facts.get("c30", 0), facts.get("c7", 0))
        status_en = STATUS_EN.get((status or "").lower(), status)
        line3 = "%s, %d%% %s." % (metric, pct_n, status_en)
        metric_short = "%d commits in 30 days" % facts.get("c30", 0)
    else:
        metric = "%d commits 30j, %d à 7j" % (facts.get("c30", 0), facts.get("c7", 0))
        line3 = "%s, %d%% %s." % (metric, pct_n, status)
        metric_short = "%d commits en 30 jours" % facts.get("c30", 0)
    line5 = " ".join(tags_for(name)[:3])
    voice = voice_for(name)

    def _render(flow_list, use_tag, use_link):
        l1 = voice_line1(name, use_tag, flow_list, metric_short, voice,
                         lang="en" if en else "fr")
        parts = [l1, line3]
        if use_link:
            parts.append(link)
        parts.append(line5)
        return "\n\n".join(parts)

    cur_flow, cur_ctx, cur_link = list(flow), ctx, link
    post = _render(cur_flow, cur_ctx, cur_link)
    # Ordre de sacrifice : thèmes surnuméraires, coupe au mot, présentation, lien.
    while len(cur_flow) > 1 and x_len(_render(cur_flow, cur_ctx, cur_link)) > 280:
        cur_flow = cur_flow[:-1]
    post = _render(cur_flow, cur_ctx, cur_link)
    if x_len(post) > 280:
        overflow = x_len(post) - 280
        cut = _cut_words(" ; ".join(cur_flow), max(20, len(" ; ".join(cur_flow)) - overflow))
        post = _render([cut], cur_ctx, cur_link)
        if x_len(post) > 280 and cur_ctx:
            post = _render([cut], "", cur_link)
        if x_len(post) > 280 and cur_link:
            post = _render([cut], "", "")
    return post


def resolve_one(p, index):
    """Pipeline complete pour UN projet Epingle. Retourne (entry, None) si
    eligible ou (None, (nom, raison)) sinon. Ne leve jamais."""
    name = p.get("name", "?")
    try:
        if p.get("external_section"):
            return None, (name, "section-externe")
        repo = find_repo(name, index)
        if repo is None:
            return None, (name, "no-local-repo")
        ownership = get_ownership(repo)
        if ownership != "OWNED":
            return None, (name, "ownership-%s" % ownership)
        if not is_eligible(p.get("status"), ownership):
            return None, (name, "statut-%s" % p.get("status"))
        facts = collect_velocity(repo)
        if facts is None:
            return None, (name, "no-git-facts")
        if days_since(facts.get("date", "")) > FRESH_DAYS:
            return None, (name, "stale")
        facts["themes"] = week_themes(repo)
        facts["theme_verbs"] = theme_verbs(repo)
        facts["project_desc"] = p.get("desc", "")
        facts["next"] = next_step(repo)
        return ({"project": p, "facts": facts, "ownership": ownership,
                 "score": velocity_score(facts)}, None)
    except Exception as exc:
        return None, (name, "erreur-%s" % exc)


def select_top(projs, top_n, docs_dir=None):
    """Selection top-velocite OWNED-only. Filtres cheap d'abord (section, repo,
    ownership, statut) puis git lourd uniquement pour les candidats. Retourne
    (selected, skipped). Ne leve jamais (CI-safe)."""
    top_n = max(1, top_n or 3)
    index = build_repo_index(docs_dir if docs_dir is not None else DOCS)
    ranked = []
    skipped = []
    for p in projs or []:
        entry, skip = resolve_one(p, index)
        if entry is not None:
            ranked.append(entry)
        elif skip is not None:
            skipped.append(skip)
    ranked.sort(key=lambda r: (r["score"], r["facts"]["c7"]), reverse=True)
    return ranked[:top_n], skipped


def select_only(projs, names, docs_dir=None):
    """Drafts forces pour projets nommes (ex: --only Helium). Memes gates
    (ownership, statut, fraicheur), sans cutoff top-N. Retourne (selected, skipped)."""
    index = build_repo_index(docs_dir if docs_dir is not None else DOCS)
    wanted = [(n or "").lower() for n in names or []]
    by_name = {}
    for p in projs or []:
        by_name.setdefault((p.get("name") or "").lower(), p)
    selected, skipped = [], []
    for w, raw in zip(wanted, names or []):
        p = by_name.get(w)
        if p is None:
            skipped.append((raw, "inconnu-epingle"))
            continue
        entry, skip = resolve_one(p, index)
        if entry is not None:
            selected.append(entry)
        elif skip is not None:
            skipped.append(skip)
    selected.sort(key=lambda r: (r["score"], r["facts"]["c7"]), reverse=True)
    return selected, skipped


def write_drafts(selected, outputs_dir, today=None, lang="fr", write_hub=True):
    """Ecrit drafts X (sûrs, lintés) + versions longues Discord + hub (optionnel).
    lang fr (annexes) ou en (hub). Longues toujours en FR (serveur francophone).
    Slugs dedupliques. Lint bloquant -> pas de fichier (raison console).
    Selection vide -> []."""
    if not selected:
        return []
    today = today or date.today().isoformat()
    out = Path(outputs_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    written = []
    used_slugs = set()
    for r in selected:
        p, f = r["project"], r["facts"]
        if "themes" in f and not f["themes"]:
            # Pipeline réelle : rien de publiable cette semaine -> pas de draft du tout.
            # (Appels legacy sans clé "themes" gardent le repli dernier-commit.)
            print("  [SKIP] %s : rien de publiable (que du trivia 7j)." % p["name"])
            continue
        post = format_post_safe(p["name"], p["pct"], p["status"], f, lang=lang)
        if post is None:
            print("  [LINT-BLOCK] %s : contenu sensible inaffichable, pas de draft." % p["name"])
            continue
        slug = re.sub(r"[^A-Za-z0-9-]+", "-", p["name"]).strip("-").lower() or "projet"
        base, n = slug, 2
        while slug in used_slugs:
            slug = "%s-%d" % (base, n)
            n += 1
        used_slugs.add(slug)
        path = out / ("x_post_%s-%s.md" % (today, slug))
        path.write_text(post + "\n", encoding="utf-8")
        written.append((p["name"], str(path), post))
        long_path = out / ("x_long_%s-%s.md" % (today, slug))
        long_path.write_text(format_long(p["name"], p["pct"], p["status"], f,
                                         p.get("desc", "")) + "\n", encoding="utf-8")
    if not written:
        return []
    # Hub : 1 post agregateur compatible R94 historique (top = premier).
    if write_hub:
        top = None
        for r in selected:
            if any(w[0] == r["project"]["name"] for w in written):
                top = r
                break
        if top is not None:
            hub_post = format_post_safe(top["project"]["name"], top["project"]["pct"],
                                        top["project"]["status"], top["facts"], lang=lang) or ""
            if hub_post:
                hub_path = out / ("x_post_%s.md" % today)
                hub_path.write_text(hub_post + "\n", encoding="utf-8")
                written.append(("HUB", str(hub_path), hub_post))
    # Menage R116 : supprime les drafts du jour devenus hors-selection
    # (ex: projet sorti du top-3). Ne touche jamais les autres dates ni le hub.
    keep = set(str(p) for _, p, _ in written)
    for stale in out.glob("x_post_%s-*.md" % today):
        if str(stale) not in keep:
            try:
                stale.unlink()
            except Exception:
                pass
    return written


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Drafts X top-velocite OWNED-only (R94-v2)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--only", action="append", default=[],
                    help="Force le draft d'un projet Epingle (repetable, ex: --only Helium). "
                         "Memes gates, sans cutoff top-N.")
    ap.add_argument("--epingle", default=str(EPINGLE))
    ap.add_argument("--docs", default=str(DOCS))
    ap.add_argument("--outputs", default=str(OUTPUTS))
    args = ap.parse_args(argv)
    dry = not args.apply
    top_n = max(1, args.top or 3)

    epingle = Path(args.epingle)
    if not epingle.is_file():
        print("[ERR] Epingle introuvable: %s" % epingle)
        return 2
    try:
        projs = load_projects(epingle)
    except RuntimeError as exc:
        print("[ERR] %s" % exc)
        return 2
    if not projs:
        print("[SKIP] Epingle vide ou illisible — aucun draft.")
        return 0
    selected, skipped = select_top(projs, top_n, docs_dir=args.docs)
    if args.only:
        forced, skipped_only = select_only(projs, args.only, docs_dir=args.docs)
        have = set(r["project"]["name"].lower() for r in selected)
        for r in forced:
            if r["project"]["name"].lower() not in have:
                selected.append(r)
                have.add(r["project"]["name"].lower())
        skipped.extend(skipped_only)
        selected.sort(key=lambda r: (r["score"], r["facts"]["c7"]), reverse=True)

    print("=== gen_x_posts (R94-v2) top=%d ===" % top_n)
    print("  Projets Epingle: %d | eligibles: %d | skipped: %d"
          % (len(projs), len(selected), len(skipped)))
    for r in selected:
        p, f = r["project"], r["facts"]
        line = "  [PICK] %-18s score=%d c30=%d c7=%d %s %s (%s)" % (
            p["name"], r["score"], f["c30"], f["c7"], f["date"], f["hash"], r["ownership"])
        print(ascii_log(line))
        preview = format_post(p["name"], p["pct"], p["status"], f).replace("\n", " / ")
        print(ascii_log("         %s (%d chars)" % (preview[:120], len(preview))))
    if dry:
        print("  [DRY] skipped=%d (top 10): %s" % (len(skipped), ascii_log(str(skipped[:10]))))
        print("  [DRY] relance avec --apply pour ecrire dans %s" % args.outputs)
        return 0

    if not selected:
        print("  [SKIP] rien d'eligible (calme ou que des skips) — aucun fichier ecrit.")
        return 0
    written = write_drafts(selected, Path(args.outputs))
    for name, path, post in written:
        print(ascii_log("  [OK] %s -> %s (%d chars)" % (name, path, len(post))))
    print("  [OK] %d fichier(s). Publication X manuelle (gate R94-v2)." % len(written))
    return 0


if __name__ == "__main__":
    sys.exit(main())
