#!/usr/bin/env python3
"""face.py — visage de Kuro pour le terminal (100% ASCII, consoles Windows OK).

Le visage reflete l etat REEL (systeme + daemon), pas l inverse :
  CONTENT  tout va bien            (^_^)
  PAISIBLE calme plat, rien ne force  (-_-)  (+ z)
  INQUIET  seuil depasse ou daemon STALE  (o_O)
  ALERTE   daemon MORT ou machine en surchauffe  (x_x)

Chaque humeur a une frame yeux ouverts / fermes (clignement bref).
Aucun Unicode : que de l ASCII 7-bit (regle R93, consoles CP1252).
"""

from __future__ import annotations

from typing import Any

LABELS = {
    "happy": "CONTENT",
    "idle": "PAISIBLE",
    "worried": "INQUIET",
    "critical": "ALERTE",
}

# chaque humeur : (yeux ouverts, yeux fermes), 2 lignes, ASCII strict.
FACES: dict[str, tuple[list[str], list[str]]] = {
    "happy": ([" .-.", "(^_^)"], [" .-.", "(-_-)"]),
    "idle": ([" .-.", "(-_-) z"], [" .-.", "(-_-) z"]),
    "worried": ([" .-.", "(o_O)"], [" .-.", "(o_-)"]),
    "critical": ([" .-.", "(x_x)"], [" .-.", "(X_X)"]),
}

SPINNER = "|/-\\"


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def mood_for(system: dict | None, kuro: dict | None) -> tuple[str, str]:
    """(humeur, raison en clair). Ordre = gravite decroissante."""
    system = system or {}
    kuro = kuro or {}
    cpu = _num((system.get("cpu") or {}).get("percent"))
    mem = _num((system.get("memory") or {}).get("percent"))
    parts = (system.get("disk") or {}).get("partitions") or []
    disk_peaks: list[tuple[float, str]] = []
    for p in parts:
        try:
            disk_peaks.append((float(p.get("percent")), str(p.get("mount", "?"))))
        except (TypeError, ValueError):
            continue
    disk_max, disk_mount = max(disk_peaks or [(0.0, "?")], key=lambda t: t[0])
    temps = [(_num(t.get("current")) or 0.0)
             for t in ((system.get("sensors") or {}).get("temperatures") or [])]
    temp_max = max(temps or [0.0])
    db = bool(kuro.get("db_present"))
    age = _num(kuro.get("heartbeat_age_min"))

    if db and age is not None and age >= 15:
        return "critical", f"daemon silencieux depuis {age:.0f} min"
    if disk_max >= 95:
        return "critical", f"disque {disk_mount} plein a {disk_max:.0f}%"
    if (cpu or 0.0) >= 90 or (mem or 0.0) >= 95 or temp_max >= 85:
        worst = max(cpu or 0.0, mem or 0.0, temp_max)
        return "critical", f"machine en surchauffe ({worst:.0f})"
    if db and age is None:
        return "worried", "aucun battement de daemon enregistre"
    if (db and age is not None and age >= 5) or (cpu or 0.0) >= 75 \
            or (mem or 0.0) >= 85 or disk_max >= 85 or temp_max >= 70:
        if db and age is not None and age >= 5:
            return "worried", f"daemon STALE depuis {age:.0f} min"
        return "worried", "charge elevee, a surveiller"
    if cpu is not None and cpu < 8:
        return "idle", "calme plat, rien ne force"
    return "happy", "tout va bien"


def should_blink(now: float | None) -> bool:
    """Clignement bref : 0.25s toutes les 4s (None = yeux ouverts)."""
    return now is not None and (now % 4.0) < 0.25


def spinner(now: float | None) -> str:
    """Caractere d activite qui tourne (preuve que ca rafraichit)."""
    return SPINNER[int((now or 0.0) * 2) % 4]


def face_frame(mood: str, blink: bool = False) -> list[str]:
    """Les 2 lignes du visage (humeur inconnue -> CONTENT par defaut)."""
    art = FACES.get(mood, FACES["happy"])
    return list(art[1] if blink else art[0])
