#!/usr/bin/env python3
"""kuro_dashboard.tui_textual — Xenon TUI : Glances Kuro riche (Textual, opt-in).

Le TUI ASCII (tui.py, zero dependance) reste le defaut : il marche partout
(console serveur 80 cols, Windows CP1252). Ce module demande Textual :

    pip install kuro-dashboard[textual]
    xenon-tui [--interval 2] [--top 10]
Ancien nom (alias déprécié) : kuro-glances-tui.

Layout : colonne principale (CPU/MEM + sparklines, disques/reseau,
TOP processus) + sidebar droite (visage + humeur, cerveau + couts LLM,
daemon Kuro). Refresh auto, `q` quitte, `espace` pause, `r` rafraichit.
"""

from __future__ import annotations

import argparse
import time
from typing import Any

from .face import mood_for
from .kuro_state import collect_kuro_snapshot
from .system import collect_system_snapshot
from .tui import _net_rates, _uptime, _usage_stats, fmt_bytes

try:
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical
    from textual.widgets import (
        DataTable,
        Footer,
        Header,
        Input,
        ProgressBar,
        Sparkline,
        Static,
    )
    _TEXTUAL_OK = True
    _TEXTUAL_ERR = ""
except Exception as exc:  # pragma: no cover - message d aide seulement
    _TEXTUAL_OK = False
    _TEXTUAL_ERR = str(exc)

MOOD_STYLES = {
    "happy": "green",
    "idle": "grey",
    "worried": "yellow",
    "critical": "red",
}

HIST_LEN = 60


class KuroApp(App):
    """Glances Kuro riche : main live + sidebar, refresh auto."""

    TITLE = "Glances Kuro"
    CSS_PATH = "kuro.tcss"
    BINDINGS = [
        Binding("q", "quit", "Quitter"),
        Binding("space", "toggle_pause", "Pause"),
        Binding("r", "refresh_now", "Rafraichir"),
        Binding("c", "sort_cpu", "Tri CPU"),
        Binding("m", "sort_mem", "Tri MEM"),
        Binding("slash", "filter", "Filtre"),
        Binding("enter", "detail", "Detail"),
        Binding("1", "toggle_kuro", "KURO"),
        Binding("2", "toggle_cpu", "CPU/MEM"),
        Binding("3", "toggle_net", "Reseau"),
        Binding("4", "toggle_proc", "Proc"),
        Binding("5", "toggle_market", "Marketing"),
    ]

    def __init__(self, interval: float = 2.0, top: int = 10) -> None:
        super().__init__()
        self._interval = max(0.5, interval)
        self._top = max(1, top)
        self._paused = False
        self._sort = "cpu"
        self._filt = ""
        self._procs: list = []
        self._detail_pid: int | None = None
        self._prev: dict | None = None
        self._prev_t: float | None = None
        self._cpu_hist: list[float] = []
        self._mem_hist: list[float] = []
        self._up_hist: list[float] = []
        self._down_hist: list[float] = []

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="main"):
                with Vertical(id="cpu-box", classes="box"):
                    yield ProgressBar(total=100, show_eta=False, id="cpu-bar")
                    yield Sparkline([], id="cpu-spark")
                    yield Static("", id="cpu-detail")
                    yield Static("", id="cores")
                with Vertical(id="mem-box", classes="box"):
                    yield ProgressBar(total=100, show_eta=False, id="mem-bar")
                    yield Sparkline([], id="mem-spark")
                    yield Static("", id="mem-detail")
                with Vertical(id="net-box", classes="box"):
                    yield Static("", id="net-detail")
                    yield Sparkline([], id="net-up-spark")
                    yield Sparkline([], id="net-down-spark")
                with Vertical(id="disk-box", classes="box"):
                    yield Static("", id="disk-net")
                with Vertical(id="proc-box", classes="box"):
                    yield Input(placeholder="filtrer (/ pour afficher, ENTREE valide, ECHAP efface)",
                                id="proc-filter", classes="hidden")
                    yield DataTable(id="procs")
                    yield Static("", id="detail")
                with Vertical(id="market-box", classes="box"):
                    yield Static("", id="market")
            with Vertical(id="sidebar"):
                with Vertical(id="face-box", classes="box"):
                    yield Static("", id="face")
                with Vertical(id="brain-box", classes="box"):
                    yield Static("", id="brain")
                with Vertical(id="kuro-box", classes="box"):
                    yield Static("", id="kuro")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#procs", DataTable)
        table.add_column("PID", width=8)
        table.add_column("Nom", width=28)
        table.add_column("CPU%", width=8)
        table.add_column("MEM%", width=8)
        self._refresh()
        self.set_interval(self._interval, self._tick)

    def _tick(self) -> None:
        if not self._paused:
            self._refresh()

    def action_toggle_pause(self) -> None:
        self._paused = not self._paused

    def action_refresh_now(self) -> None:
        self._refresh()

    def action_sort_cpu(self) -> None:
        self._sort = "cpu"
        self._refresh()
    def action_sort_mem(self) -> None:
        self._sort = "mem"
        self._refresh()

    def _toggle_boxes(self, *box_ids: str) -> None:
        try:
            for box_id in box_ids:
                self.query_one("#" + box_id).toggle_class("hidden")
        except Exception:
            pass

    def action_toggle_kuro(self) -> None:
        self._toggle_boxes("face-box", "brain-box", "kuro-box")

    def action_toggle_cpu(self) -> None:
        self._toggle_boxes("cpu-box", "mem-box")

    def action_toggle_net(self) -> None:
        self._toggle_boxes("net-box", "disk-box")

    def action_toggle_proc(self) -> None:
        self._toggle_boxes("proc-box")

    def action_toggle_market(self) -> None:
        self._toggle_boxes("market-box")

    def action_filter(self) -> None:
        box = self.query_one("#proc-filter", Input)
        if box.has_class("hidden"):
            box.remove_class("hidden")
            box.focus()
        else:
            box.add_class("hidden")
            box.value = ""
            self._filt = ""
            self._refresh()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "proc-filter":
            self._filt = (event.value or "").strip()[:20]
            event.input.add_class("hidden")
            self.set_focus(None)
            self._refresh()

    def action_detail(self) -> None:
        """Entree : fiche du processus sous le curseur (re-Entree : ferme)."""
        if self._detail_pid is not None:
            self._detail_pid = None
            self._render_detail()
            return
        try:
            table = self.query_one("#procs", DataTable)
            row = table.cursor_row
        except Exception:
            return
        try:
            if 0 <= row < len(self._procs):
                self._detail_pid = int(self._procs[row].get("pid"))
                self._render_detail()
        except Exception:
            return

    # -- rendu ---------------------------------------------------------
    def _refresh(self) -> None:
        try:
            snap = collect_system_snapshot(top_n=self._top)
            ksnap = collect_kuro_snapshot()
        except Exception:
            return
        now = time.monotonic()
        dt = (now - self._prev_t) if self._prev_t else self._interval
        try:
            cpu = (snap.get("cpu") or {}).get("percent") or 0.0
            mem = (snap.get("memory") or {}).get("percent") or 0.0
            self._cpu_hist = [*self._cpu_hist, float(cpu)][-HIST_LEN:]
            self._mem_hist = [*self._mem_hist, float(mem)][-HIST_LEN:]
            sent, recv = _net_rates(snap, self._prev, dt)
            self._up_hist = [*self._up_hist, float(sent or 0.0)][-HIST_LEN:]
            self._down_hist = [*self._down_hist, float(recv or 0.0)][-HIST_LEN:]
            self._render_bars(snap, float(cpu), float(mem))
            self._render_net(snap, sent, recv)
            self._render_disk_net(snap, dt)
            self._render_procs(snap)
            self._render_sidebar(snap, ksnap)
            self._render_market()
        except Exception:
            pass
        finally:
            self._prev, self._prev_t = snap, now

    def _title(self, box_id: str, text: str) -> None:
        try:
            self.query_one("#" + box_id).border_title = text
        except Exception:
            pass

    def _render_bars(self, snap: dict, cpu: float, mem: float) -> None:
        self._title("cpu-box", f"CPU {cpu:.0f}%")
        self._title("mem-box", f"MEMOIRE {mem:.0f}%")
        self.query_one("#cpu-bar", ProgressBar).update(progress=min(100.0, cpu))
        self.query_one("#mem-bar", ProgressBar).update(progress=min(100.0, mem))
        self.query_one("#cpu-spark", Sparkline).data = list(self._cpu_hist)
        self.query_one("#mem-spark", Sparkline).data = list(self._mem_hist)
        host = snap.get("host") or {}
        per = ((snap.get("cpu") or {}).get("per_cpu") or [])[:8]
        per_txt = "  ".join(f"c{i}:{v:.0f}%" for i, v in enumerate(per))
        self.query_one("#cpu-detail", Static).update(
            f"{cpu:.1f}%  ({host.get('cpu_count', '?')} coeurs)  {per_txt}")
        cores = ((snap.get("cpu") or {}).get("per_cpu") or [])[:8]
        if cores:
            try:
                from rich.text import Text as _Text
                t = _Text()
                for i, v in enumerate(cores):
                    f = min(12, max(0, int(float(v or 0.0) / 100 * 12)))
                    col = "red" if v >= 90 else ("yellow" if v >= 75 else "green")
                    t.append(f"c{i} ", style="dim")
                    t.append("#" * f + "-" * (12 - f), style=col)
                    t.append("  ")
                self.query_one("#cores", Static).update(t)
            except Exception:
                self.query_one("#cores", Static).update(per_txt)
        memd = snap.get("memory") or {}
        self.query_one("#mem-detail", Static).update(
            f"{mem:.1f}%  {fmt_bytes(memd.get('used'))} / {fmt_bytes(memd.get('total'))}")

    def _render_net(self, snap: dict, sent: float | None, recv: float | None) -> None:
        s_txt = fmt_bytes(sent) + "/s" if sent is not None else "n/a"
        r_txt = fmt_bytes(recv) + "/s" if recv is not None else "n/a"
        self._title("net-box", f"RESEAU ^ {s_txt} / v {r_txt}")
        self.query_one("#net-detail", Static).update(
            f"envoi {s_txt}  reception {r_txt}")
        self.query_one("#net-up-spark", Sparkline).data = list(self._up_hist)
        self.query_one("#net-down-spark", Sparkline).data = list(self._down_hist)

    def _render_disk_net(self, snap: dict, dt: float) -> None:
        self._title("disk-box", "DISQUES / CAPTEURS")
        lines = []
        for part in ((snap.get("disk") or {}).get("partitions") or [])[:4]:
            pct = part.get("percent")
            lines.append(f"{part.get('mount', '?'):>10} {pct if pct is not None else 'n/a':>5}%  "
                         f"{fmt_bytes(part.get('used'))} / {fmt_bytes(part.get('total'))}")
        temps = ((snap.get("sensors") or {}).get("temperatures") or [])[:3]
        if temps:
            lines.append("TEMP " + "  ".join(
                f"{t.get('label', '?')}:{t.get('current', '?')}C" for t in temps))
        for gpu in snap.get("gpu") or []:
            lines.append(f"GPU [{gpu.get('index')}] {gpu.get('name')} "
                         f"{gpu.get('util_percent')}% {gpu.get('temp_c')}C")
        docker = snap.get("docker") or {}
        if docker.get("available"):
            lines.append(f"DOCKER {docker.get('count')} conteneurs")
        self.query_one("#disk-net", Static).update("\n".join(lines) or "n/a")

    def _render_procs(self, snap: dict) -> None:
        title = f"PROCESSUS tri {self._sort.upper()}"
        if self._filt:
            title += f" /{self._filt[:20]}/"
        self._title("proc-box", title)
        table = self.query_one("#procs", DataTable)
        table.clear()
        procs = list(snap.get("processes") or [])
        key = "mem" if self._sort == "mem" else "cpu"
        try:
            procs.sort(key=lambda r: (r.get(key) or 0), reverse=True)
        except Exception:
            pass
        needle = (self._filt or "").lower()
        if needle:
            procs = [p for p in procs
                     if needle in str(p.get("name") or "").lower()]
        self._procs = procs[: self._top]
        for proc in self._procs:
            try:
                table.add_row(str(proc.get("pid", "?")),
                              str(proc.get("name") or "?")[:28],
                              f"{float(proc.get('cpu') or 0.0):.1f}",
                              f"{float(proc.get('mem') or 0.0):.1f}")
            except Exception:
                continue
        self._render_detail()

    def _render_detail(self) -> None:
        """Fiche detail du processus selectionne (live, disparait s il meurt)."""
        try:
            from .system import proc_detail as _proc_detail
            from .tui import sec_proc_detail
        except Exception:
            return
        try:
            box = self.query_one("#detail", Static)
        except Exception:
            return
        if self._detail_pid is None:
            box.update("")
            return
        try:
            info = _proc_detail(self._detail_pid)
        except Exception:
            info = None
        if not info:
            self._detail_pid = None
            box.update("")
            return
        try:
            box.update("\n".join(sec_proc_detail(info)))
        except Exception:
            box.update("")

    def _render_sidebar(self, snap: dict, kuro: dict | None) -> None:
        mood, reason = mood_for(snap, kuro)
        style = MOOD_STYLES.get(mood, "white")
        self._title("face-box", f"KURO {mood}")
        self._title("brain-box", "CERVEAU")
        self._title("kuro-box", "DAEMON")
        self.query_one("#face", Static).update(
            f"[{style}](^_^)\nhumeur : {mood} - {reason}[/]")
        brain_lines = self._brain_lines()
        self.query_one("#brain", Static).update("\n".join(brain_lines))
        self.query_one("#kuro", Static).update("\n".join(self._kuro_lines(kuro)))

    def _brain_lines(self) -> list[str]:
        try:
            from .tui import _legs_line, _read_brain, _rel_age, _short_model_name
            data = _read_brain()
        except Exception:
            data = None
        if not data:
            lines = ["cerveau : inconnu"]
        else:
            eng = str(data.get("engine") or "?")
            model = _short_model_name(data.get("model") or "")
            tag = f" [{model}]" if model and model != eng else ""
            age = _rel_age(data.get("at"))
            lines = [f"cerveau : {eng}{tag} ({data.get('latency_s', '?')}s"
                     f"{', ' + age if age else ''})"]
        try:
            from .tui import _pl, _unk_txt
            (calls_d, cost_d, unk_d, cache_d,
             calls_w, cost_w, unk_w, cache_w, top, lat) = _usage_stats()
        except Exception:
            return lines
        if calls_d or calls_w or cache_d or cache_w:
            lines.append(f"couts : ~${cost_d:.4f} auj. ({calls_d} {_pl(calls_d, 'appel')}"
                         f"{_unk_txt(unk_d)})")
            lines.append(f"~${cost_w:.4f} /7j ({calls_w} {_pl(calls_w, 'appel')}"
                         f"{_unk_txt(unk_w)}) top:{top} lat:{lat}s")
            if cache_d or cache_w:
                lines.append(f"cache : {cache_w} hits /7j (0 token)")
        try:
            lines.extend(_legs_line())
        except Exception:
            pass
        return lines

    def _kuro_lines(self, kuro: dict | None) -> list[str]:
        if not kuro:
            return ["KURO : donnees non chargees"]
        if not kuro.get("db_present"):
            return ["KURO : base absente", "daemon jamais lance ?"]
        age = kuro.get("heartbeat_age_min")
        if age is None:
            state, age_txt = "JAMAIS", "aucun battement"
        elif age < 5:
            state, age_txt = "SAIN", f"il y a {age:.0f} min"
        elif age < 15:
            state, age_txt = "STALE", f"il y a {age:.0f} min"
        else:
            state, age_txt = "MORT", f"il y a {age:.0f} min"
        try:
            eff = max(int(kuro.get("projects", 0) or 0),
                      int(kuro.get("repos_fs") or 0))
        except Exception:
            eff = kuro.get("projects", 0)
        lines = [f"daemon {state} ({age_txt})",
                 f"projets {eff}  alertes {kuro.get('alerts_open', 0)}",
                 f"sessions {kuro.get('sessions', 0)}  memoire {kuro.get('memory_nodes', 0)}"]
        for alert in (kuro.get("recent_alerts") or [])[:4]:
            lines.append(f"[{alert.get('severity', '?')}] "
                         f"{str(alert.get('message', ''))[:40]}")
        return lines

    def _render_market(self) -> None:
        self._title("market-box", "MARKETING")
        try:
            from .tui import sec_marketing, sec_strategy
            lines = [*sec_marketing(), *sec_strategy()]
        except Exception:
            lines = ["MARKETING (indisponible)"]
        try:
            self.query_one("#market", Static).update("\n".join(lines))
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Glances Kuro en TUI riche (Textual)")
    parser.add_argument("--interval", type=float, default=2.0)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args(argv)
    if not _TEXTUAL_OK:
        print("Textual manquant : pip install kuro-dashboard[textual]")
        if _TEXTUAL_ERR:
            print(f"({ _TEXTUAL_ERR})")
        return 1
    KuroApp(interval=args.interval, top=args.top).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
