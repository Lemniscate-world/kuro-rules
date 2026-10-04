#!/usr/bin/env python3
"""kuro_system.py — snapshot systeme live pour le Glances Kuro.

But : donner au dashboard une photo fraiche de la machine (CPU, memoire,
disques, reseau, capteurs, GPU, Docker, top process), comme l outil Glances
mais au format de Kuro.

Dependance optionnelle : psutil (pip install psutil). Sans psutil le module
reste utilisable et renvoie des champs vides avec psutil_available=False.
Aucun secret, aucun reseau sortant, que du local.

Usage:
    python -m kuro_dashboard.system [--json] [--top 10]
    kuro-system [--json] [--top 10]
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_TOP_N = 10
SUBPROCESS_TIMEOUT = 4
# Pseudo-filesystemes bruyants : toujours "pleins" par conception (snaps),
# jamais un vrai signal. Glances les masque aussi.
SKIP_FSTYPES = {"squashfs"}
SKIP_MOUNT_PREFIXES = ("/snap",)
_SNAP_CACHE: dict[str, Any] = {"ts": 0.0, "payload": None}


def _psutil():  # type: ignore[no-untyped-def]
    """Retourne le module psutil ou None (jamais d exception)."""
    try:
        import psutil  # type: ignore

        return psutil
    except ImportError:
        return None


def _host() -> dict[str, Any]:
    psutil_mod = _psutil()
    cpu_count = os.cpu_count() or 0
    if psutil_mod is not None:
        try:
            cpu_count = psutil_mod.cpu_count(logical=True) or cpu_count
        except Exception:
            pass
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "cpu_count": cpu_count,
    }


def _cpu(psutil_mod: Any) -> dict[str, Any]:
    if psutil_mod is None:
        return {"percent": None, "per_cpu": [], "load_avg": list(os.getloadavg()) if hasattr(os, "getloadavg") else None}
    try:
        percent = float(psutil_mod.cpu_percent(interval=None))
    except Exception:
        percent = None
    try:
        per_cpu = [float(v) for v in psutil_mod.cpu_percent(interval=None, percpu=True)]
    except Exception:
        per_cpu = []
    load = list(os.getloadavg()) if hasattr(os, "getloadavg") else None
    return {"percent": percent, "per_cpu": per_cpu, "load_avg": load}


def _memory(psutil_mod: Any) -> dict[str, Any]:
    if psutil_mod is None:
        return {"total": None, "percent": None, "swap_percent": None}
    try:
        vm = psutil_mod.virtual_memory()._asdict()
        sw = psutil_mod.swap_memory()._asdict()
    except Exception:
        return {"total": None, "percent": None, "swap_percent": None}
    return {
        "total": vm.get("total"),
        "available": vm.get("available"),
        "used": vm.get("used"),
        "percent": vm.get("percent"),
        "swap_total": sw.get("total"),
        "swap_used": sw.get("used"),
        "swap_percent": sw.get("percent"),
    }


def _disk(psutil_mod: Any) -> dict[str, Any]:
    partitions: list[dict[str, Any]] = []
    if psutil_mod is not None:
        try:
            for part in psutil_mod.disk_partitions(all=False):
                if part.fstype in SKIP_FSTYPES:
                    continue
                if part.mountpoint.startswith(SKIP_MOUNT_PREFIXES):
                    continue
                try:
                    usage = psutil_mod.disk_usage(part.mountpoint)._asdict()
                except Exception:
                    continue
                partitions.append(
                    {
                        "mount": part.mountpoint,
                        "fstype": part.fstype,
                        "total": usage.get("total"),
                        "used": usage.get("used"),
                        "percent": usage.get("percent"),
                    }
                )
        except Exception:
            partitions = []
    if not partitions:
        total, used, _free = shutil.disk_usage(Path.home().anchor)
        partitions = [{"mount": "fallback", "fstype": "", "total": total, "used": used,
                       "percent": round(used / total * 100, 1) if total else None}]
    io: dict[str, Any] = {}
    if psutil_mod is not None:
        try:
            io = psutil_mod.disk_io_counters()._asdict()
        except Exception:
            io = {}
    return {"partitions": partitions, "io": io}


def _network(psutil_mod: Any) -> dict[str, Any]:
    if psutil_mod is None:
        return {"io": {}, "interfaces": {}}
    try:
        io = psutil_mod.net_io_counters()._asdict()
    except Exception:
        io = {}
    interfaces: dict[str, Any] = {}
    try:
        for name, addrs in psutil_mod.net_if_addrs().items():
            interfaces[name] = [
                {"family": str(a.family), "address": a.address} for a in addrs
            ]
    except Exception:
        interfaces = {}
    return {"io": io, "interfaces": interfaces}


def _sensors(psutil_mod: Any) -> dict[str, Any]:
    if psutil_mod is None:
        return {"temperatures": [], "fans": {}}
    temperatures: list[dict[str, Any]] = []
    try:
        raw = psutil_mod.sensors_temperatures() or {}
        for chip, entries in raw.items():
            for entry in entries:
                temperatures.append(
                    {"chip": chip, "label": entry.label or chip,
                     "current": entry.current, "high": entry.high}
                )
    except Exception:
        temperatures = []
    fans: dict[str, Any] = {}
    try:
        raw_fans = psutil_mod.sensors_fans() or {}
        fans = {k: [{"label": e.label, "current": e.current} for e in v]
                for k, v in raw_fans.items()}
    except Exception:
        fans = {}
    return {"temperatures": temperatures[:20], "fans": fans}


def _gpu() -> list[dict[str, Any]]:
    cmd = ["nvidia-smi", "--query-gpu=index,name,utilization.gpu,"
           "memory.used,memory.total,temperature.gpu",
           "--format=csv,noheader,nounits"]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=SUBPROCESS_TIMEOUT, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return []
    if completed.returncode != 0 or not completed.stdout.strip():
        return []
    cards: list[dict[str, Any]] = []
    for line in completed.stdout.strip().splitlines()[:8]:
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 6:
            continue
        cards.append({"index": parts[0], "name": parts[1],
                      "util_percent": _to_float(parts[2]),
                      "mem_used_mb": _to_float(parts[3]),
                      "mem_total_mb": _to_float(parts[4]),
                      "temp_c": _to_float(parts[5])})
    return cards


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _docker() -> dict[str, Any]:
    cmd = ["docker", "ps", "--format", "{{.ID}} {{.Names}} {{.Status}}"]
    try:
        completed = subprocess.run(cmd, capture_output=True, text=True,
                                   timeout=SUBPROCESS_TIMEOUT, check=False)
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return {"available": False, "count": 0, "containers": []}
    if completed.returncode != 0:
        return {"available": False, "count": 0, "containers": []}
    containers: list[dict[str, Any]] = []
    for line in completed.stdout.strip().splitlines()[:20]:
        if line.strip():
            containers.append({"line": line.strip()[:160]})
    return {"available": True, "count": len(containers), "containers": containers}


def proc_detail(pid: int) -> dict[str, Any] | None:
    """Detail d un processus via psutil (None si parti/injoignable)."""
    psutil_mod = _psutil()
    if psutil_mod is None:
        return None
    try:
        proc = psutil_mod.Process(int(pid))
        with proc.oneshot():
            name = proc.name()
            try:
                cmd = " ".join(proc.cmdline() or [])[:160]
            except Exception:
                cmd = ""
            try:
                user = proc.username()
            except Exception:
                user = "?"
            try:
                threads = proc.num_threads()
            except Exception:
                threads = None
            try:
                rss = proc.memory_info().rss
            except Exception:
                rss = None
            try:
                status = str(proc.status())
            except Exception:
                status = "?"
            try:
                created = proc.create_time()
            except Exception:
                created = None
            try:
                times = proc.cpu_times()
                cpu_user, cpu_sys = float(times.user), float(times.system)
            except Exception:
                cpu_user, cpu_sys = None, None
        return {"pid": int(pid), "name": str(name or "?")[:64], "cmd": cmd,
                "user": str(user)[-24:], "threads": threads, "rss": rss,
                "status": status, "created": created,
                "cpu_user": cpu_user, "cpu_sys": cpu_sys}
    except Exception:
        return None


def _top_processes(psutil_mod: Any, top_n: int) -> list[dict[str, Any]]:
    if psutil_mod is None:
        return []
    try:
        procs = list(psutil_mod.process_iter(
            ["pid", "name", "cpu_percent", "memory_percent", "status"]))
    except Exception:
        return []
    rows: list[dict[str, Any]] = []
    for proc in procs:
        try:
            info = proc.info
            rows.append({"pid": info.get("pid"), "name": str(info.get("name") or "?")[:64],
                         "cpu": info.get("cpu_percent"), "mem": info.get("memory_percent"),
                         "status": str(info.get("status") or "")})
        except Exception:
            continue
    rows.sort(key=lambda r: (r["cpu"] or 0), reverse=True)
    return rows[:max(1, top_n)]


def collect_system_snapshot(top_n: int = DEFAULT_TOP_N) -> dict[str, Any]:
    """Photo complete de la machine (jamais d exception levee)."""
    psutil_mod = _psutil()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "psutil_available": psutil_mod is not None,
        "host": _host(),
        "cpu": _cpu(psutil_mod),
        "memory": _memory(psutil_mod),
        "disk": _disk(psutil_mod),
        "network": _network(psutil_mod),
        "sensors": _sensors(psutil_mod),
        "gpu": _gpu(),
        "docker": _docker(),
        "processes": _top_processes(psutil_mod, top_n),
    }


def get_cached_snapshot(top_n: int = DEFAULT_TOP_N, ttl: float = 2.5) -> dict[str, Any]:
    """Snapshot avec cache court pour le refresh 3s du dashboard (S2 avance)."""
    import time as _time

    now = _time.monotonic()
    cached = _SNAP_CACHE.get("payload")
    if cached is not None and (now - float(_SNAP_CACHE.get("ts", 0.0))) < ttl:
        return cached
    payload = collect_system_snapshot(top_n=top_n)
    _SNAP_CACHE["ts"] = _time.monotonic()
    _SNAP_CACHE["payload"] = payload
    return payload


def render(payload: dict[str, Any]) -> str:
    cpu = payload.get("cpu", {}).get("percent")
    mem = payload.get("memory", {}).get("percent")
    lines = [
        f"Glances Kuro - {payload.get('generated_at')}",
        f"  CPU: {cpu}%  MEM: {mem}%  "
        f"(psutil: {payload.get('psutil_available')})",
        "  Top process:",
    ]
    for proc in payload.get("processes", [])[:10]:
        lines.append(f"    {proc.get('pid')} {proc.get('name')} cpu={proc.get('cpu')} mem={proc.get('mem')}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Snapshot systeme Kuro")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--top", type=int, default=DEFAULT_TOP_N)
    parser.add_argument("--projects", action="store_true",
                        help="depots git sous KURO_PROJECTS_ROOTS (sensing generique)")
    args = parser.parse_args()
    if args.projects:
        from .projects import discover
        repos = discover()
        if args.json:
            print(json.dumps({"projects": repos}, indent=2, ensure_ascii=False, default=str))
        else:
            print(f"Git projects: {len(repos)}")
            for repo in repos:
                flag = f" +{repo['dirty']}" if repo["dirty"] else ""
                print(f"  {repo['name']:<28} [{repo['branch'] or '-'}]{flag}  {repo['last'][:60]}")
        return 0
    payload = collect_system_snapshot(top_n=args.top)
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str)
          if args.json else render(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
