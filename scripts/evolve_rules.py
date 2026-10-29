"""Boucle d'evolution des regles : coreset DPP + front de Pareto (WS4).

Protocole rule_125 (HarnessPro, arXiv:2610.26770) :

1. Verifie le verrou de l'evaluateur fige (evals/frozen_eval.lock.json) :
   si l'evaluateur a ete modifie sans re-freeze, REFUSE (l'evolution ne
   peut pas toucher son examinateur).
2. Choisit un COSET de regles a faire evoluer en premier, par DPP greedy
   (diversite = similarite de contenu, difficulte = densite du fichier).
3. Construit le FRONT DE PARETO des packs (cout = tokens estimes, perf =
   couverture ponderee mandatory x2 / optionnelle x1) avec plafond = h0.

Sortie : reports/evolution_report_<date>.json (deterministe, hors reseau).
Le diagnostic et la reecriture restent LLM/agent (session dediee) : cet
outil fournit le plan, pas la reecriture.

Usage :
  python scripts/evolve_rules.py [--coreset 10] [--report PATH]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "evals"))

import eval_rules  # noqa: E402  (evaluateur fige, import pur — pas d'execution)
from kuro_paths import confine_arg  # noqa: E402

RULES_DIR = ROOT / "rules"
REPORTS_DIR = ROOT / "reports"
LOCK_PATH = ROOT / "evals" / "frozen_eval.lock.json"
THETA = 0.7  # ponderation difficulte (comme RHO/HarnessPro) : alpha = t/(2(1-t))
STOPWORDS = set(
    "rule rules the and for with that this from must should when check verify "
    "action default file files session sessions project projects agent agents"
    .split()
)


def check_lock() -> dict:
    """Le verrou doit exister et matcher l'evaluateur actuel."""
    if not LOCK_PATH.exists():
        raise SystemExit(
            "[evolve] VERROU ABSENT : sceller d'abord la baseline h0 avec\n"
            "  python evals/eval_rules.py --freeze")
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    current = eval_rules.eval_sha256()
    if lock.get("eval_sha256") != current:
        raise SystemExit(
            "[evolve] REFUSE : l'evaluateur fige a ete modifie depuis le\n"
            "  freeze. Re-freeze explicite requis (eval_rules.py --freeze)\n"
            "  avec validation humaine — rule_125.")
    return lock


# ---------------------------------------------------------------- DPP

def fingerprint(path: Path) -> dict[str, float]:
    """Embedding sac-de-mots normalise L2 (stopwords retires)."""
    text = path.read_text(encoding="utf-8").lower()
    words = [w for w in re.findall(r"[a-z]{4,}", text) if w not in STOPWORDS]
    vec: dict[str, float] = {}
    for w in words:
        vec[w] = vec.get(w, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {k: v / norm for k, v in vec.items()}


def cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(v * b.get(k, 0.0) for k, v in a.items())


def det(matrix: list[list[float]]) -> float:
    """Determinant par elimination de Gauss (std lib, k petit)."""
    m = [row[:] for row in matrix]
    n = len(m)
    d = 1.0
    for i in range(n):
        pivot = max(range(i, n), key=lambda r: abs(m[r][i]))
        if abs(m[pivot][i]) < 1e-12:
            return 0.0
        if pivot != i:
            m[i], m[pivot] = m[pivot], m[i]
            d = -d
        d *= m[i][i]
        for r in range(i + 1, n):
            factor = m[r][i] / m[i][i]
            for c in range(i, n):
                m[r][c] -= factor * m[i][c]
    return d


def dpp_coreset(paths: list[Path], k: int) -> list[dict]:
    """k-DPP greedy : ajoute la regle qui maximise le determinant du kernel.

    Kernel K = diag(w) S diag(w), S = similarite cosinus des fingerprints,
    w = (difficulte / max difficulte)^alpha, alpha = theta/(2(1-theta)).
    Diversite + difficulte, comme le coreset de taches du papier.
    """
    vecs = {p: fingerprint(p) for p in paths}
    lines = {p: len(p.read_text(encoding="utf-8").splitlines()) for p in paths}
    max_lines = max(lines.values()) or 1
    alpha = THETA / (2 * (1 - THETA))
    weights = {p: max(lines[p] / max_lines, 0.05) ** alpha for p in paths}

    kernel = {}
    for p in paths:
        kernel[p] = {}
        for q in paths:
            kernel[p][q] = weights[p] * weights[q] * cosine(vecs[p], vecs[q])

    chosen: list[Path] = []
    remaining = list(paths)
    while remaining and len(chosen) < k:
        best, best_det = None, -1.0
        for cand in remaining:
            subset = chosen + [cand]
            sub = [[kernel[a][b] for b in subset] for a in subset]
            d = det(sub)
            if d > best_det:
                best, best_det = cand, d
        chosen.append(best)
        remaining.remove(best)

    return [{
        "rule": p.stem,
        "difficulty": round(lines[p] / max_lines, 3),
        "tokens_est": len(p.read_text(encoding="utf-8")) // 4,
        "dpp_gain": None,
    } for p in chosen]


# ------------------------------------------------------- Pareto packs

def load_pack_membership() -> dict[str, list[str]]:
    import gen_rule_packs
    return gen_rule_packs.rule_packs(gen_rule_packs.load_metadata())


def mandatory_ids() -> set[str]:
    """IDs mandatory — delegation au module canonique (gen_rule_packs)."""
    import gen_rule_packs
    return gen_rule_packs.mandatory_ids()


def pareto_packs(membership: dict[str, list[str]]) -> list[dict]:
    """Tableau perf/coût des 3 packs + dominance. Perf = couverture ponderee."""
    import gen_rule_packs
    all_rules = sorted(membership)
    mand_nums = gen_rule_packs.mandatory_rule_numbers()
    mand_files = [n for n in all_rules
                  if gen_rule_packs.rule_numbers(n) & mand_nums]
    # poids : mandatory x2 (papier : la couverture mandatory domine)
    max_perf = 2 * len(mand_files) + (len(all_rules) - len(mand_files))

    rows = []
    for pack in ("lite", "medium", "heavy"):
        included = [n for n in all_rules if pack in membership[n]]
        perf = (2 * sum(1 for n in included if n in mand_files)
                + sum(1 for n in included if n not in mand_files)) / max_perf
        tokens = sum(len((RULES_DIR / f"{n}.md").read_text(encoding="utf-8"))
                     for n in included) // 4
        rows.append({
            "pack": pack,
            "rules": len(included),
            "tokens_est": tokens,
            "perf_cover": round(perf, 3),
            "dominated_by": None,
        })
    for a in rows:
        for b in rows:
            if a is b:
                continue
            if (b["tokens_est"] <= a["tokens_est"]
                    and b["perf_cover"] >= a["perf_cover"]
                    and (b["tokens_est"] < a["tokens_est"]
                         or b["perf_cover"] > a["perf_cover"])):
                a["dominated_by"] = b["pack"]
    return rows


# ------------------------------------------------------------- main

def build_report(coreset_size: int) -> dict:
    lock = check_lock()
    baseline = lock.get("baseline", {})
    paths = sorted(RULES_DIR.glob("rule_*.md"))
    coreset = dpp_coreset(paths, coreset_size)
    packs = pareto_packs(load_pack_membership())

    summary = eval_rules.evaluate(ROOT)
    floor = baseline.get("pass_rate", 1.0)
    current = summary["pass_rate"]

    return {
        "generated_at": date.today().isoformat(),
        "evaluator_locked": True,
        "baseline_h0": {"pass_rate": floor,
                        "passed": baseline.get("passed"),
                        "total": baseline.get("total")},
        "current": {"pass_rate": current,
                    "passed": summary["passed"],
                    "total": summary["total"],
                    "floor_respected": current >= floor},
        "failing_checks": [c["id"] for c in summary["checks"] if not c["ok"]],
        "coreset": coreset,
        "packs_pareto": packs,
        "next_actions": [
            "Diagnostiquer les regles du coreset (trajectoires/session"
            " summaries, R89 lessons) dans une session dediee.",
            "Proposer des reecritures en candidats separes (git), sans"
            " toucher a evals/.",
            "Rejeter tout candidat faisant chuter pass_rate sous la"
            " baseline h0 (plafond rule_125).",
            "Proposer a l'humain le menu des candidats non-domines"
            " (lite/medium/heavy).",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Rapport d'evolution des regles")
    parser.add_argument("--coreset", type=int, default=10,
                        help="taille du coreset DPP (defaut 10)")
    parser.add_argument("--report", default=None,
                        help="fichier rapport JSON (defaut : reports/")
    args = parser.parse_args(argv)

    report = build_report(args.coreset)

    out = (confine_arg(args.report, [ROOT, Path(tempfile.gettempdir()).resolve()])
           if args.report
           else REPORTS_DIR / f"evolution_report_{report['generated_at']}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                   encoding="utf-8")

    cur = report["current"]
    print(f"[evolve] evaluateur verrouille OK ; baseline h0 ="
          f" {report['baseline_h0']['pass_rate']:.0%}"
          f" ; actuel = {cur['pass_rate']:.0%}"
          f" ; plafond respecte = {cur['floor_respected']}")
    print(f"[evolve] coreset DPP ({len(report['coreset'])} regles) :")
    for c in report["coreset"]:
        print(f"    - {c['rule']:48} diff={c['difficulty']}"
              f" ~{c['tokens_est']}tok")
    print("[evolve] front de Pareto des packs :")
    for p in report["packs_pareto"]:
        dom = f" (DOMINE par {p['dominated_by']})" if p["dominated_by"] else ""
        print(f"    - {p['pack']:6} perf={p['perf_cover']:.0%}"
              f" cout={p['tokens_est']}tok {p['rules']}regles{dom}")
    try:
        shown = out.relative_to(ROOT)
    except ValueError:
        shown = out
    print(f"[evolve] rapport : {shown}")
    return 0 if cur["floor_respected"] and not report["failing_checks"] else 1


if __name__ == "__main__":
    sys.exit(main())
