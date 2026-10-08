#!/usr/bin/env python3
"""kuro_paths — confinement des chemins fournis en CLI (S8707).

Contexte : les scripts sont parfois invoqués par le cron ou via des
arguments assemblés par un LLM. Un `--from-file /etc/passwd` ou un
`--out ../../ailleurs` malveillant ne doit jamais traverser.
`confine_arg()` résout le chemin et exige qu'il reste sous `base`
(ROOT du repo en général) : sinon repli sûr ou refus explicite.

Même pattern que `kuro_anydo._confined_out` / `kuro_strategy._confined_out`,
factorisé pour les 10+ scripts exposés.
"""

from __future__ import annotations

from pathlib import Path


def confine_arg(value: str | Path | None, base: str | Path,
                default: str | None = None) -> Path:
    """Résout un chemin CLI et exige qu'il reste sous `base`.

    Relatif -> résolu depuis `base`. Absolu -> accepté seulement s'il
    reste sous `base` (liens symboliques résolus, `..` neutralisés).
    Hors base : `base / default` si `default` donné, sinon SystemExit(2)
    avec message explicite (jamais silencieux).
    """
    try:
        if not str(value or "").strip():
            raise ValueError("chemin vide")
        raw = Path(str(value)).expanduser()
        resolved_base = Path(base).expanduser().resolve()
        target = ((resolved_base / raw).resolve() if not raw.is_absolute()
                  else raw.resolve())
        if target == resolved_base or resolved_base in target.parents:
            return target
    except Exception:
        pass
    if default is not None:
        return Path(base).expanduser().resolve() / default
    raise SystemExit(f"chemin refusé (hors {base}) : {value}")
