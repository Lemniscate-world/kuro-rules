#!/usr/bin/env python3
"""post_brain.py — Moteur qui raisonne et auto-ameliore les posts (R94-v2).

Boucle memoire :
  review  : note un draft (score deterministe + critique LLM best-effort).
  flag    : 'museler <terme>' -> ajoute aux overrides (applique des demain).
  ingest  : statut de diffusion des posts (file Buffer / envoye / disparu).
  learn   : agrege historique -> constats + propositions (auto : rien de destructif).

Le LLM (kuro_llm : OpenRouter -> DeepSeek -> Ollama cloud) ne bloque JAMAIS :
indisponible -> score deterministe seul. Aucune reecriture silencieuse :
--rewrite n'ecrit que si le nouveau draft passe le lint ET ameliore le score.

Zero dependance hors kuro_llm (optionnel). Fichiers :
  outputs/post_history.jsonl      (1 ligne JSON par review)
  outputs/post_delivery.json      (statut file/envoye/disparu par id)
  outputs/post_metrics.json       (metriques d'engagement quand dispo)
  config/posting_overrides.json   (termes museles par projet)
"""
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path.home()
DOCS = Path(os.environ.get("DOCS_DIR", str(HOME / "Documents")))
KURORULES = Path(os.environ.get("KURO_RULES_DIR", str(DOCS / "kuro-rules")))
OUTPUTS = KURORULES / "outputs"
HISTORY = OUTPUTS / "post_history.jsonl"
DELIVERY = OUTPUTS / "post_delivery.json"
METRICS = OUTPUTS / "post_metrics.json"
OVERRIDES = KURORULES / "config" / "posting_overrides.json"


def load_overrides(path=None):
    try:
        data = json.loads(Path(path or OVERRIDES).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def deterministic_score(project, text, themes=(), lang="fr"):
    """Score /100 sans reseau. Retourne (score, issues[])."""
    t = text or ""
    issues = []
    score = 50
    n_themes = len([x for x in themes or [] if x])
    if n_themes >= 2:
        score += 15
    elif n_themes == 1:
        score += 8
    else:
        score -= 20
        issues.append("aucun theme : micro-commit ou semaine vide")
    if (lang or "fr").lower() == "en":
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from gen_x_posts import looks_french
            if looks_french(t):
                score -= 8
                issues.append("melange FR/EN : themes non traduits")
        except Exception:
            pass
    ln = len(t)
    if 120 <= ln <= 260:
        score += 10
    elif ln < 60:
        score -= 10
        issues.append("trop court : n'informe pas")
    words = re.findall(r"[A-Za-zÀ-ÿ']+", t)
    sentences = [s for s in re.split(r"[.!?]+", t) if s.strip()]
    if sentences and words:
        avg = len(words) / len(sentences)
        if avg <= 25:
            score += 5
        else:
            score -= 5
            issues.append(f"phrases trop longues ({avg:.0f} mots/phrase)")
    if re.search(r"  +", t):
        score -= 2
        issues.append("espaces doubles")
    if re.search(r"[A-Za-z]:\\[^\s]*|/home/[^\s]*", t):
        score -= 10
        issues.append("chemin local visible")
    return max(0, min(100, score)), issues


def llm_critique(project, text, lang="fr"):
    """Critique LLM best-effort. None si aucun moteur dispo. Jamais de crash."""
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from kuro_llm import ask
    except Exception:
        return None
    if (lang or "fr").lower() == "en":
        prompt = (
            "You are an editor for tech X posts (280 chars max). "
            f"Project: {project}. Post: \"{text[:500]}\". "
            "Reply with strict JSON only: "
            '{"score": <0-100>, "issues": ["..."], "rewrite": "<improved version>" or null}. '
            "Criteria: clarity for non-experts, real informative value, "
            "useless jargon, risk of leaking internal details. "
            "The rewrite keeps hashtags and metric, <=280 chars.")
        system = "You are a demanding editor. Strict JSON only."
    else:
        prompt = (
            "Tu es éditeur pour des posts X tech (280 car max). "
            f"Projet : {project}. Post : « {text[:500]} ». "
            "Réponds JSON strict uniquement : "
            '{"score": <0-100>, "issues": ["..."], "rewrite": "<version améliorée>" ou null}. '
            "Critères : clarté pour un non-initié, valeur informative réelle, "
            "jargon inutile, risque de révéler des détails internes. "
            "Le rewrite garde hashtags et métrique, ≤280 car.")
        system = "Tu es un éditeur exigeant. JSON strict uniquement."
    try:
        raw = ask(prompt, system=system)
    except Exception:
        return None
    if not raw:
        return None
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        data = json.loads(m.group(0) if m else raw)
        return {"score": int(data.get("score", 0)),
                "issues": list(data.get("issues", []))[:5],
                "rewrite": data.get("rewrite")}
    except Exception:
        return None


def review_draft(project, text, themes=(), lang="fr"):
    det, issues = deterministic_score(project, text, themes)
    out = {"date": date.today().isoformat(), "projet": project,
           "score_det": det, "issues": issues, "score_llm": None, "rewrite": None}
    crit = llm_critique(project, text, lang=lang)
    if crit:
        out["score_llm"] = max(0, min(100, crit["score"]))
        out["issues"] = list(dict.fromkeys(issues + crit["issues"]))[:8]
        out["rewrite"] = crit["rewrite"]
    out["score"] = out["score_llm"] if out["score_llm"] is not None else det
    return out


def append_history(entry, path=HISTORY):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def apply_overrides(strategies):
    """Fusionne config/posting_overrides.json : {Projet: {never_add: [...]}} (additif)."""
    for proj, ov in load_overrides().items():
        key = (proj or "").lower()
        if key in strategies:
            extra = [t for t in (ov.get("never_add") or []) if t]
            strategies[key]["never"] = sorted(set(strategies[key].get("never", [])) | set(extra))
    return strategies


def flag_term(project, term, path=None):
    """'Museler' un terme : ajoute a never_add (effectif des demain). Retourne True si nouveau."""
    p = Path(path or OVERRIDES)
    data = load_overrides(p)
    key = project
    entry = data.get(key, {})
    terms = entry.get("never_add", [])
    if term in terms:
        return False
    entry["never_add"] = terms + [term]
    data[key] = entry
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def ingest_delivery(state_path=None, out_path=None):
    """Statut reel de chaque post enregistre : scheduled / sent / gone.
    Ecrit outputs/post_delivery.json. Retourne le dict."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import buffer_post as bp
    api_key = os.environ.get("BUFFER_API_KEY", "")
    if not api_key:
        return {"error": "BUFFER_API_KEY absent"}
    try:
        import gen_x_posts as gx
        state = json.loads(Path(state_path or gx.OUTPUTS / "x_posted.json").read_text(encoding="utf-8"))
    except Exception as exc:
        return {"error": f"etat illisible: {exc}"}
    orgs = bp.list_organizations(api_key)
    if not orgs:
        return {"error": "aucune organisation"}
    scheduled, sent = {}, {}
    for org in orgs:
        for status_name, filt in (("scheduled", "scheduled"), ("sent", "sent")):
            q = ("query Posts {{ posts(input: {{ organizationId: \"{}\", "
                 "filter: {{ status: [{}] }} }}) {{ edges {{ node {{ id }} }} }} }}".format(org["id"], status_name))
            try:
                data = bp.gql(q, api_key)
            except Exception:
                continue
            for e in (data.get("posts") or {}).get("edges", []) or []:
                nid = (e.get("node") or {}).get("id", "")
                if nid:
                    (scheduled if status_name == "scheduled" else sent)[nid] = True
    out = {}
    for account, entries in state.items():
        for e in entries or []:
            pid = e.get("id", "")
            if not pid:
                continue
            if pid in scheduled:
                st = "scheduled"
            elif pid in sent:
                st = "sent"
            else:
                st = "gone"
            out[pid] = {"compte": account, "projet": e.get("projet", ""),
                        "statut": st, "date": e.get("date", "")}
    p = Path(out_path or DELIVERY)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def learn(history_path=None):
    """Agrege l'historique -> constats chiffres + propositions. Auto : rien de destructif."""
    notes = []
    rows = []
    try:
        for line in Path(history_path or HISTORY).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    except Exception:
        pass
    if not rows:
        return ["pas encore d'historique : lance `review` sur les drafts du jour."]
    by_proj = {}
    for r in rows:
        by_proj.setdefault(r.get("projet", "?"), []).append(r.get("score", 0))
    for proj, scores in sorted(by_proj.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
        avg = sum(scores) / len(scores)
        notes.append("%s : score moyen %d/%d reviews — %s" % (
            proj, avg, len(scores),
            "a museler/retravailler" if avg < 55 else "stable" if avg < 75 else "bon"))
    all_issues = {}
    for r in rows:
        for i in r.get("issues", []):
            all_issues[i] = all_issues.get(i, 0) + 1
    for issue, n in sorted(all_issues.items(), key=lambda kv: -kv[1])[:5]:
        notes.append("motif recurrent x%d : %s" % (n, issue))
    notes.append("proposition : `flag --project <P> --term <mot>` pour museler un terme.")
    return notes


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Moteur posts : review/learn/ingest/flag")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_rev = sub.add_parser("review")
    p_rev.add_argument("--project", required=True)
    p_rev.add_argument("--from-file", default="")
    p_rev.add_argument("--text", default="")
    p_rev.add_argument("--rewrite", action="store_true",
                       help="Ecrit la version LLM si meilleure ET lint OK.")
    p_fl = sub.add_parser("flag")
    p_fl.add_argument("--project", required=True)
    p_fl.add_argument("--term", required=True)
    sub.add_parser("ingest")
    sub.add_parser("learn")
    args = ap.parse_args(argv)

    if args.cmd == "flag":
        if flag_term(args.project, args.term):
            print(f"  [OK] '{args.term}' musele pour {args.project} (effectif des demain).")
        else:
            print("  [SKIP] deja musele.")
        return 0

    if args.cmd == "ingest":
        out = ingest_delivery()
        if "error" in out:
            print("[ERR] {}".format(out["error"]))
            return 1
        counts = {}
        for v in out.values():
            counts[v["statut"]] = counts.get(v["statut"], 0) + 1
        print(f"  diffusion: {counts}")
        return 0

    if args.cmd == "learn":
        for line in learn():
            print(f"  - {line}")
        return 0

    if args.cmd == "review":
        text = args.text
        if args.from_file:
            try:
                text = Path(args.from_file).read_text(encoding="utf-8")
            except Exception as exc:
                print(f"[ERR] draft illisible: {exc}")
                return 2
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import gen_x_posts as gx
        lint = gx.lint_post(args.project, text)
        rep = review_draft(args.project, text)
        print("  score: %d/100 (det %d%s)" % (
            rep["score"], rep["score_det"],
            (", llm %d" % rep["score_llm"]) if rep["score_llm"] is not None else ", llm indisponible"))
        for i in rep["issues"] + (["lint: " + ", ".join(lint)] if lint else []):
            print(f"  - {i}")
        append_history(rep)
        if args.rewrite and rep.get("rewrite"):
            new = (rep["rewrite"] or "").strip()
            if new and len(new) <= 280 and not gx.lint_post(args.project, new):
                det2, _ = deterministic_score(args.project, new)
                if det2 >= rep["score_det"]:
                    Path(args.from_file).write_text(new + "\n", encoding="utf-8")
                    print("  [OK] rewrite applique (score %d -> %d)." % (rep["score_det"], det2))
                    return 0
            print("  [SKIP] rewrite rejete (lint ou score).")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
