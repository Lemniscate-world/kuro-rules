"""Assemblage des 3 graphes. Import langgraph lazy : scripts restent utilisables sans.

Usage :
    python -m apps.kuro-graph.graph --daily --dry-run
    python apps/kuro-graph/graph.py --validation --dry-run
    python apps/kuro-graph/graph.py --daily --full --no-dry-run --approve --thread-id run1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from state import STATE_VERSION, new_state


def _require_langgraph():
    try:
        from langgraph.graph import END, StateGraph  # type: ignore

        return END, StateGraph
    except Exception as exc:
        raise RuntimeError(
            "langgraph non installe. Installe apps/kuro-graph/requirements.txt "
            "ou utilise scripts/kuro_automate.py (zero-dependance)."
        ) from exc


def _checkpointer(thread_id: str = ""):
    # SqliteSaver si dispo (langgraph-checkpoint-sqlite), sinon None.
    # Le checkpoint fichier maison (utils.save_checkpoint) reste actif dans main().
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver  # type: ignore

        if thread_id:
            return SqliteSaver.from_conn_string(":memory:")
        return None
    except Exception:
        return None


def _wrap_daily():
    import nodes_daily as d
    import utils as u

    return {
        "doctor": u.timed(u.with_retry(d.node_doctor)),
        "truth": u.timed(u.with_retry(d.node_truth)),
        "portfolio": u.timed(d.node_portfolio),
        "strategy": u.timed(d.node_strategy),
        "publish": u.timed(d.node_publish),
        "should_publish": d.should_publish,
    }


def build_daily_graph(checkpointer=None):
    END, state_graph = _require_langgraph()
    d = _wrap_daily()

    g = state_graph(dict)
    g.add_node("doctor", d["doctor"])
    g.add_node("truth", d["truth"])
    g.add_node("portfolio", d["portfolio"])
    g.add_node("strategy", d["strategy"])
    g.add_node("publish", d["publish"])
    g.set_entry_point("doctor")
    g.add_edge("doctor", "truth")
    g.add_edge("truth", "portfolio")
    g.add_edge("portfolio", "strategy")
    g.add_conditional_edges("strategy", d["should_publish"], {"publish": "publish", "end": END})
    g.add_edge("publish", END)
    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


def build_validation_graph(checkpointer=None):
    END, state_graph = _require_langgraph()
    import nodes_validation as v
    import utils as u

    g = state_graph(dict)
    for stage in v.GATES:
        g.add_node(stage, u.timed(v.make_stage_node(stage)))
    g.set_entry_point(v.GATES[0])
    for i, stage in enumerate(v.GATES):
        nxt = v.next_after(stage)

        def _route(state, _s=stage, _n=nxt):
            if state.get("halted"):
                return "end"
            return "end" if _n == "end" else _n

        if nxt == "end":
            g.add_edge(stage, END)
        else:
            g.add_conditional_edges(stage, _route, {nxt: nxt, "end": END})
    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


def build_radar_graph(checkpointer=None):
    END, state_graph = _require_langgraph()
    import nodes_radar as r
    import utils as u

    g = state_graph(dict)
    g.add_node("collect", u.timed(r.node_collect))
    g.add_node("score", u.timed(r.node_score))
    g.add_node("draft", u.timed(r.node_draft))
    g.add_node("archive", u.timed(r.node_archive))
    g.set_entry_point("collect")
    g.add_edge("collect", "score")
    g.add_conditional_edges("score", r.route_radar, {"draft": "draft", "archive": "archive", "end": END})
    g.add_edge("draft", END)
    g.add_edge("archive", END)
    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


def build_multirepo_graph(checkpointer=None):
    END, state_graph = _require_langgraph()
    import nodes_multirepo as m
    import utils as u

    g = state_graph(dict)
    g.add_node("fanout", u.timed(m.node_fanout))
    g.add_node("impact", u.timed(m.node_impact))
    g.set_entry_point("fanout")
    g.add_conditional_edges("fanout", m.route_after_fanout, {"impact": "impact", "end": END})
    g.add_edge("impact", END)
    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


def _parse_args():
    ap = argparse.ArgumentParser(description="Kuro graphs POC")
    ap.add_argument("--daily", action="store_true")
    ap.add_argument("--validation", action="store_true")
    ap.add_argument("--radar", action="store_true")
    ap.add_argument("--multirepo", action="store_true")
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--no-dry-run", action="store_true", help="desactive dry-run (exige --full + --approve)")
    ap.add_argument("--full", action="store_true", help="autorise write=True")
    ap.add_argument("--approve", action="store_true", help="validation humaine explicite")
    ap.add_argument("--thread-id", default="", help="id de reprise checkpoint")
    ap.add_argument("--checkpoint", default="", help="chemin sqlite checkpoints")
    return ap.parse_args()


def _init_state(args):
    import utils as u

    dry_run = bool(args.dry_run and not args.no_dry_run)
    write = bool(args.full and not dry_run)
    state = new_state(write=write, dry_run=dry_run)
    state["human_approved"] = bool(args.approve and write and not dry_run)
    state["thread_id"] = str(args.thread_id or "")
    state["state_version"] = STATE_VERSION
    ckpt_path = u.checkpoint_path(args.checkpoint or None)
    # Reprise : si thread-id existe, on repart de l'etat sauvegarde.
    if state["thread_id"]:
        prev = u.load_checkpoint(ckpt_path, state["thread_id"])
        if isinstance(prev, dict) and prev.get("state_version") == STATE_VERSION:
            state = {**prev, "write": write, "dry_run": dry_run,
                     "human_approved": state["human_approved"], "thread_id": state["thread_id"]}
    return state, ckpt_path


def _pick_graph(args):
    which = "daily"
    if args.validation:
        which = "validation"
    elif args.radar:
        which = "radar"
    elif args.multirepo:
        which = "multirepo"
    elif not args.daily:
        which = "daily"
    builders = {"daily": build_daily_graph, "validation": build_validation_graph,
                "radar": build_radar_graph, "multirepo": build_multirepo_graph}
    try:
        saver = _checkpointer()
        return which, builders[which](checkpointer=saver)
    except RuntimeError as exc:
        print(str(exc))
        return which, None


def _invoke(app, state):
    if state.get("thread_id"):
        config = {"configurable": {"thread_id": state["thread_id"]}}
        try:
            return app.invoke(state, config=config)
        except Exception:
            pass
    return app.invoke(state)


def _report(which, state, result, ckpt_path):
    import utils as u

    summary = u.merge_metrics(result)
    print(f"graph={which} halted={result.get('halted')} fails={result.get('fails')} steps={sorted(result.get('steps', {}).keys())}")
    print(f"metrics durations={summary['durations']} retries={summary['retries']}")
    if state.get("thread_id"):
        ok = u.save_checkpoint(ckpt_path, state["thread_id"], result)
        print(f"checkpoint thread={state['thread_id']} saved={ok} path={ckpt_path}")
    try:
        init_metrics = dict(state.get("validation_results", {}))
    except Exception:
        init_metrics = {}
    if init_metrics:
        print(f"init_metrics_keys={sorted(init_metrics.keys())}")


def main() -> int:
    args = _parse_args()
    state, ckpt_path = _init_state(args)
    which, app = _pick_graph(args)
    if app is None:
        return 2
    result = _invoke(app, state)
    _report(which, state, result, ckpt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
