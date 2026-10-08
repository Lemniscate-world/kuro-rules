#!/usr/bin/env python3
"""kuro_dashboard.tui — Xenon : Glances Kuro en terminal (live, zero dependance).

Le vrai Glances : plein terminal, refresh auto, `q` pour quitter.
Sans terminal (pipe, CI) : affiche UNE frame et sort (jamais de boucle).

Usage :
    xenon [--interval 2] [--top 10] [--no-color]
    python -m kuro_dashboard.tui [--interval 2] [--top 10]
Ancien nom (alias déprécié) : kuro-glances.
Touches en live : q quitter, espace pause, c/m tri CPU/MEM, / filtre nom,
Haut/Bas selection, Entree fiche detail, 1-7 montre/cache boxes,
r refresh, +/- vitesse. Couleurs ANSI (coupees hors tty, avec NO_COLOR/--no-color).
Box 5 MARKETING : pipeline local + drafts LAUNCH_POSTS + tracker acquisition.
Box 6 STRATÉGIE : runway/velocite/OKR (strategy_history.local.json).
Box 7 SEO : audit ~/leads/SEO_AUDIT.md (serveur ; absent sur PC = message honnête).
"""

from __future__ import annotations

import argparse
import functools
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from .agents import agents_lines
from .face import face_frame, mood_for, should_blink, spinner
from .kuro_state import collect_kuro_snapshot
from .projects import quick_lines as git_project_lines
from .system import collect_system_snapshot


def _load_dotenv() -> None:
    """Repli .env local si les cles ne sont pas dans l'environnement.

    Meme role que dans scripts/kuro_llm.py mais sans l'importer (Xenon reste
    sans dependance ni reseau a l'import) : sinon la ligne "jambes" affiche
    tout "off" quand Xenon est lance depuis un contexte sans env. setdefault
    uniquement, jamais de secret journalise, jamais d'exception.
    """
    try:
        root = os.environ.get("KURO_RULES_DIR")
        repo = Path(root) if root else Path(__file__).resolve().parent.parent.parent
        env_path = repo / ".env"
        if not env_path.exists():
            return
        for line in env_path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip().strip('"').strip("'")
    except Exception:
        pass


_load_dotenv()

DEFAULT_INTERVAL = 2.0
LLM_LAST_FILE = Path.home() / ".kuro" / "llm_last.json"
LLM_USAGE_FILE = Path.home() / ".kuro" / "llm_usage.jsonl"
HIST_LEN = 48
WIDE_MIN_WIDTH = 150
SIDEBAR_WIDTH = 46
SPARK_CHARS = " .:-=+*#@"
_COLOR = True
ANSI = {"ok": "\x1b[32m", "warn": "\x1b[33m", "crit": "\x1b[31m",
        "dim": "\x1b[2m", "reset": "\x1b[0m", "blue": "\x1b[34m",
        "magenta": "\x1b[35m", "cyan": "\x1b[36m"}
_PAINT_LEVELS = ("ok", "warn", "crit", "dim", "blue", "magenta", "cyan")
MOOD_COLORS = {"happy": "ok", "idle": "dim", "worried": "warn",
               "critical": "crit"}


def _stdout_is_tty() -> bool:
    """stdout est-il un terminal ? Jamais d'exception (pipe ferme, etc.)."""
    try:
        return bool(sys.stdout.isatty())
    except Exception:
        return False


def _colors_on() -> bool:
    """Couleurs si terminal reel + autorise (NO_COLOR et --no-color coupent).

    KURO_FORCE_COLOR=1 force pour demos/captures (pipe compris).
    Jamais d'exception : un stdout exotique (pipe ferme, console
    minimale) ne doit pas tuer le rendu — vu en prod, frame perdue.
    """
    try:
        if os.environ.get("KURO_FORCE_COLOR") == "1":
            return bool(_COLOR)
        return bool(_COLOR) and sys.stdout.isatty() and os.environ.get("NO_COLOR") is None
    except Exception:
        return False


def _paint(text: str, level: str, use_color: bool) -> str:
    if not use_color or level not in _PAINT_LEVELS:
        return text
    return f"{ANSI[level]}{text}{ANSI['reset']}"


def _level(pct: Any, warn: float = 75.0, crit: float = 90.0) -> str:
    try:
        value = float(pct)
    except (TypeError, ValueError):
        return "dim"
    if value >= crit:
        return "crit"
    if value >= warn:
        return "warn"
    return "ok"


def _ioctl_size() -> tuple | None:
    """Taille reelle du terminal via ioctl (ignore COLUMNS/LINES perimees)."""
    try:
        import fcntl
        import struct
        import termios

        for fd in (sys.__stdout__.fileno(), sys.__stdin__.fileno()):
            try:
                h, w, _hp, _wp = struct.unpack(
                    "HHHH", fcntl.ioctl(fd, termios.TIOCGWINSZ,
                                        struct.pack("HHHH", 0, 0, 0, 0)))
                if w >= 20 and h >= 5:
                    return w, h
            except Exception:
                continue
    except Exception:
        pass
    return None


def term_width() -> int:
    size = _ioctl_size()
    if size:
        return max(60, size[0])
    try:
        return max(60, shutil.get_terminal_size((100, 30)).columns)
    except Exception:
        return 100


def term_height() -> int:
    size = _ioctl_size()
    if size:
        return max(10, size[1])
    try:
        return max(10, shutil.get_terminal_size((100, 30)).lines)
    except Exception:
        return 24


# Plages Unicode larges (2 colonnes) et zero-largeur, version compacte de
# wcwidth (zero dependance : pas de paquet externe pour un test de largeur).
_WIDE_RANGES = (
    (0x1100, 0x115F), (0x231A, 0x231B), (0x2329, 0x232A),
    (0x23E9, 0x23EC), (0x23F0, 0x23F0), (0x23F3, 0x23F3),
    (0x25FD, 0x25FE), (0x2614, 0x2615), (0x2648, 0x2653),
    (0x267F, 0x267F), (0x2693, 0x269D), (0x26A1, 0x26A1),
    (0x26AA, 0x26AB), (0x26BD, 0x26BE), (0x26C4, 0x26C5),
    (0x26CE, 0x26CE), (0x26D4, 0x26D4), (0x26EA, 0x26EA),
    (0x26F2, 0x26F3), (0x26F5, 0x26F5), (0x26FA, 0x26FA),
    (0x26FD, 0x26FD), (0x2705, 0x2705), (0x270A, 0x270B),
    (0x2728, 0x2728), (0x274C, 0x274C), (0x274E, 0x274E),
    (0x2753, 0x2755), (0x2757, 0x2757), (0x2795, 0x2797),
    (0x27B0, 0x27B0), (0x27BF, 0x27BF), (0x2B1B, 0x2B1C),
    (0x2B50, 0x2B50), (0x2B55, 0x2B55), (0x2E80, 0x2E99),
    (0x2E9B, 0x2EF3), (0x2F00, 0x2FD5), (0x2FF0, 0x2FFB),
    (0x3000, 0x303E), (0x3041, 0x3096), (0x3099, 0x30FF),
    (0x3105, 0x312D), (0x3131, 0x318E), (0x3190, 0x31BA),
    (0x31C0, 0x31E3), (0x31F0, 0x321E), (0x3220, 0x3247),
    (0x3250, 0x32FE), (0x3300, 0x4DBF), (0x4E00, 0xA4CF),
    (0xA960, 0xA97C), (0xAC00, 0xD7A3), (0xF900, 0xFAFF),
    (0xFE30, 0xFE4F), (0xFF00, 0xFF60), (0xFFE0, 0xFFE6),
    (0x1F300, 0x1FAFF), (0x20000, 0x3FFFD),
)
_ZERO_RANGES = (
    (0x0300, 0x036F), (0x0483, 0x0489), (0x0591, 0x05BD),
    (0x0610, 0x061A), (0x064B, 0x065F), (0x0670, 0x0670),
    (0x06D6, 0x06DC), (0x200B, 0x200F), (0xFE00, 0xFE0F),
    (0xFE20, 0xFE2F), (0xE0100, 0xE01EF),
)


def _char_width(ch: str) -> int:
    """Largeur terminal d un caractere : 0, 1 ou 2 (jamais d exception)."""
    try:
        o = ord(ch)
        if o < 0x20 or o == 0x7F:
            return 0
        for lo, hi in _ZERO_RANGES:
            if lo <= o <= hi:
                return 0
        for lo, hi in _WIDE_RANGES:
            if lo <= o <= hi:
                return 2
        return 1
    except Exception:
        return 1


def _visible_width(text: str) -> int:
    """Largeur visible : ignores escapes ANSI, emojis/CJK = 2."""
    try:
        total, i = 0, 0
        while i < len(text):
            if text[i] == "\x1b" and i + 1 < len(text) and text[i + 1] == "[":
                j = text.find("m", i)
                if 0 <= j - i <= 16:
                    i = j + 1
                    continue
                i += 1
                continue
            total += _char_width(text[i])
            i += 1
        return total
    except Exception:
        return len(text)


def _fit(line: Any, width: int) -> str:
    """Coupe une ligne a `width` colonnes visibles, sans casser les escapes ANSI."""
    try:
        # Tabulations et controles invisibles : le terminal les rend sur
        # plusieurs colonnes (\t) ou casse la ligne (\r) -> neutralise.
        text = str(line).expandtabs(4)
        text = "".join(ch for ch in text
                       if ch == "\x1b" or ord(ch) >= 0x20)
        # Coupe-circuit : une ligne saine fait < 4x la largeur (ANSI inclus).
        # Sans borne, une ligne pathologique (Mo de JSON) bloque le rendu.
        cap = max(256, int(width) * 4 + 64)
        if len(text) > cap:
            text = text[:cap]
        if _visible_width(text) <= width and "\x1b" not in text:
            return text
        out: list[str] = []
        vis = 0
        i = 0
        while i < len(text):
            ch = text[i]
            if ch == "\x1b" and i + 1 < len(text) and text[i + 1] == "[":
                j = text.find("m", i)
                if j == -1 or j - i > 16:
                    i += 1
                    continue
                out.append(text[i:j + 1])
                i = j + 1
                continue
            w = _char_width(ch)
            if vis + w > width:
                break
            out.append(ch)
            vis += w
            i += 1
        s = "".join(out)
        if "\x1b" in text and ANSI["reset"] not in s:
            s += ANSI["reset"]
        return s
    except Exception:
        try:
            return str(line)[:width]
        except Exception:
            return ""


def _vpad(text: str, width: int) -> str:
    """Pad avec des espaces jusqu a `width` colonnes visibles."""
    try:
        pad = max(0, width - _visible_width(text))
        return text + " " * pad
    except Exception:
        return text


def _split_ansi(text: str) -> list[tuple[str, str]]:
    """Decoupe en segments (style_actif, morceau_visible). Jamais d exception."""
    segs: list[tuple[str, str]] = []
    try:
        cur = ""
        i = 0
        buf: list[str] = []
        while i < len(text):
            if text[i] == "\x1b" and i + 1 < len(text) and text[i + 1] == "[":
                j = text.find("m", i)
                if 0 <= j - i <= 16:
                    if buf:
                        segs.append((cur, "".join(buf)))
                        buf = []
                    cur = text[i:j + 1]
                    if cur == ANSI["reset"]:
                        cur = ""
                    i = j + 1
                    continue
            buf.append(text[i])
            i += 1
        if buf:
            segs.append((cur, "".join(buf)))
        return segs
    except Exception:
        return [("", text)]


def _wrap(text: str, width: int, max_lines: int = 4) -> list[str]:
    """Enroule une phrase sur plusieurs lignes (mots entiers, style ANSIporte).

    Le surplus au-dela de max_lines est coupe avec "..." (ASCII).
    """
    try:
        if _visible_width(text) <= width:
            return [text]
        words: list[tuple[str, str]] = []
        for style, chunk in _split_ansi(text):
            for word in chunk.split(" "):
                words.append((style, word))
        lines: list[str] = []
        cur_style = ""
        cur_text = ""
        cur_vis = 0
        for style, word in words:
            w = _visible_width(word)
            if w > width:  # mot geant : coupe dure
                if cur_text:
                    lines.append(cur_style + cur_text)
                    cur_text, cur_vis = "", 0
                cut = _fit(word if not style else style + word, width)
                lines.append(cut)
                cur_style = style
                continue
            sep = 1 if cur_text else 0
            if cur_vis + sep + w > width:
                lines.append(cur_style + cur_text if cur_style else cur_text)
                cur_text, cur_vis = "", 0
                sep = 0
            if style != cur_style:
                cur_style = style
            cur_text += (" " if sep else "") + word
            cur_vis += sep + w
        if cur_text:
            lines.append(cur_style + cur_text if cur_style else cur_text)
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            lines[-1] = _fit(lines[-1], max(0, width - 3)) + "..."
        out = []
        for line in lines:
            if "\x1b" in line and ANSI["reset"] not in line:
                line += ANSI["reset"]
            out.append(line)
        return out or [text[:width]]
    except Exception:
        return [_fit(text, width)]


def bar(pct: float | None, width: int = 24, color: str | None = None) -> str:
    """Barre ASCII : [####------] (jamais d Unicode, consoles Windows)."""
    if pct is None:
        return "[" + "?" * width + "]"
    filled = min(width, max(0, round(pct / 100 * width)))
    fill = "#" * filled
    if fill and color in _PAINT_LEVELS:
        fill = f"{ANSI[color]}{fill}{ANSI['reset']}"
    return "[" + fill + "-" * (width - filled) + "]"


def fmt_bytes(value: Any) -> str:
    if value is None:
        return "n/a"
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "n/a"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024.0 or unit == "TB":
            return f"{int(num)} B" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} TB"  # pragma: no cover - TB matche toujours ci-dessus


def fmt_rate(bytes_per_s: float | None) -> str:
    if bytes_per_s is None:
        return "n/a"
    return fmt_bytes(bytes_per_s) + "/s"


def _net_rates(cur: dict, prev: dict | None, dt: float) -> tuple:
    """Debit reseau octet/s depuis 2 snapshots (None si pas calculable)."""
    if not prev or dt <= 0:
        return None, None
    try:
        io, pio = cur["network"]["io"], prev["network"]["io"]
        sent = (io.get("bytes_sent", 0) - pio.get("bytes_sent", 0)) / dt
        recv = (io.get("bytes_recv", 0) - pio.get("bytes_recv", 0)) / dt
        return max(0.0, sent), max(0.0, recv)
    except Exception:
        return None, None


def _uptime() -> str:
    try:
        import psutil

        secs = int(time.time() - psutil.boot_time())
    except Exception:
        return "n/a"
    days, secs = divmod(secs, 86400)
    hours, secs = divmod(secs, 3600)
    mins, _secs = divmod(secs, 60)
    return f"{days}j {hours}h {mins}m" if days else f"{hours}h {mins}m"


def sec_header(payload: dict) -> list[str]:
    host = payload.get("host", {})
    load = (payload.get("cpu") or {}).get("load_avg") or []
    load_txt = " / ".join(f"{v:.2f}" for v in load[:3]) or "n/a"
    return [
        f"GLANCES KURO  {host.get('hostname', '?')}  "
        f"{host.get('system', '?')}  up { _uptime()}  load {load_txt}  "
        f"{time.strftime('%H:%M:%S')}",
        f"genere a {payload.get('generated_at', '?')}  "
        f"(psutil: {payload.get('psutil_available')})",
    ]


def spark(values: list | None, width: int = 24) -> str:
    """Sparkline ASCII (jamais d Unicode) : ' .:-=+*#' selon amplitude."""
    try:
        vals = [float(v) for v in (values or []) if v is not None][-width:]
    except Exception:
        return "?" * width
    if not vals:
        return " " * width
    mx = max(vals)
    if mx <= 0:
        return " " * width
    seq = "".join(SPARK_CHARS[min(8, int(v / mx * 8))] for v in vals)
    return seq.rjust(width, " ")


def _swap_rates(cur: dict, prev: dict | None, dt: float) -> tuple:
    """Pagination swap (pages/s) depuis 2 snapshots (None si pas calculable)."""
    if not prev or dt <= 0:
        return None, None
    try:
        mem, pmem = cur.get("memory") or {}, (prev.get("memory") or {})
        sin = ((mem.get("swap_sin") or 0) - (pmem.get("swap_sin") or 0)) / dt
        sout = ((mem.get("swap_sout") or 0) - (pmem.get("swap_sout") or 0)) / dt
        if mem.get("swap_sin") is None or pmem.get("swap_sin") is None:
            return None, None
        return max(0.0, sin), max(0.0, sout)
    except Exception:
        return None, None


def _disk_busy(cur: dict, prev: dict | None, dt: float) -> float | None:
    """% de temps disques occupes (read+write time) entre 2 snapshots.

    Exige les 4 compteurs (psutil les documente optionnels par plateforme) :
    sinon le cumul courant passerait pour un intervalle -> faux 100%.
    """
    if not prev or dt <= 0:
        return None
    try:
        io, pio = (cur.get("disk") or {}).get("io") or {}, \
            (prev.get("disk") or {}).get("io") or {}
        vals = [io.get("read_time"), io.get("write_time"),
                pio.get("read_time"), pio.get("write_time")]
        if any(v is None for v in vals):
            return None
        busy_ms = ((io["read_time"] - pio["read_time"])
                   + (io["write_time"] - pio["write_time"]))
        return min(100.0, max(0.0, busy_ms / (dt * 1000) * 100))
    except Exception:
        return None


def sec_cpu_mem(payload: dict, hist: dict | None = None, width: int = 0,
                prev: dict | None = None, dt: float = 0.0) -> list[str]:
    use = _colors_on()
    cpu = payload.get("cpu") or {}
    mem = payload.get("memory") or {}
    cpu_p, mem_p = cpu.get("percent"), mem.get("percent")
    cpu_txt = f"{cpu_p}%" if cpu_p is not None else "n/a%"
    mem_txt = f"{mem_p}%" if mem_p is not None else "n/a%"
    lines = []
    if width:
        lines.append(_div("processeur", width))
    lines.append(
        f"CPU  {bar(cpu_p, color=_level(cpu_p) if use else None)} "
        f"{_paint(cpu_txt, _level(cpu_p), use)}  "
        f"({(payload.get('host') or {}).get('cpu_count', '?')} coeurs)")
    per = (cpu.get("per_cpu") or [])[:8]
    if per:
        lines.append("     " + "  ".join(f"c{i}:{v:.0f}%" for i, v in enumerate(per)))
    load = (cpu.get("load_avg") or [])[:1]
    cores = (payload.get("host") or {}).get("cpu_count") or 0
    if load and cores:
        try:
            sat = float(load[0]) / float(cores)
            flag = "  << file d attente !" if sat >= 1 else ""
            lines.append(f"     charge 1min {float(load[0]):.2f} / {cores} coeurs{flag}")
        except Exception:
            pass
    if hist and len([v for v in (hist.get("cpu") or []) if v is not None]) >= 2:
        gw = max(24, min(term_width(), 100) - 14)
        lines.append(f"CPU graph [{spark(hist.get('cpu'), gw)}]")
    if width:
        lines.append(_div("memoire", width))
    lines.append(
        f"MEM  {bar(mem_p, color=_level(mem_p) if use else None)} "
        f"{_paint(mem_txt, _level(mem_p), use)}  "
        f"{fmt_bytes(mem.get('used'))} / {fmt_bytes(mem.get('total'))}")
    swap = mem.get("swap_percent")
    if swap is not None:
        lines.append(f"SWAP {bar(swap, color=_level(swap) if use else None)} {swap}%")
    sin, sout = _swap_rates(payload, prev, dt)
    if sin is not None and sout is not None and (sin > 0 or sout > 0):
        lines.append(f"     pagination swap : {sin:.0f} pages/s entree, "
                     f"{sout:.0f} pages/s sortie (saturation memoire !)")
    if hist:
        lines.append(f"MEM hist [{spark(hist.get('mem'), 24)}]")
    return lines


def sec_disk_net(payload: dict, prev: dict | None, dt: float,
                 hist: dict | None = None, width: int = 0,
                 max_parts: int = 4) -> list[str]:
    use = _colors_on()
    lines = []
    if width:
        lines.append(_div("disques", width))
    parts = ((payload.get("disk") or {}).get("partitions") or [])[:max(1, max_parts)]
    if not parts:
        lines.append("DISK n/a (aucun disque detecte)")
    for part in parts:
        pct = part.get("percent")
        pct_txt = f"{pct}%" if pct is not None else "n/a%"
        lines.append(
            f"DISK {part.get('mount', '?'):<10} {bar(pct, color=_level(pct, 85, 95) if use else None)} "
            f"{_paint(pct_txt, _level(pct, 85, 95), use)}  "
            f"{fmt_bytes(part.get('used'))} / {fmt_bytes(part.get('total'))}"
        )
    if width:
        lines.append(_div("reseau", width))
    sent, recv = _net_rates(payload, prev, dt)
    lines.append(f"NET  envoi {fmt_rate(sent):>12}  reception {fmt_rate(recv):>12}")
    busy = _disk_busy(payload, prev, dt)
    if busy is not None:
        lines.append(f"     disques occupes a {busy:.0f}% "
                     f"{'<< saturation I/O !' if busy >= 90 else ''}".rstrip())
    try:
        io = (payload.get("network") or {}).get("io") or {}
        errs = sum(int(io.get(k) or 0) for k in
                   ("errin", "errout", "dropin", "dropout"))
    except Exception:
        errs = 0
    if errs:
        lines.append(f"     reseau : {errs} erreurs/pertes cumulees (a surveiller)")
    if hist and len([v for v in (hist.get("up") or []) if v is not None]) >= 2:
        lines.append(f"UP   [{spark(hist.get('up'), 24)}] {fmt_rate(sent)}")
        lines.append(f"DOWN [{spark(hist.get('down'), 24)}] {fmt_rate(recv)}")
    return lines


def sec_extra(payload: dict) -> list[str]:
    lines = []
    temps = ((payload.get("sensors") or {}).get("temperatures") or [])[:3]
    if temps:
        lines.append("TEMP " + "  ".join(
            f"{t.get('label', '?')}:{t.get('current', '?')}C" for t in temps))
    for gpu in payload.get("gpu") or []:
        lines.append(f"GPU  [{gpu.get('index')}] {gpu.get('name')} "
                     f"{gpu.get('util_percent')}%  {gpu.get('temp_c')}C")
    docker = payload.get("docker") or {}
    if docker.get("available"):
        lines.append(f"DOCKER {docker.get('count')} conteneurs")
    return lines


def _num(value: Any) -> str:
    """Nombre 1 decimale, n/a si absent (affichage propre des processus)."""
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "n/a"


def sec_procs(payload: dict, width: int, sort: str = "cpu", filt: str = "",
              sel: int = -1, limit: int = 10) -> list[str]:
    title = f"TOP PROCESSUS  (tri {sort.upper()})"
    if filt:
        title += f"  [filtre:{filt[:20]}]"
    lines = [title]
    try:
        states = payload.get("process_states") or {}
        # waiting = normal sur Windows/macOS (psutil), idle/? = fond.
        weird = {k: v for k, v in states.items()
                 if k not in ("running", "sleeping", "waiting", "idle", "?", "") and v}
        if weird:
            lines.append("  etats anormaux : " + ", ".join(
                f"{v} {k}" for k, v in sorted(weird.items())))
    except Exception:
        pass
    procs = _visible_procs(payload, sort, filt)
    for idx, proc in enumerate(procs[: max(1, limit)]):
        name = str(proc.get("name") or "?")[: width - 40]
        mark = ">" if idx == sel else " "
        lines.append(f"{mark} {str(proc.get('pid', '?')):>7}  {name:<{width - 40}}  "
                     f"CPU {_num(proc.get('cpu')):>6}  MEM {_num(proc.get('mem')):>6}")
    if len(lines) == 1:
        if filt:
            lines.append("  (aucun processus ne correspond au filtre, ENTREE vide pour effacer)")
        else:
            lines.append("  (liste indisponible : installez psutil sur l hote)")
    return lines


def sec_proc_detail(info: dict | None) -> list[str]:
    """Fiche detail d un processus (pur, jamais d exception)."""
    if not info:
        return []
    try:
        from datetime import datetime
        born = datetime.fromtimestamp(float(info.get("created") or 0)).strftime(
            "%Y-%m-%d %H:%M:%S") if info.get("created") else "?"
    except Exception:
        born = "?"
    cpu_txt = (f"{info['cpu_user']:.1f}s user / {info['cpu_sys']:.1f}s sys"
               if info.get("cpu_user") is not None else "n/a")
    return [
        f"DETAIL pid {info.get('pid', '?')} ({info.get('name', '?')})",
        f"  cmd : {str(info.get('cmd') or '(inconnu)')[:120]}",
        f"  user : {info.get('user', '?')}  etat : {info.get('status', '?')}  "
        f"threads : {info.get('threads', '?')}",
        f"  mem : {fmt_bytes(info.get('rss'))}  cpu : {cpu_txt}",
        f"  demarre : {born}",
    ]


def sec_kuro(kuro: dict | None) -> list[str]:
    """Section Kuro : daemon + compteurs effectifs + dernieres alertes (DB locale)."""
    if not kuro:
        return ["KURO donnees non chargees"]
    if not kuro.get("db_present"):
        return ["KURO base absente (~/.kuro/kuro.db) : daemon jamais lance ?"]
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
        db_proj = int(kuro.get("projects", 0) or 0)
    except Exception:
        db_proj = 0
    repos = kuro.get("repos_fs")
    sums = kuro.get("summaries_fs")
    scanned = kuro.get("hb_projects_scanned")
    # Compteurs effectifs : la table DB legacy est souvent vide (daemon actuel
    # n y ecrit plus) -> repli sur les signaux disque reels.
    try:
        eff_proj = max(db_proj, int(repos) if repos is not None else 0)
    except Exception:
        eff_proj = db_proj
    lines = [f"KURO daemon {state} ({age_txt})  projets {eff_proj}  "
             f"sessions {kuro.get('sessions', 0)}  alertes {kuro.get('alerts_open', 0)}  "
             f"memoire {kuro.get('memory_nodes', 0)}"]
    try:
        file_age = float(kuro.get("file_age_min") or 0)
    except Exception:
        file_age = 0.0
    if file_age > 15:
        lines[0] += f"  [fichier vieux de {file_age:.0f} min]"
    replica = kuro.get("replica") or {}
    if replica:
        lines.append(f"  replica : {replica.get('projects', '?')} projets "
                     f"(vieux de {(replica.get('file_age_min') or 0):.0f} min)")
    if repos is not None or sums is not None or scanned is not None:
        lines[0] += (f"  [reel: {repos if repos is not None else '?'} repos, "
                     f"{sums if sums is not None else '?'} summaries, "
                     f"scan {scanned if scanned is not None else '?'}]")
    for alert in (kuro.get("recent_alerts") or [])[:5]:
        proj = f" [{alert.get('project')}]" if alert.get("project") else ""
        lines.append(f"  [{alert.get('severity', '?')}]"
                     f"{str(alert.get('message', ''))} ({alert.get('created_at', '?')}){proj}")
    return lines


def sec_face(payload: dict, kuro: dict | None, now: float | None) -> list[str]:
    """Visage + humeur de Kuro (etat reel, jamais decoratif seul)."""
    from .face import LABELS

    mood, reason = mood_for(payload, kuro)
    art = face_frame(mood, should_blink(now))
    label = LABELS.get(mood, mood)
    label = _paint(label, MOOD_COLORS.get(mood, "ok"), _colors_on())
    return [*art, f"humeur : {label} {spinner(now)} - {reason}"]


def _read_brain() -> dict | None:
    try:
        data = json.loads(LLM_LAST_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


# Moteurs qui ne sont pas des appels LLM : le cache local (0 token,
# instantane) et le mode deterministe (que des echecs) gonflaient les
# "appels" et ecrasaient la latence moyenne vers 0. Ils sont comptes a
# part (hits) et exclus des stats d appels.
_NON_CALL_ENGINES = {"", "cache", "deterministe"}


def _latency_pcts() -> dict:
    """P50/P95 des latences d appels reels 7 j (cache/deterministe exclus).

    La moyenne seule cachait les stalls (ex : 20 min noyees dans 8,1 s).
    Renvoie {} si moins de 2 valeurs.
    """
    lats: list[float] = []
    try:
        from datetime import date, timedelta
        week_ago = (date.today() - timedelta(days=6)).isoformat()
        lines = LLM_USAGE_FILE.read_text(encoding="utf-8").splitlines()[-2000:]
    except Exception:
        return {}
    for line in lines:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict) or (e.get("day") or "") < week_ago:
            continue
        if str(e.get("engine") or "?") in _NON_CALL_ENGINES:
            continue
        try:
            lats.append(float(e.get("latency_s") or 0.0))
        except Exception:
            continue
    if len(lats) < 2:
        return {}
    ordered = sorted(lats)

    def _pct(p: float) -> float:
        try:
            idx = min(len(ordered) - 1, max(0, int(round((p / 100) * (len(ordered) - 1)))))
            return round(ordered[idx], 1)
        except Exception:
            return 0.0

    return {"p50": _pct(50), "p95": _pct(95)}


def _pl(n: int, sing: str, plur: str | None = None) -> str:
    """Pluriel francais : 1 appel, 0/2+ appels. Jamais d exception."""
    try:
        return sing if int(n) == 1 else (plur if plur else sing + "s")
    except Exception:
        return plur if plur else sing + "s"


def _usage_stats() -> tuple:
    """Stats 7 j sur les VRAIS appels LLM (cache/deterministe exclus).

    (appels_auj, cout_auj, couts_inconnus_auj, hits_cache_auj,
     appels_7j, cout_7j, couts_inconnus_7j, hits_cache_7j,
     top_moteur, lat_moy).
    cout inconnu = modele payant non tarife (prix null, pas $0 menteur).
    """
    zero = (0, 0.0, 0, 0, 0, 0.0, 0, 0, "?", "?")
    calls_d = cache_d = calls_w = cache_w = 0
    cost_d = cost_w = 0.0
    unk_d = unk_w = 0
    lat_sum = 0.0
    lat_n = 0
    engines: dict[str, int] = {}
    try:
        from datetime import date, timedelta
        today = date.today()
        week_ago = (today - timedelta(days=6)).isoformat()
        today_s = today.isoformat()
        lines = LLM_USAGE_FILE.read_text(encoding="utf-8").splitlines()[-2000:]
    except Exception:
        return zero
    for line in lines:
        try:
            e = json.loads(line)
        except Exception:
            continue
        if not isinstance(e, dict) or (e.get("day") or "") < week_ago:
            continue
        eng = str(e.get("engine") or "?")
        is_today = e.get("day") == today_s
        if eng in _NON_CALL_ENGINES:
            cache_w += 1
            if is_today:
                cache_d += 1
            continue
        raw_cost = e.get("est_cost_usd")
        if raw_cost is None:
            unk_w += 1
            if is_today:
                unk_d += 1
            c = 0.0
        else:
            try:
                c = float(raw_cost or 0.0)
            except Exception:
                c = 0.0
        calls_w += 1
        cost_w += c
        engines[eng] = engines.get(eng, 0) + 1
        try:
            lat_sum += float(e.get("latency_s") or 0.0)
            lat_n += 1
        except Exception:
            pass
        if is_today:
            calls_d += 1
            cost_d += c
    top = max(engines, key=lambda k: engines[k]) if engines else "?"
    lat = f"{lat_sum / lat_n:.1f}" if lat_n else "?"
    return (calls_d, cost_d, unk_d, cache_d,
            calls_w, cost_w, unk_w, cache_w, top, lat)


def sec_agents() -> list[str]:
    """Agents + taches OpenClaw (cache 60 s interne). Jamais d exception."""
    try:
        rows = agents_lines()
        return ["AGENTS", *rows] if rows else ["AGENTS"]
    except Exception:
        return ["AGENTS (indisponible)"]


def sec_projects(kuro: dict | None = None) -> list[str]:
    """Depots git (sensing generique) : affiche si la DB Kuro est vide/absente.

    Jamais d exception. Desactive en tests via KURO_PROJECTS_ROOTS vide.
    """
    try:
        if kuro and kuro.get("db_present") and (kuro.get("projects") or 0) > 0:
            return []
        return git_project_lines()
    except Exception:
        return []


def _rules_dir() -> Path:
    """Racine kuro-rules (fichiers marketing locaux). Jamais d exception.

    Ordre : $KURO_RULES_DIR, cwd (lancement depuis le repo), ~/Documents/kuro-rules
    (meme regle que api.py), puis parents[2] (dev src/). Prend le premier qui
    contient au moins un fichier marketing connu, sinon ~/Documents/kuro-rules.
    Resultat mis en cache (Path.resolve() peut bloquer sur lecteurs reseau).
    """
    env = os.environ.get("KURO_RULES_DIR")
    if env and str(env).strip():
        return Path(str(env).strip()).expanduser()
    return _rules_dir_cached()


@functools.lru_cache(maxsize=1)
def _rules_dir_cached() -> Path:
    try:
        env = os.environ.get("KURO_RULES_DIR")
        if env and str(env).strip():
            # Explicite : respecte strictement (meme si vide -> message avec ce dir).
            return Path(env).expanduser()
        candidates: list[Path] = []
        try:
            candidates.append(Path.cwd())
        except Exception:
            pass
        try:
            candidates.append(Path.home() / "Documents" / "kuro-rules")
        except Exception:
            pass
        try:
            candidates.append(Path(__file__).resolve().parents[2])
        except Exception:
            pass
        markers = ("pipeline.local.json", "LAUNCH_POSTS.md", "acquisition_tracker.md")
        for cand in candidates:
            try:
                if not cand.is_dir():
                    continue
                for m in markers:
                    if (cand / m).exists():
                        return cand
            except Exception:
                continue
        # Aucun marqueur : repli historique (api.py) pour message d erreur parlant.
        try:
            return Path.home() / "Documents" / "kuro-rules"
        except Exception:
            return Path(".")
    except Exception:
        return Path(".")


def _load_json_obj(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _marketing_pipeline(root: Path) -> tuple:
    """(total, interviews_7j, derniere_insight, prochain_pas). Zeros si absent."""
    try:
        from datetime import date, timedelta
        data = _load_json_obj(root / "pipeline.local.json")
        entries = [e for e in (data.get("entries") or []) if isinstance(e, dict)]
        total = len(entries)
        week_ago = (date.today() - timedelta(days=6)).isoformat()
        interviews_7d = 0
        for e in entries:
            try:
                if e.get("type") == "interview" and str(e.get("date", "")) >= week_ago:
                    interviews_7d += 1
            except Exception:
                continue
        last = max(entries, key=lambda e: str(e.get("date", ""))) if entries else {}
        insight = str(last.get("insight") or "").strip().replace("\n", " ")
        nxt = ""
        for e in reversed(entries):
            if isinstance(e, dict) and str(e.get("next_step") or "").strip():
                nxt = str(e.get("next_step")).strip().replace("\n", " ")
                break
        return total, interviews_7d, insight[:110], nxt[:110]
    except Exception:
        return 0, 0, "", ""


def _marketing_launch(root: Path) -> tuple:
    """(drafts, publies) depuis LAUNCH_POSTS.md. Zeros si absent."""
    try:
        text = (root / "LAUNCH_POSTS.md").read_text(encoding="utf-8")
    except Exception:
        return 0, 0
    try:
        drafts = sum(1 for line in text.splitlines()
                     if line.startswith("## ") and "checklist" not in line.lower())
        publies = sum(1 for line in text.splitlines()
                      if line.strip().startswith("- [x]") or line.strip().startswith("- [X]"))
        # Cap : la checklist contient aussi des taches non-posts -> borne aux drafts.
        publies = min(publies, drafts)
        return drafts, publies
    except Exception:  # pragma: no cover - splitlines() sur str ne leve pas
        return 0, 0


def _marketing_tracker(root: Path) -> tuple:
    """(canaux, doc_nom) depuis acquisition_tracker.md (racine ou docs/tracking)."""
    try:
        candidates = [root / "acquisition_tracker.md",
                      root / "docs" / "tracking" / "acquisition_tracker.md"]
        path = next((p for p in candidates if p.exists()), candidates[0])
        text = path.read_text(encoding="utf-8")
    except Exception:
        return 0, "?"
    try:
        rows = [line for line in text.splitlines()
                if line.strip().startswith("|") and "**" in line
                and any(k in line for k in ("Reddit", "Discord", "GitHub", "X ", "HN", "Lobsters", "Blog"))]
        return len(rows), path.name
    except Exception:  # pragma: no cover - comprehension sur str ne leve pas
        return 0, "?"


def _file_age_txt(path: Path) -> str:
    """" (maj il y a 17j)" / " (maj il y a 3h)" / "" si illisible."""
    try:
        from datetime import datetime as _dt
        age_s = max(0.0, (_dt.now().astimezone() - _dt.fromtimestamp(
            path.stat().st_mtime).astimezone()).total_seconds())
        if age_s < 5400:
            return f" (maj il y a {int(age_s // 60)} min)"
        if age_s < 86400:
            return f" (maj il y a {int(age_s // 3600)}h)"
        return f" (maj il y a {int(age_s // 86400)}j)"
    except Exception:
        return ""


def sec_marketing() -> list[str]:
    """Apercu marketing local (pipeline + drafts + tracker). Jamais d exception.

    Sources 100% locales : pipeline.local.json, LAUNCH_POSTS.md,
    acquisition_tracker.md. Zero reseau, zero LLM. Chaque ligne porte l'age
    de sa source : un chiffre vieux de 3 semaines ne doit pas passer pour
    du live.
    """
    try:
        root = _rules_dir()
        total, itw_7d, insight, nxt = _marketing_pipeline(root)
        drafts, publies = _marketing_launch(root)
        canaux, _doc = _marketing_tracker(root)
        if not total and not drafts and not canaux:
            return [f"MARKETING donnees absentes (dir {root} : "
                    "pipeline.local.json / LAUNCH_POSTS.md introuvables)"]
        pipe_age = _file_age_txt(root / "pipeline.local.json")
        launch_age = _file_age_txt(root / "LAUNCH_POSTS.md")
        track_age = _file_age_txt(root / "acquisition_tracker.md")
        if not (root / "acquisition_tracker.md").exists():
            track_age = _file_age_txt(root / "docs" / "tracking" / "acquisition_tracker.md")
        lines = [f"pipeline : {total} entrees - {itw_7d} {_pl(itw_7d, 'interview')} 7j"
                 f" (cible 3/sem){pipe_age}"]
        if insight:
            lines.append(f"  insight : {insight}")
        if nxt:
            lines.append(f"  prochain pas : {nxt}")
        if drafts:
            lines.append(f"  drafts : {drafts} posts prets [{publies}/{drafts} publies]{launch_age}")
        if canaux:
            lines.append(f"  tracker : {canaux} canaux suivis (Reddit/Discord/GitHub){track_age}")
        return lines[:6]
    except Exception:
        return ["MARKETING (indisponible)"]


def _strategy_history() -> list[dict]:
    """Snapshots mensuels (kuro_strategy.py --snapshot). Liste vide si absent."""
    try:
        data = json.loads((_rules_dir() / "strategy_history.local.json").read_text(
            encoding="utf-8"))
        rows = [r for r in (data if isinstance(data, list) else [])
                if isinstance(r, dict) and len(str(r.get("date", ""))) == 10]
        return sorted(rows, key=lambda r: str(r["date"]))
    except Exception:
        return []


def _strat_delta(new: Any, old: Any, suffix: str = "") -> str:
    """'+1.2 mois ▲' / '-0.5 ▲...' / '?' si incalculable."""
    try:
        if new is None or old is None:
            return "?"
        diff = float(new) - float(old)
        if diff > 0:
            return f"+{diff:g}{suffix} ▲"
        if diff < 0:
            return f"{diff:g}{suffix} ▼"
        return f"={suffix}"
    except Exception:
        return "?"


def sec_strategy() -> list[str]:
    """Suivi strategique mensuel (runway, velocite, OKR, decisions).

    Lit UNIQUEMENT strategy_history.local.json : jamais de git, jamais
    de LLM, jamais d exception. Historique jeune -> message honnete
    (pas de courbe avec 1 point).
    """
    try:
        rows = _strategy_history()
        root = _rules_dir()
        if not rows:
            return [f"STRATÉGIE pas d historique (dir {root} : "
                    "lancer `python scripts/kuro_strategy.py --snapshot`)"]
        age = _file_age_txt(root / "strategy_history.local.json")
        last = rows[-1]
        prev = None
        for r in reversed(rows[:-1]):
            if str(r.get("date", ""))[:7] != str(last.get("date", ""))[:7]:
                prev = r
                break
        old = prev or {}
        okr = last.get("okr_avg_pct")
        okr_txt = f"{okr}%" if okr is not None else "?"
        def _val(key: str) -> str:
            value = last.get(key)
            return "?" if value is None else str(value)

        lines = [
            f"runway : {_val('runway_months')} mois "
            f"({_strat_delta(last.get('runway_months'), old.get('runway_months'), ' mois')})"
            f"{age}",
            f"  velocite : {_val('velocity')} c/sem "
            f"({_strat_delta(last.get('velocity'), old.get('velocity'), ' c/sem')})",
            f"  OKR : {okr_txt} moy. "
            f"({_strat_delta(last.get('okr_avg_pct'), old.get('okr_avg_pct'), ' pts')}) "
            f"{last.get('okr_hit', '?')}/{last.get('okr_total', '?')} atteints",
            f"  decisions : {len(last.get('decisions_open') or [])} ouvertes "
            f"· {last.get('interviews_7d', '?')} interviews 7j",
        ]
        return lines[:6]
    except Exception:
        return ["STRATÉGIE (indisponible)"]


# ---------- registre de boxes (point d extension) ----------
# Les boxes "simples" (lignes pures, meme contenu en large et en etroit)
# sont cataloguees ici : le rendu itere le registre au lieu d empiler
# des if. Les tiers ajoutent la leur via register_box() (numeros 8-9,
# 7 pris par SEO — voir extension SEO plus bas).
_BOX_DEFS: list[dict] = [
    {"key": "market", "num": "5", "title": "5 MARKETING", "color": "cyan",
     "rows": sec_marketing},
    {"key": "strat", "num": "6", "title": "6 STRATÉGIE", "color": "cyan",
     "rows": sec_strategy},
]


def _extra_boxes(hidden: set, width: int) -> list[str]:
    """Boxes du registre en cadres (jamais d exception, ordre catalogue)."""
    try:
        body: list[str] = []
        for defn in list(_BOX_DEFS):
            try:
                if str(defn.get("key")) in (hidden or set()):
                    continue
                func = defn.get("rows")
                rows = func() if callable(func) else []
                rows = list(rows) if isinstance(rows, list) else []
            except Exception:
                rows = ["(indisponible)"]
            body += _box(str(defn.get("title") or "?"), rows,
                         max(10, int(width)),
                         defn.get("color") if defn.get("color") in _PAINT_LEVELS else None)
        return body
    except Exception:
        return []


def register_box(key: str, title: str, color: str, rows_func) -> str:
    """Enregistre une box d extension (tiers). Retourne le numero (8-9) ou "".

    rows_func() -> list[str], appelee a chaque frame en mode non-compact.
    Cles reservees (kuro/cpu/net/proc/market/strat/seo) refusees.
    """
    try:
        key = str(key or "").strip()
        if not key or not callable(rows_func):
            return ""
        taken_keys = {str(b.get("key")) for b in _BOX_DEFS}
        taken_keys.update(("kuro", "cpu", "net", "proc"))
        if key in taken_keys:
            return ""
        taken_nums = {str(b.get("num")) for b in _BOX_DEFS}
        num = next((str(n) for n in range(8, 10) if str(n) not in taken_nums), "")
        if not num:
            return ""
        _BOX_DEFS.append({"key": key, "num": num,
                          "title": f"{num} {str(title or key).strip()}",
                          "color": color if color in _PAINT_LEVELS else "cyan",
                          "rows": rows_func})
        return num
    except Exception:
        return ""


def _leads_path(name: str) -> Path:
    """Fichier ~/leads/<name> (existe sur serveur, absent sur PC : honnete)."""
    try:
        return Path.home() / "leads" / name
    except Exception:
        return Path(name)


def sec_seo() -> list[str]:
    """Audit SEO quotidien (~/leads/SEO_AUDIT.md) : date, P0/P1, top actions.

    Lecture seule du fichier genere par le cron strategy-daily. Absent
    (PC sans leads) -> message honnete, pas de chiffres inventes.
    """
    try:
        path = _leads_path("SEO_AUDIT.md")
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return ["SEO pas d audit (cron strategy-daily : ~/leads/SEO_AUDIT.md absent)"]
        date = ""
        for line in text.splitlines()[:12]:
            cleaned = line.strip().lstrip("#* ").strip()
            if cleaned.startswith("Date"):
                date = cleaned[4:].strip("* :")[:40]
                break
        p0 = _seo_items(text, "### P0")
        p1 = _seo_items(text, "### P1")
        age = _rel_age(_seo_file_date(path))
        lines = [(f"audit : {date or '?'}"
                  + (f" ({age})" if age else ""))[:100]]
        lines.append(f"  P0 : {len(p0)} actions  ·  P1 : {len(p1)} actions")
        lines += [f"  -> {item}" for item in p0[:2]]
        return lines[:6]
    except Exception:
        return ["SEO (indisponible)"]


def _seo_file_date(path: Path) -> str:
    """Date ISO du fichier pour _rel_age (via mtime)."""
    try:
        from datetime import datetime as _dt
        return _dt.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(
            timespec="seconds")
    except Exception:
        return ""


def _seo_items(text: str, header: str) -> list[str]:
    """Items numerotes sous un header ### (pur, testable)."""
    try:
        out: list[str] = []
        inside = False
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("### "):
                inside = stripped == header
                continue
            if inside and stripped and stripped[0].isdigit():
                item = stripped.split(None, 1)
                out.append(item[1][:110] if len(item) > 1 else stripped[:110])
        return out
    except Exception:
        return []


# Extension SEO (box 7) : definie APRES sec_seo (ref avant = NameError
# a l import). Ordre catalogue : 5 MARKETING, 6 STRATÉGIE, 7 SEO.
_BOX_DEFS.append({"key": "seo", "num": "7", "title": "7 SEO", "color": "cyan",
                  "rows": sec_seo})


def _rel_age(when: Any) -> str:
    """Age relatif best-effort ("il y a 10h", "il y a 3j", ""). Jamais d exception."""
    try:
        from datetime import datetime as _dt
        txt = str(when or "").strip()
        if not txt:
            return ""
        stamp = _dt.fromisoformat(txt.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            stamp = stamp.astimezone()
        secs = max(0.0, (_dt.now().astimezone() - stamp).total_seconds())
        if secs < 300:
            return "a l'instant"
        if secs < 5400:
            return f"il y a {int(secs // 60)} min"
        if secs < 86400:
            return f"il y a {int(secs // 3600)}h"
        return f"il y a {int(secs // 86400)}j"
    except Exception:
        return ""


def _short_model_name(model: Any) -> str:
    """Nom court d un modele ("a/b:free" -> "b:free"). "" si absent."""
    try:
        return str(model or "").split("@")[0].split("/")[-1] or ""
    except Exception:
        return ""


def _budgets() -> dict:
    """Budgets {daily_usd, weekly_usd} depuis budgets.local.json (gitigne)."""
    try:
        data = json.loads((_rules_dir() / "budgets.local.json").read_text(
            encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _budget_txt(spent: float, cap: Any) -> str:
    """" [$1.20/$2.00 60%]" + " !!" au-dela de 100%, "" si pas de budget."""
    try:
        cap_f = float(cap)
        if cap_f <= 0:
            return ""
        pct = float(spent or 0.0) / cap_f * 100
        flag = " !!" if pct >= 100 else (" !" if pct >= 80 else "")
        return f" [${float(spent or 0.0):.4f}/${cap_f:.2f} {pct:.0f}%{flag}]"
    except Exception:
        return ""


def _unk_txt(n: int) -> str:
    """" +2 couts inconnus" / "" si 0. Jamais d exception."""
    try:
        if int(n) <= 0:
            return ""
        return f" +{int(n)} {_pl(n, 'coût inconnu', 'coûts inconnus')}"
    except Exception:
        return ""


def sec_brain() -> list[str]:
    """Dernier cerveau utilise (jambe LLM qui a repondu + latence + couts estimes)."""
    data = _read_brain()
    if not data:
        lines = ["cerveau : inconnu (aucun appel LLM enregistre)"]
    else:
        age = _rel_age(data.get("at"))
        eng = str(data.get("engine") or "?")
        model = _short_model_name(data.get("model") or "")
        tag = f" [{model}]" if model and model != eng else ""
        lines = [f"cerveau : {eng}{tag}  "
                 f"({data.get('latency_s', '?')}s, {data.get('at', '?')}"
                 f"{', ' + age if age else ''})"]
    (calls_d, cost_d, unk_d, cache_d,
     calls_w, cost_w, unk_w, cache_w, top, lat) = _usage_stats()
    if calls_d or calls_w or cache_d or cache_w:
        budgets = _budgets()
        pcts = _latency_pcts()
        p95 = f" p95:{pcts['p95']}s" if pcts else ""
        lines.append(f"  couts : ~${cost_d:.4f} auj. ({calls_d} {_pl(calls_d, 'appel')}"
                     f"{_unk_txt(unk_d)}){_budget_txt(cost_d, budgets.get('daily_usd'))}  "
                     f"~${cost_w:.4f} /7j ({calls_w} "
                     f"{_pl(calls_w, 'appel')}{_unk_txt(unk_w)})"
                     f"{_budget_txt(cost_w, budgets.get('weekly_usd'))}  "
                     f"top:{top} lat:{lat}s{p95}")
        if cache_d or cache_w:
            lines.append(f"  cache local : {cache_d} {_pl(cache_d, 'hit')} auj., "
                         f"{cache_w} {_pl(cache_w, 'hit')} /7j (0 token, instantané)")
    lines.extend(_legs_line())
    return lines


def _recent_legs(limit: int = 60, max_age_days: int = 7) -> dict[str, str]:
    """Dernier statut connu par jambe (historique local recent). Jamais d exception.

    Fenetre de 7 j : un "DOWN" vieux de 3 semaines sans aucun appel depuis
    n'est plus une info, c'est du bruit qui fait croire a une panne live.
    Entrees sans date lisible -> conservees (compatibilite ascendante).
    """
    out: dict[str, str] = {}
    try:
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=max_age_days)).isoformat()
    except Exception:
        cutoff = ""
    try:
        text = LLM_USAGE_FILE.read_text(encoding="utf-8")
    except Exception:
        return out
    for line in text.splitlines()[-limit:]:
        try:
            entry = json.loads(line)
        except Exception:
            continue
        if not isinstance(entry, dict):
            continue
        try:
            day = str(entry.get("day") or "")
            if cutoff and day and day < cutoff:
                continue
        except Exception:  # pragma: no cover - str() sur JSON ne leve pas
            pass
        for pair in entry.get("legs") or []:
            try:
                out[str(pair[0])] = str(pair[1])
            except Exception:
                continue
    return out


_OLLAMA_TTL_SECONDS = 120.0
_OLLAMA_CACHE: dict = {"ts": 0.0, "ok": False, "names": []}


def _ollama_state() -> tuple[bool, list]:
    """Ollama localhost joignable + modeles tires (cache 120 s).

    Meme semantique que kuro_llm.brain_status() pour la jambe locale, sans
    l'importer (Xenon reste sans dependance a l'import) : que du loopback
    (OLLAMA_URL ou 127.0.0.1:11434), timeout 2 s, jamais d internet,
    jamais de tokens depenses, jamais d exception. Le "local ?" permanent
    (jamais teste) mentait alors que le daemon tourne avec le modele.
    """
    now = time.monotonic()
    try:
        if (now - float(_OLLAMA_CACHE.get("ts", 0.0))) < _OLLAMA_TTL_SECONDS:
            return bool(_OLLAMA_CACHE.get("ok")), list(_OLLAMA_CACHE.get("names") or [])
    except Exception:
        pass
    ok, names = False, []
    try:
        import urllib.request

        base = (os.environ.get("OLLAMA_URL") or "http://127.0.0.1:11434").rstrip("/")
        with urllib.request.urlopen(base + "/api/tags", timeout=2) as resp:  # nosec B310 - loopback seul (OLLAMA_URL ou 127.0.0.1), timeout 2s
            data = json.loads((resp.read() or b"").decode("utf-8") or "{}")
        if isinstance(data, dict):
            names = [str(m.get("name") or "") for m in (data.get("models") or [])
                     if isinstance(m, dict)]
            ok = True
    except Exception:
        ok, names = False, []
    _OLLAMA_CACHE.update({"ts": time.monotonic(), "ok": ok, "names": names})
    return ok, names


def _legs_line() -> list[str]:
    """Etat des jambes SANS depenser de tokens (cles + historique + sonde locale).

    Jambes cloud : presence des cles + derniers resultats connus (pas de
    sonde reseau : un test couterait des tokens). Jambe locale : sonde
    localhost /api/tags en cache 120 s (meme semantique que
    kuro_llm.brain_status, sans l importer). Marques : OK (prouve),
    DOWN (echec recent), off (non configure), ? (jamais teste).
    """
    try:
        recent = _recent_legs()
        states: list[tuple] = []
        for leg, var in (("openrouter", "OPENROUTER_API_KEY"),
                         ("groq", "GROQ_API_KEY"),
                         ("deepseek", "DEEPSEEK_API_KEY")):
            if not os.environ.get(var):
                states.append((leg, "off"))
            elif recent.get(leg) == "ok":
                states.append((leg, "OK"))
            elif recent.get(leg):
                states.append((leg, "DOWN"))
            else:
                states.append((leg, "?"))
        model = os.environ.get("OLLAMA_MODEL")
        if not model or model.endswith(":cloud"):
            states.append(("local", "off"))
        else:
            ok, names = _ollama_state()
            states.append(("local", "OK" if ok and model in names else "DOWN"))
        states.append(("pollinations", "off"
                       if os.environ.get("KURO_POLLINATIONS", "1") == "0" else "?"))
        states.append(("litellm", "on"
                       if os.environ.get("KURO_ROUTER") == "litellm" else "off"))
        return ["jambes : " + " | ".join(f"{leg} {st}" for leg, st in states)]
    except Exception:
        return []


def _div(label: str, width: int) -> str:
    """Sous-separateur facon btop : -- label ------ (largeur exacte)."""
    try:
        w = max(8, int(width))
        name = str(label)[: max(0, w - 4)]
        return ("-- " + name + " " + "-" * max(0, w - 4 - len(name)))[:w]
    except Exception:
        return ""


def _help_rows() -> list[str]:
    """Contenu de l aide (touche h)."""
    rows = [
        "q : quitter              espace : pause",
        "c / m : tri CPU / MEM    / : filtre processus",
        "Haut / Bas (ou j / k) : selection   Entree : fiche detail",
        "1-7 : montre/cache KURO, CPU, RESEAU, PROC, MARKETING, STRATÉGIE, SEO",
        "r : rafraichir           +/- : vitesse",
        "h : cette aide           q / Echap : fermer",
    ]
    try:
        extras = [f"{b.get('num')} {b.get('key')}"
                  for b in list(_BOX_DEFS)
                  if str(b.get("num")) not in ("5", "6", "7")]
        if extras:
            rows.append("8-9 : extensions (" + ", ".join(extras) + ")")
    except Exception:
        pass
    return rows


def _box(title: str, rows: list[str], width: int, color: str | None = None) -> list[str]:
    """Cadre ASCII facon btop : +- TITRE --+ / | ... | / +--+. Largeur exacte."""
    try:
        w = max(10, int(width))
        name = str(title)[: max(0, w - 6)]
        if color in _PAINT_LEVELS and _colors_on():
            name = f"{ANSI[color]}{name}{ANSI['reset']}"
        top = "+- " + name + " " + "-" * max(0, w - 4 - _visible_width(name))
        out = [_fit(top, w)]
        for row in rows or []:
            for piece in _wrap(row, w - 4):
                cell = _vpad(piece, w - 4)
                out.append("| " + cell + " |")
        out.append("+" + "-" * (w - 2) + "+")
        return out
    except Exception:
        return list(rows or [])


def _side_by_side(left: list[str], right: list[str], total: int, rw: int) -> list[str]:
    """Deux colonnes ASCII : gauche fluide + sidebar droite (jamais d exception)."""
    try:
        lw = max(20, total - rw - 3)
        n = max(len(left), len(right))
        out = []
        for i in range(n):
            left_cell = left[i] if i < len(left) else ""
            right_cell = right[i] if i < len(right) else ""
            out.append(_vpad(_fit(left_cell, lw), lw) + " | " + _vpad(_fit(right_cell, rw), rw))
        return out
    except Exception:
        return [*left, *right]


def _titled(label: str, rows: list[str], width: int) -> list[str]:
    """Sous-section avec diviseur (vide -> rien). Jamais d exception."""
    try:
        if not rows:
            return []
        return [_div(label, width), *rows]
    except Exception:
        try:
            return list(rows or [])
        except Exception:
            return []


def _compact_strat_seo(hidden: set) -> list[str]:
    """Digest 1 ligne strat+SEO pour le mode compact (budget <=26 rangs).

    Vide si les deux boxes sont cachées. Jamais d exception.
    """
    try:
        parts: list[str] = []
        if "strat" not in (hidden or set()):
            try:
                first = (sec_strategy() or ["?"])[0]
            except Exception:
                first = "?"
            parts.append(str(first).strip()[:60])
        if "seo" not in (hidden or set()):
            try:
                rows = sec_seo() or ["?"]
                pick = next((r for r in rows if "P0" in r and "P1" in r), rows[0])
            except Exception:
                pick = "?"
            parts.append(str(pick).strip()[:45])
        if not parts:
            return []
        return [" · ".join(parts)[:90]]
    except Exception:
        return []


def _shrink_compact(parts: list[str], height: int) -> list[str]:
    """Rogne le compact à `height` rangs (petits écrans).

    Priorité : box PROC d'abord (garde 1 ligne), digest STRAT/SEO ensuite.
    Header + footer jamais touchés. Pur, testable.
    """
    try:
        parts = list(parts)
        if len(parts) <= height or height < 12:
            return parts
        for marker, keep in (("+- 4 ", 1), ("+- 6 STRAT/SEO", 0)):
            if len(parts) <= height:
                break
            start = next((i for i, line in enumerate(parts)
                          if line.startswith(marker)), -1)
            if start < 0:
                continue
            end = next((i for i in range(start + 1, len(parts))
                        if parts[i].startswith("+")
                        and set(parts[i]) <= {"+", "-"}), -1)
            if end < 0:
                continue
            if keep == 0:
                del parts[start:end + 1]
            else:
                overflow = len(parts) - height
                removable = max(0, (end - start - 1) - keep)
                del parts[start + 1:start + 1 + min(removable, overflow)]
        return parts
    except Exception:
        return parts


def render_frame(payload: dict, prev: dict | None = None, dt: float = 0.0,
                 kuro: dict | None = None, now: float | None = None,
                 hist: dict | None = None, sort: str = "cpu", filt: str = "",
                 sel: int = -1, detail: dict | None = None,
                 hidden: tuple = (), help: bool = False,
                 compact: bool | None = None) -> str:
    """Une frame complete (jamais d exception : que des .get).

    Terminal large (>=150 cols) : sidebar droite (visage + cerveau + Kuro),
    le reste a gauche. Sinon : empilement classique.
    hidden : sous-ensemble de {"kuro", "cpu", "net", "proc", "market", "strat", "seo"} (touches 1-7).
    help : affiche l aide au lieu du tableau de bord (touche h).
    compact : TOP 5, sans graphes ni capteurs (auto si <32 rangs tty).
    """
    width = term_width()
    if compact is None:
        try:
            compact = _stdout_is_tty() and term_height() < 32
        except Exception:
            compact = False
    nprocs = 5 if compact else 10
    footer = ("[q] quitter [espace] pause [c/m] tri [/] filtre [HB] choix "
              "[Entree] detail [1-7] boxes [h] aide [r] refresh [+/-] vitesse")
    if compact:
        footer = "[q] quitter [/] filtre [HB] choix [Entree] detail [h] aide"
    if filt:
        footer += f"  filtre:{filt[:20]}"
    if help:
        total = min(width, 100) if width < WIDE_MIN_WIDTH else min(width, 170)
        body = [*_box("AIDE - touches (h pour fermer)", _help_rows(), total, "cyan")]
        parts = [_fit(p, total) for p in body] + [_fit(footer, total)]
        return "\n".join(parts) + "\n"
    if compact:
        # Slim <=26 rangs : l essentiel + 1 ligne strat/SEO (sinon l audit
        # strategique est invisible sur petit terminal — vu en prod).
        # Budget : UNE box d 1 ligne (3 rangs), pas deux boxes.
        total = min(width, 100)
        mood = sec_face(payload, kuro, now)[-1:]
        ksum = sec_kuro(kuro)[:1]
        cpu_all = sec_cpu_mem(payload, None, prev=prev, dt=dt)
        net_all = sec_disk_net(payload, prev, dt, None, max_parts=2)
        procs = sec_procs(payload, total - 4, sort=sort, filt=filt, sel=sel,
                           limit=5)
        hide_c = set(hidden or ())
        body = [
            *sec_header(payload),
            *_box("1 KURO", [*mood, *ksum], total, "dim"),
            *_box("2 CPU / MEMOIRE", cpu_all, total, "ok"),
            *_box("3 DISQUES / RESEAU", net_all, total, "blue"),
            *_box("4 " + (procs[0] if procs else "TOP PROCESSUS"), procs[1:], total, "magenta"),
        ]
        digest = _compact_strat_seo(hide_c)
        if digest:
            body += _box("6 STRAT/SEO", digest, total, "cyan")
        if detail:
            body += _box(f"DETAIL {detail.get('pid', '?')}",
                         sec_proc_detail(detail), total, "cyan")
        parts = [_fit(p, total) for p in body] + [_fit(footer, total)]
        if _stdout_is_tty():
            try:
                height = term_height()
            except Exception:
                height = 0
            if height and len(parts) > height:
                parts = _shrink_compact(parts, height)
            try:
                room = term_height() - len(parts)
            except Exception:
                room = 0
            if room > 0:
                parts = parts[:-1] + [""] * room + parts[-1:]
        return "\n".join(parts) + "\n"
    hide = set(hidden or ())
    if width >= WIDE_MIN_WIDTH:
        total = min(width, 170)
        lw = total - SIDEBAR_WIDTH - 3
        dn_extra = sec_disk_net(payload, prev, dt, hist,
                                width=lw - 4) + ([] if compact else sec_extra(payload))
        procs = sec_procs(payload, lw - 4, sort=sort, filt=filt, sel=sel,
                           limit=nprocs)
        left = []
        if "cpu" not in hide:
            left += _box("2 CPU / MEMOIRE", sec_cpu_mem(payload, hist,
                                                      width=lw - 4,
                                                      prev=prev, dt=dt), lw, "ok")
        if "net" not in hide:
            left += _box("3 DISQUES / RESEAU", dn_extra, lw, "blue")
        if "proc" not in hide:
            left += _box("4 " + (procs[0] if procs else "TOP PROCESSUS"),
                         procs[1:], lw, "magenta")
        if not compact:
            left += _extra_boxes(hide, lw)
        if detail:
            left += _box(f"DETAIL {detail.get('pid', '?')}",
                         sec_proc_detail(detail), lw, "cyan")
        right = []
        if "kuro" not in hide:
            face = sec_face(payload, kuro, now)
            inner = SIDEBAR_WIDTH - 4
            kuro_rows = [
                *face,
                *_titled("daemon", sec_kuro(kuro), inner),
                *_titled("cerveau", sec_brain(), inner),
                *_titled("agents", sec_agents(), inner),
                *_titled("projets", sec_projects(kuro), inner),
            ]
            right = _box("1 KURO", kuro_rows, SIDEBAR_WIDTH, "dim")
        header = [f"GLANCES KURO  {(payload.get('host') or {}).get('hostname', '?')}"]
        body = [*header, *_side_by_side(left, right, total, SIDEBAR_WIDTH)]
    else:
        total = min(width, 100)
        procs = sec_procs(payload, total - 4, sort=sort, filt=filt, sel=sel,
                           limit=nprocs)
        detail_box = (_box(f"DETAIL {detail.get('pid', '?')}",
                           sec_proc_detail(detail), total, "cyan")
                      if detail else [])
        inner = total - 4
        kuro_rows = [
            *sec_face(payload, kuro, now),
            *_titled("daemon", sec_kuro(kuro), inner),
            *_titled("cerveau", sec_brain(), inner),
            *_titled("agents", sec_agents(), inner),
            *_titled("projets", sec_projects(kuro), inner),
        ]
        body = [*sec_header(payload)]
        if "kuro" not in hide:
            body += _box("1 KURO", kuro_rows, total, "dim")
        if "cpu" not in hide:
            body += _box("2 CPU / MEMOIRE",
                         sec_cpu_mem(payload, hist, width=inner,
                                     prev=prev, dt=dt), total, "ok")
        if "net" not in hide:
            body += _box("3 DISQUES / RESEAU",
                         sec_disk_net(payload, prev, dt, hist,
                                      width=inner) + ([] if compact
                                                      else sec_extra(payload)),
                         total, "blue")
        if "proc" not in hide:
            body += _box("4 " + (procs[0] if procs else "TOP PROCESSUS"),
                         procs[1:], total, "magenta")
        if not compact:
            body += _extra_boxes(hide, total)
        body += detail_box
    parts = [_fit(p, total) for p in body] + [_fit(f"{footer} {spinner(now)}", total)]
    if _stdout_is_tty():
        # Remplit tout l ecran, footer colle en bas (captures/tests : pas de pad).
        try:
            room = term_height() - len(parts)
        except Exception:
            room = 0
        if room > 0:
            parts = parts[:-1] + [""] * room + parts[-1:]
    return "\n".join(parts) + "\n"


class _RawKeys:
    """Touches instantanees (sans Entree). Windows: msvcrt. Unix: termios."""

    def __init__(self) -> None:
        self._unix_fd: int | None = None
        self._unix_old: Any = None

    def __enter__(self) -> _RawKeys:
        if os.name != "nt":  # pragma: no cover - branches Unix (CI Windows)
            try:
                import termios
                import tty

                self._unix_fd = sys.stdin.fileno()
                self._unix_old = termios.tcgetattr(self._unix_fd)
                tty.setcbreak(self._unix_fd)
            except Exception:
                self._unix_fd = None
        return self

    def __exit__(self, *args: Any) -> None:
        if self._unix_fd is not None:  # pragma: no cover - branches Unix
            try:
                import termios

                termios.tcsetattr(self._unix_fd, termios.TCSADRAIN, self._unix_old)
            except Exception:
                pass

    def read(self) -> str | None:
        try:
            if os.name == "nt":
                import msvcrt

                if msvcrt.kbhit():
                    first = msvcrt.getch()
                    if first in (b"\xe0", b"\x00"):
                        # Fleches Windows : normalise comme les sequences ANSI.
                        second = msvcrt.getch()
                        try:  # pragma: no cover - decode(replace) ne leve pas
                            letter = second.decode("utf-8", "replace")
                        except Exception:  # pragma: no cover
                            return None
                        return {"H": "\x1b[A", "P": "\x1b[B"}.get(letter)
                    return first.decode("utf-8", "replace")
                return None
            import select  # pragma: no cover - branches Unix (CI Windows)

            if select.select([sys.stdin], [], [], 0)[0]:  # pragma: no cover
                return sys.stdin.read(1)  # pragma: no cover
            return None  # pragma: no cover
        except Exception:
            return None


def _visible_procs(payload: dict, sort: str = "cpu", filt: str = "",
                   limit: int = 10) -> list[dict]:
    """Liste affichee par sec_procs (tri + filtre), pour la selection clavier."""
    try:
        procs = list((payload or {}).get("processes") or [])
        key = "mem" if sort == "mem" else "cpu"
        try:
            procs.sort(key=lambda r: (r.get(key) or 0), reverse=True)
        except Exception:
            pass
        if filt:
            needle = filt.lower()
            procs = [p for p in procs
                     if needle in str(p.get("name") or "").lower()]
        return procs[: max(1, limit)]
    except Exception:
        return []


def _read_key(keys: _RawKeys) -> str | None:
    """Touche logique : fleches -> up/down, sinon caractere brut."""
    try:
        ch = keys.read()
    except Exception:
        return None
    if ch is None:
        return None
    if ch == "\x1b":
        # Sequence ANSI : lit "[" puis la lettre (poll court, touches arrivees
        # ensemble en cbreak).
        seq = ""
        for _ in range(20):
            time.sleep(0.005)
            nxt = keys.read()
            if nxt is None:
                continue
            seq += nxt
            if len(seq) >= 2:
                break
        if seq == "[A":
            return "up"
        if seq == "[B":
            return "down"
        return None
    if ch == "\x1b[A":
        return "up"
    if ch == "\x1b[B":
        return "down"
    return ch


def _read_line(keys: _RawKeys, prompt: str = "filtre: ") -> str | None:
    """Saisie d une ligne en mode cbreak (ENTREE valide, ECHAP annule)."""
    buf: list[str] = []
    try:
        sys.stdout.write("\n" + prompt)
        sys.stdout.flush()
        while True:
            time.sleep(0.05)
            ch = keys.read()
            if ch is None:
                continue
            if ch in ("\r", "\n"):
                sys.stdout.write("\n")
                return "".join(buf)
            if ch == "\x1b":
                sys.stdout.write("\n")
                return None
            if ch in ("\x7f", "\x08"):
                if buf:
                    buf.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                continue
            if ch.isprintable():
                buf.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
    except Exception:
        return None


def _collect_once(top: int) -> tuple:
    """Un cycle de collecte systeme + Kuro (jamais d exception)."""
    try:
        snap = collect_system_snapshot(top_n=top)
    except Exception:
        snap = {}
    try:
        ksnap = collect_kuro_snapshot()
    except Exception:
        ksnap = None
    return snap, ksnap


def watch(interval: float = DEFAULT_INTERVAL, top: int = 10,
          compact: bool | None = None) -> int:
    """Boucle live : collecte synchrone, rendu, clavier (monothread).

    Sections lentes protegees par caches TTL (agents 60 s, git 60 s,
    disque 120 s) : un refresh ne bloque que sur du jamais-vu.
    Touches: q,c,m,/,HB,Entree,1-7,h,espace,+,-,r (+8-9 extensions).
    """
    prev: dict | None = None
    prev_t: float | None = None
    hist: dict[str, list] = {"cpu": [], "mem": [], "up": [], "down": []}
    paused = False
    sort = "cpu"
    filt = ""
    sel = -1
    detail: dict | None = None
    last_procs: list[dict] = []
    hidden: set[str] = set()
    show_help = False
    compact_mode = bool(compact)
    key2box = {"1": "kuro", "2": "cpu", "3": "net", "4": "proc"}
    try:
        for defn in list(_BOX_DEFS):
            key2box[str(defn.get("num"))] = str(defn.get("key"))
    except Exception:
        pass
    with _RawKeys() as keys:
        while True:
            if compact is None:
                try:
                    compact_mode = (_stdout_is_tty()
                                    and term_height() < 32)
                except Exception:
                    compact_mode = False
            if not paused:
                snap, ksnap = _collect_once(top)
                try:
                    hist["cpu"].append((snap.get("cpu") or {}).get("percent"))
                    hist["mem"].append((snap.get("memory") or {}).get("percent"))
                    hist["cpu"] = hist["cpu"][-HIST_LEN:]
                    hist["mem"] = hist["mem"][-HIST_LEN:]
                except Exception:  # pragma: no cover - snap.get() ne leve pas
                    pass
                now = time.monotonic()
                dt = (now - prev_t) if prev_t else interval
                try:
                    sent, recv = _net_rates(snap, prev, dt)
                    hist["up"].append(sent)
                    hist["down"].append(recv)
                    hist["up"] = hist["up"][-HIST_LEN:]
                    hist["down"] = hist["down"][-HIST_LEN:]
                except Exception:  # pragma: no cover - ne leve pas en pratique
                    pass
                sys.stdout.write("\x1b[H\x1b[J" + render_frame(
                    snap, prev, dt, ksnap, now, hist, sort, filt, sel,
                    detail, tuple(sorted(hidden)), show_help,
                    compact_mode))
                sys.stdout.flush()
                prev, prev_t = snap, now
                last_procs = _visible_procs(snap, sort, filt,
                                            5 if compact_mode else 10)
                if detail is not None:
                    # Fiche live : suit le processus selectionne.
                    try:
                        from .system import proc_detail
                        detail = proc_detail(detail.get("pid"))
                    except Exception:
                        detail = None
            waited = 0.0
            while waited < interval:
                time.sleep(0.1)
                waited += 0.1
                raw = _read_key(keys)
                key = raw if raw in ("up", "down") else (raw or "").lower()
                if key == "q":
                    sys.stdout.write("\n")
                    return 0
                if key == " ":
                    paused = not paused
                elif key in ("+", "="):
                    interval = min(10.0, interval + 0.5)
                elif key == "-":
                    interval = max(0.5, interval - 0.5)
                elif key == "c":
                    sort = "cpu"
                elif key == "m":
                    sort = "mem"
                elif key in key2box:
                    box = key2box[key]
                    if box in hidden:
                        hidden.remove(box)
                    else:
                        hidden.add(box)
                elif key == "h":
                    show_help = not show_help
                elif key == "/":
                    got = _read_line(keys)
                    if got is not None:
                        filt = got.strip()[:20]
                        sel = -1
                        detail = None
                elif key in ("up", "down", "k", "j"):
                    if key == "k":
                        key = "up"
                    elif key == "j":
                        key = "down"
                    if last_procs:
                        step = -1 if key == "up" else 1
                        if sel < 0:
                            sel = 0 if key == "down" else len(last_procs) - 1
                        else:
                            sel = (sel + step) % len(last_procs)
                        if detail is not None:
                            try:
                                from .system import proc_detail
                                detail = proc_detail(last_procs[sel].get("pid"))
                            except Exception:
                                detail = None
                elif key in ("\r", "\n"):
                    if detail is not None:
                        detail = None
                    elif 0 <= sel < len(last_procs):
                        try:
                            from .system import proc_detail
                            detail = proc_detail(last_procs[sel].get("pid"))
                        except Exception:
                            detail = None
                elif key == "r":
                    waited = interval
    return 0  # pragma: no cover - boucle infinie, sortie par "q"


def doctor() -> list[tuple[str, bool, str]]:
    """Auto-diagnostic Xenon (<3 s, loopback max, jamais de cles affichees).

    Rend [(nom, ok, detail)] : cles presentes (noms seuls), daemon,
    Ollama local, OpenClaw CLI, fichiers d usage, table de prix.
    """
    out: list[tuple[str, bool, str]] = []

    def _add(name: str, ok: bool, detail: str = "") -> None:
        try:
            out.append((str(name), bool(ok), str(detail or "")))
        except Exception:
            pass

    try:
        keys = [v for v in ("OPENROUTER_API_KEY", "GROQ_API_KEY",
                            "DEEPSEEK_API_KEY") if os.environ.get(v)]
        _add("cles-cloud", True, f"{len(keys)} configuree(s)" if keys
             else "aucune (mode local/pollinations)")
    except Exception:
        _add("cles-cloud", False, "illisibles")
    try:
        snap = collect_kuro_snapshot()
        if not snap.get("db_present"):
            _add("daemon", False, "base absente (~/.kuro/kuro.db)")
        else:
            age = snap.get("heartbeat_age_min")
            old = age is not None and age >= 15
            _add("daemon", not old,
                 "aucun battement" if age is None else f"battement il y a {age:.0f} min")
    except Exception:
        _add("daemon", False, "erreur lecture")
    try:
        model = os.environ.get("OLLAMA_MODEL")
        if not model or model.endswith(":cloud"):
            _add("ollama-local", True, "non configure (off)")
        else:
            ok, names = _ollama_state()
            _add("ollama-local", bool(ok and model in names),
                 model if ok and model in names else "daemon injoignable ou modele absent")
    except Exception:
        _add("ollama-local", False, "erreur sonde")
    try:
        import shutil as _sh
        found = _sh.which("openclaw")
        _add("openclaw-cli", bool(found), found or "absent (section AGENTS vide)")
    except Exception:
        _add("openclaw-cli", False, "erreur")
    try:
        have_last = LLM_LAST_FILE.exists()
        have_usage = LLM_USAGE_FILE.exists()
        _add("journal-llm", bool(have_last or have_usage),
             "llm_last.json + usage.jsonl" if have_last and have_usage
             else "aucun appel enregistre")
    except Exception:
        _add("journal-llm", False, "illisible")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Glances Kuro en terminal (live)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--no-color", action="store_true",
                        help="pas de couleurs ANSI (pipes, vieilles consoles)")
    parser.add_argument("--compact", action="store_true",
                        help="mode compact (petits ecrans) ; auto si <32 rangs")
    parser.add_argument("--doctor", action="store_true",
                        help="auto-diagnostic (cles, daemon, ollama, cli, journal)")
    args = parser.parse_args(argv)
    global _COLOR
    _COLOR = not args.no_color
    if args.doctor:
        bad = 0
        for name, ok, detail in doctor():
            mark = "OK " if ok else "KO "
            if not ok:
                bad += 1
            sys.stdout.write(f"[{mark}] {name}" + (f" : {detail}" if detail else "") + "\n")
        return 1 if bad else 0
    if not _stdout_is_tty():
        sys.stdout.write(render_frame(collect_system_snapshot(top_n=args.top),
                                       kuro=collect_kuro_snapshot()))
        return 0
    try:
        return watch(interval=args.interval, top=args.top,
                     compact=True if args.compact else None)
    except KeyboardInterrupt:
        sys.stdout.write("\n")
        return 130


if __name__ == "__main__":  # pragma: no cover - point d'entree script
    sys.exit(main())  # pragma: no cover
