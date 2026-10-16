"""Harnais Q8 : batch de runs vers les 30 verts exiges avant decision go/no-go.

Scenarios par iteration (sans ecriture, sans reseau sauf git remote local) :
  1. validation-pass : 5 gates OK -> halted=False attendu
  2. validation-halt : fuzzer KO -> halted=True attendu
  3. multirepo : fan-out lecture seule -> fails=0 attendu
  4. compile-4 : les 4 graphes compilent

Rapport JSON local uniquement (logs/ ignore, jamais committe) :
    python apps/kuro-graph/run_matrix.py --runs 5 --append

Decision go/no-go (PLAN Q8) : 30 runs verts + revue R38, sinon NO-GO.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

GRAPH = Path(__file__).resolve().parent
sys.path.insert(0, str(GRAPH))

from state import STATE_VERSION, new_state

PASS_METRICS = {
    "fuzzer": {"detection_rate": 0.9},
    "stress": {"passed": 15, "total": 15, "crashes": 0, "false_positives": 0},
    "combinatorial": {"overall": 0.9, "worst_family": 0.8},
    "oos": {"detected": 6, "total": 6, "fp_events": 2},
    "benchmark": {"detection_gain_vs_best": 0.6},
}

HALT_METRICS = {"fuzzer": {"detection_rate": 0.4}}

TARGET_RUNS = 30


def base_state() -> dict:
    s = new_state(write=False, dry_run=True)
    s["state_version"] = STATE_VERSION
    return s


def scenario_validation_pass(app) -> tuple[bool, str]:
    s = base_state()
    s["validation_results"] = dict(PASS_METRICS)
    try:
        r = app.invoke(s)
        ok = r.get("halted") is False and r.get("validation_stage") == "benchmark"
        return ok, f"halted={r.get('halted')} stage={r.get('validation_stage')}"
    except Exception as exc:
        return False, f"exception: {exc}"


def scenario_validation_halt(app) -> tuple[bool, str]:
    s = base_state()
    s["validation_results"] = dict(HALT_METRICS)
    try:
        r = app.invoke(s)
        ok = r.get("halted") is True and "fuzzer" in str(r.get("halt_reason", ""))
        return ok, f"halted={r.get('halted')} reason={r.get('halt_reason')}"
    except Exception as exc:
        return False, f"exception: {exc}"


def scenario_multirepo(app) -> tuple[bool, str]:
    try:
        r = app.invoke(base_state())
        ok = r.get("fails") == 0 and len(r.get("multirepo_audited", [])) >= 1
        return ok, f"fails={r.get('fails')} audited={r.get('multirepo_audited')}"
    except Exception as exc:
        return False, f"exception: {exc}"


def check_compiled(builders: dict) -> tuple[bool, str]:
    try:
        for name, fn in builders.items():
            fn()
        return True, f"compiled={sorted(builders.keys())}"
    except Exception as exc:
        return False, f"compile error: {exc}"


def run_batch(runs: int) -> dict:
    import graph as g

    builders = {
        "daily": g.build_daily_graph,
        "validation": g.build_validation_graph,
        "radar": g.build_radar_graph,
        "multirepo": g.build_multirepo_graph,
    }
    try:
        v_app = g.build_validation_graph()
        m_app = g.build_multirepo_graph()
    except RuntimeError as exc:
        return {"ok": False, "error": str(exc), "iterations": []}
    iterations = []
    for i in range(1, runs + 1):
        start = time.monotonic()
        results = {}
        ok_pass, d_pass = scenario_validation_pass(v_app)
        results["validation-pass"] = {"ok": ok_pass, "detail": d_pass}
        ok_halt, d_halt = scenario_validation_halt(v_app)
        results["validation-halt"] = {"ok": ok_halt, "detail": d_halt}
        ok_mr, d_mr = scenario_multirepo(m_app)
        results["multirepo"] = {"ok": ok_mr, "detail": d_mr}
        ok_c, d_c = check_compiled(builders)
        results["compile-4"] = {"ok": ok_c, "detail": d_c}
        all_ok = all(v["ok"] for v in results.values())
        iterations.append({
            "n": i,
            "ok": all_ok,
            "elapsed_s": round(time.monotonic() - start, 3),
            "scenarios": results,
        })
    green = sum(1 for it in iterations if it["ok"])
    return {
        "ok": green == runs,
        "green": green,
        "total": runs,
        "target": TARGET_RUNS,
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "iterations": iterations,
    }


def default_out() -> Path:
    root = GRAPH.parents[1]
    logs = root / "logs"
    logs.mkdir(exist_ok=True)
    return logs / "kuro-graph-run-matrix.json"


def resolve_out(arg: str, default: Path) -> Path:
    """Confine --out dans le repo : refuse le path traversal (S8707)."""
    if not arg:
        return default
    root = GRAPH.parents[1].resolve()
    candidate = (root / arg).resolve() if not Path(arg).is_absolute() else Path(arg).resolve()
    try:
        candidate.relative_to(root)
    except Exception:
        raise ValueError(f"--out doit rester dans le repo: {arg}")
    return candidate


def main() -> int:
    ap = argparse.ArgumentParser(description="Harnais Q8 : batch de runs kuro-graph")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--out", default="")
    ap.add_argument("--append", action="store_true", help="cumule au rapport existant")
    args = ap.parse_args()
    if args.runs < 1 or args.runs > 30:
        print("runs doit etre entre 1 et 30")
        return 2
    report = run_batch(args.runs)
    try:
        out = resolve_out(args.out, default_out())
    except ValueError as exc:
        print(str(exc))
        return 2
    existing = []
    if args.append and out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8", errors="replace"))
            existing = prev.get("batches", [])
        except Exception:
            existing = []
    payload = {"batches": existing + [report]}
    cumulative = sum(b.get("green", 0) for b in payload["batches"])
    payload["cumulative_green"] = cumulative
    payload["target"] = TARGET_RUNS
    payload["go_nogo"] = "GO-candidate" if cumulative >= TARGET_RUNS else "NO-GO (runs insuffisants)"
    try:
        out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    except Exception as exc:
        print(f"ecriture rapport impossible: {exc}")
        return 1
    print(f"batch ok={report['ok']} green={report['green']}/{report['total']}")
    print(f"cumul={cumulative}/{TARGET_RUNS} verdict={payload['go_nogo']} rapport={out}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
