#!/usr/bin/env python3
"""make-demo-gif.py — genere packaging/demo.gif (PIL + Consolas, 100% offline).

24 frames de Xenon ASCII avec CPU sinusoidale, MEM en derive et
trafic reseau simule. Aucune donnee reelle, aucun reseau.
Usage : python scripts/make-demo-gif.py [--out packaging/demo.gif]
"""

from __future__ import annotations

import argparse
import math
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from kuro_dashboard import tui  # noqa: E402

FONT = r"C:\Windows\Fonts\CascadiaMono.ttf"  # mono sans ligatures (TUI aligne)
SIZE = 13
FRAMES = 24


def fake_payload(i: int) -> dict:
    cpu = 45 + 38 * math.sin(i / FRAMES * 2 * math.pi)
    mem = 55 + 10 * math.sin(i / FRAMES * 4 * math.pi + 1)
    per = [max(0.0, min(100.0, cpu + 12 * math.sin(i + j))) for j in range(4)]
    return {
        "generated_at": "demo",
        "psutil_available": True,
        "host": {"hostname": "demo", "system": "Linux", "cpu_count": 4},
        "cpu": {"percent": round(cpu, 1), "per_cpu": per,
                "load_avg": [1.2, 0.9, 0.7]},
        "memory": {"percent": round(mem, 1), "used": int(8e9 * mem / 100),
                   "total": 8_000_000_000, "swap_percent": 2.0},
        "disk": {"partitions": [{"mount": "/", "percent": 62.0,
                                 "used": 62_000_000_000, "total": 100_000_000_000}]},
        "network": {"io": {"bytes_sent": i * 50_000, "bytes_recv": i * 120_000}},
        "sensors": {"temperatures": [{"label": "cpu", "current": 58.0}]},
        "gpu": [],
        "docker": {"available": True, "count": 3},
        "processes": [
            {"pid": 101, "name": "python", "cpu": 34.2, "mem": 4.1},
            {"pid": 202, "name": "code", "cpu": 12.7, "mem": 8.9},
            {"pid": 303, "name": "docker", "cpu": 3.1, "mem": 2.2},
        ],
    }


def fake_kuro() -> dict:
    return {"db_present": True, "heartbeat": None, "heartbeat_age_min": 1.0,
            "projects": 55, "sessions": 12, "alerts_open": 2,
            "memory_nodes": 7, "repos_fs": 55, "summaries_fs": 22,
            "hb_projects_scanned": 0,
            "recent_alerts": [
                {"severity": "high", "message": "demo: charge CPU elevee",
                 "created_at": "demo", "project": "demo"},
            ]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="packaging/demo.gif")
    args = parser.parse_args()
    tui.term_width = lambda: 100
    tmp = Path(tempfile.mkdtemp())
    (tmp / "llm_usage.jsonl").write_text(
        '{"day": "2099-01-01", "at": "2099-01-01 10:00:00", "engine": "openrouter",'
        ' "latency_s": 3.2, "prompt_chars": 400, "resp_chars": 800,'
        ' "est_tokens": 300, "est_cost_usd": 0.0009}\n', encoding="utf-8")
    tui.LLM_USAGE_FILE = tmp / "llm_usage.jsonl"
    # fige "aujourd hui" sur 2099 pour que la ligne couts s affiche
    import datetime as _dt

    class _Date(_dt.date):
        @classmethod
        def today(cls):
            return cls(2099, 1, 1)

    _dt.date = _Date

    from PIL import Image, ImageDraw, ImageFont
    font = ImageFont.truetype(FONT, SIZE)
    box = font.getbbox("M")
    ascent, descent = font.getmetrics()
    cw, ch = box[2] - box[0] + 1, ascent + descent + 5
    prev = None
    hist: dict[str, list] = {"cpu": [], "mem": [], "up": [], "down": []}
    images = []
    for i in range(FRAMES):
        snap = fake_payload(i)
        dt = 0.5
        hist["cpu"].append(snap["cpu"]["percent"])
        hist["mem"].append(snap["memory"]["percent"])
        sent, recv = tui._net_rates(snap, prev, dt)
        hist["up"].append(sent)
        hist["down"].append(recv)
        frame = tui.render_frame(snap, prev, dt, fake_kuro(), now=float(i) * 0.5,
                                 hist=hist)
        prev = snap
        rows = frame.splitlines()
        img = Image.new("RGB", (100 * cw + 16, len(rows) * ch + 12), "#0d1117")
        draw = ImageDraw.Draw(img)
        for j, row in enumerate(rows):
            draw.text((8, 6 + j * ch), row, font=font, fill="#e6edf3")
        images.append(img)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(out, save_all=True, append_images=images[1:],
                   duration=400, loop=0)
    print(f"[OK] {out} ({out.stat().st_size} octets, {FRAMES} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
