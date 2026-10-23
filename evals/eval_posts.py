"""Eval deterministe de la qualite des posts X (P2 : evals CI).

Sur un dataset golden (evals/data/post_cases.jsonl), verifie que les
couches deterministes du cerveau de posts se comportent comme prevu :
- lint_post detecte les etiquettes attendues (ou reste vide si attendu) ;
- deterministic_score respecte les bornes et signale les issues attendues.

Sortie : evals/report.json ; code retour 1 si un cas echoue.
Aucun reseau, aucun LLM : c'est le filet CI deterministe (R115 gate 1).
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from gen_x_posts import lint_post  # noqa: E402
from kuro_paths import confine_arg  # noqa: E402
from post_brain import deterministic_score  # noqa: E402

DEFAULT_DATA = ROOT / "evals" / "data" / "post_cases.jsonl"
DEFAULT_REPORT = ROOT / "evals" / "report.json"
# Racines legitimes pour --data / --report : le depot, plus le temp systeme
# (les evals CI tournent dans un tmp_path pytest hors depot).
_EVAL_ROOTS = [ROOT, Path(tempfile.gettempdir()).resolve()]


def load_cases(path=DEFAULT_DATA):
    """Charge le dataset JSONL (lignes vides / # commentees ignorees).

    `path` peut venir de la CLI (S8707) : confine aux racines d'eval.
    """
    cases = []
    for line in confine_arg(path, _EVAL_ROOTS).read_text(
            encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        cases.append(json.loads(line))
    return cases


def run_case(case):
    """Execute un cas : retourne le detail + la liste des echecs (vide = OK)."""
    text = case["text"]
    projet = case.get("projet", "")
    themes = case.get("themes", [])
    lang = case.get("lang", "fr")

    lint = lint_post(projet, text)
    score, issues = deterministic_score(projet, text, themes=themes, lang=lang)

    fails = []
    expect_lint_any = case.get("expect_lint_any")
    if expect_lint_any and not any(lbl in lint for lbl in expect_lint_any):
        fails.append(f"lint attendu {expect_lint_any} absent (obtenu {lint})")
    if case.get("expect_lint_none") and lint:
        fails.append(f"lint devrait etre vide (obtenu {lint})")

    expect_issue_any = case.get("expect_issue_any")
    if expect_issue_any:
        joined = " | ".join(issues)
        if not any(frag in joined for frag in expect_issue_any):
            fails.append(f"issue attendue {expect_issue_any} absente ({issues})")

    score_min = case.get("expect_score_min")
    if score_min is not None and score < score_min:
        fails.append(f"score {score} < minimum {score_min}")
    score_max = case.get("expect_score_max")
    if score_max is not None and score > score_max:
        fails.append(f"score {score} > maximum {score_max}")

    return {"id": case.get("id", "?"), "score": score, "lint": lint,
            "issues": issues, "fails": fails}


def evaluate(cases):
    """Execute tous les cas et resume le taux de reussite."""
    results = [run_case(c) for c in cases]
    failed = [r for r in results if r["fails"]]
    return {
        "total": len(results),
        "passed": len(results) - len(failed),
        "failed": len(failed),
        "pass_rate": (len(results) - len(failed)) / len(results) if results else 0.0,
        "results": results,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Eval deterministe des posts X")
    parser.add_argument("--data", default=str(DEFAULT_DATA),
                        help="dataset JSONL (defaut : evals/data/post_cases.jsonl)")
    parser.add_argument("--report", default=str(DEFAULT_REPORT),
                        help="fichier rapport JSON (defaut : evals/report.json)")
    args = parser.parse_args(argv)

    cases = load_cases(args.data)
    if not cases:
        print(f"[evals] dataset vide : {args.data}")
        return 1

    summary = evaluate(cases)
    report = confine_arg(args.report, _EVAL_ROOTS)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(summary, ensure_ascii=False, indent=2),
                      encoding="utf-8")

    for r in summary["results"]:
        status = "OK  " if not r["fails"] else "FAIL"
        detail = "" if not r["fails"] else " -> " + " ; ".join(r["fails"])
        print(f"[evals] {status} {r['id']:32} score={r['score']:3}{detail}")

    print(f"[evals] {summary['passed']}/{summary['total']} cas OK"
          f" (pass_rate={summary['pass_rate']:.0%})")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
