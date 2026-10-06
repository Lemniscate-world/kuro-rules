#!/usr/bin/env python3
"""kuro_replica_push.py — pousse un snapshot coherent de kuro.db vers le standby.

Backup via l API SQLite (jamais de cp sur base ouverte), envoi scp vers
~/.kuro/kuro-replica.db.tmp + mv atomique distant. Prevu pour le
planificateur toutes les 5 min (RPO <= 10 min). Jamais d exception levee.

Usage:
    python scripts/kuro_replica_push.py [--server gad@192.168.1.84] [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC_DB = Path(os.environ.get("KURO_DB", Path.home() / ".kuro" / "kuro.db"))
DST_NAME = "kuro-replica.db"
DEFAULT_SERVER = "gad@192.168.1.84"


def log(message: str) -> None:
    print(f"[replica-push] {message}", flush=True)


def _rotate_own_log(limit: int = 200) -> None:
    """Garde les 200 dernieres lignes de notre log (croissance bornee)."""
    path = Path.home() / ".kuro" / "replica-push.log"
    try:
        if not path.exists():
            return
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > limit:
            path.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")
    except Exception:
        pass


def snapshot_db(src: Path, dst: Path) -> bool:
    """Snapshot coherent via backup API. False si impossible."""
    try:
        if not src.exists():
            return False
        src_conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=10)
        try:
            dst_conn = sqlite3.connect(dst)
            try:
                src_conn.backup(dst_conn)
            finally:
                dst_conn.close()
        finally:
            src_conn.close()
        return dst.exists() and dst.stat().st_size > 0
    except Exception as exc:
        log(f"snapshot impossible : {exc}")
        return False


def _run(cmd: list[str], timeout: int) -> tuple[bool, str]:
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (done.stdout or "") + (done.stderr or "")
        return done.returncode == 0, out
    except Exception as exc:
        return False, str(exc)


def push(server: str, dry_run: bool = False) -> int:
    if not SRC_DB.exists():
        log(f"pas de base locale ({SRC_DB}), rien a pousser")
        return 1
    if dry_run:
        log(f"dry-run : {SRC_DB} -> {server}:~/.kuro/{DST_NAME}")
        return 0
    _rotate_own_log()
    ssh_base = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=15"]
    with tempfile.TemporaryDirectory() as tmp:
        snap = Path(tmp) / DST_NAME
        if not snapshot_db(SRC_DB, snap):
            return 1
        ok, out = _run(["scp", *ssh_base, str(snap),
                        f"{server}:.kuro/{DST_NAME}.tmp"], 180)
        if not ok:
            log(f"scp echec : {out.strip()[:200]}")
            return 1
        ok, out = _run(["ssh", *ssh_base, server,
                        f"mv .kuro/{DST_NAME}.tmp .kuro/{DST_NAME}"], 60)
        if not ok:
            log(f"mv distant echec : {out.strip()[:200]}")
            return 1
    log(f"replica a jour ({datetime.now(timezone.utc):%H:%M:%S}Z)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Push snapshot kuro.db vers standby")
    parser.add_argument("--server", default=os.environ.get("KURO_STANDBY", DEFAULT_SERVER))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    return push(args.server, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
