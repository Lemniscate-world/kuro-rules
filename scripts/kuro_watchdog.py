#!/usr/bin/env python3
"""kuro_watchdog.py — surveillance post-merge : merge rouge -> PR de revert + Discord.

Pour chaque merge recent (48h) non encore vu : verifie les checks du commit
de merge. Si rouge -> ouvre une PR de revert (jamais de push direct ni de
merge auto) et alerte Discord. Sinon marque vu et passe.

Usage:
  python scripts/kuro_watchdog.py            # dry-run : lecture seule
  python scripts/kuro_watchdog.py --write --max 5
"""

import argparse
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ci_guardian import DEFAULT_OWNERS, _git, api, discover_all  # noqa: E402

import kuro_proposals as P  # noqa: E402

STORE = Path(__file__).resolve().parent.parent / "watchdog.local.json"
WINDOW_HOURS = 48


def _load() -> dict:
    try:
        data = json.loads(STORE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(store: dict) -> None:
    try:
        STORE.write_text(json.dumps(store, indent=1, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def recent_merges(repo: str, token: str) -> list:
    st, data = api("GET", f"/repos/{repo}/pulls?state=closed&sort=updated&direction=desc&per_page=10", token)
    if st != 200 or not isinstance(data, list):
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    out = []
    for pr in data:
        if not isinstance(pr, dict) or not pr.get("merged_at"):
            continue
        try:
            when = datetime.fromisoformat(str(pr["merged_at"]).replace("Z", "+00:00"))
        except ValueError:
            continue
        if when >= cutoff:
            out.append(pr)
    return out


def merge_failures(repo: str, sha: str, token: str) -> list:
    st, data = api("GET", f"/repos/{repo}/commits/{sha}/check-runs?per_page=30", token)
    if st != 200 or not isinstance(data, dict):
        return []
    return [c.get("name", "?") for c in data.get("check_runs", [])
            if isinstance(c, dict) and c.get("conclusion") == "failure"]


def open_revert_pr(repo: str, sha: str, number: int, token: str, dry_run: bool) -> str:
    """Clone, revert, push branche revert-*, ouvre la PR. Retourne message."""
    branch = f"revert-{number}-{sha[:7]}"
    if dry_run:
        return f"dry-run : PR de revert {branch} envisagee"
    workdir = Path(tempfile.mkdtemp(prefix="kuro-revert-"))
    try:
        url = f"https://x-access-token:{token}@github.com/{repo}.git"
        ok, out = _git(workdir, "clone", "--depth", "30", "--quiet", url, str(workdir / "repo"))
        if not ok:
            return f"clone impossible : {out[:120]}"
        rd = workdir / "repo"
        _git(rd, "config", "user.name", "github-actions[bot]")
        _git(rd, "config", "user.email", "github-actions[bot]@users.noreply.github.com")
        _git(rd, "checkout", "-b", branch)
        ok, out = _git(rd, "revert", "-m", "1", "--no-edit", sha)
        if not ok:
            return f"revert en conflit, intervention humaine requise : {out[:120]}"
        ok, out = _git(rd, "push", "origin", f"HEAD:{branch}")
        if not ok:
            return f"push revert impossible : {out[:120]}"
        st, data = api("POST", f"/repos/{repo}/pulls", token,
                       {"title": f"Revert #{number} (merge rouge, watchdog)",
                        "head": branch, "base": "main",
                        "body": f"Revert automatique de #{number} ({sha[:7]}) : checks rouges "
                                f"apres merge. A relire avant merge."})
        if st in (200, 201) and isinstance(data, dict):
            return f"PR de revert ouverte : {data.get('html_url', branch)}"
        return "creation PR revert impossible"
    finally:
        import shutil
        shutil.rmtree(workdir, ignore_errors=True)


def watch_repo(repo: str, token: str, write: bool) -> list[str]:
    store = _load()
    seen_repo = store.setdefault("seen", {}).setdefault(repo, [])
    lines = []
    for pr in recent_merges(repo, token):
        sha = (pr.get("merge_commit_sha") or "")
        number = pr.get("number")
        if not sha or sha in seen_repo:
            continue
        failing = merge_failures(repo, sha, token)
        if not failing:
            seen_repo.append(sha)
            continue
        pid = P.add(f"{repo}#{number}", f"Merge #{number} rouge : {', '.join(failing[:3])}",
                    "Checks rouges apres merge. Revert propose, validation humaine requise.",
                    [f"https://github.com/{repo}/pull/{number}"])
        if not write:
            lines.append(f"{repo}#{number} rouge ({pid}) : dry-run, pas de revert")
        elif not P.budget_use("revert_pr"):
            lines.append(f"{repo}#{number} rouge ({pid}) : budget revert epuise")
        else:
            lines.append(f"{repo}#{number} rouge ({pid}) : {open_revert_pr(repo, sha, number, token, False)}")
        seen_repo.append(sha)
    _save(store)
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Watchdog post-merge Kuro")
    ap.add_argument("--owners", nargs="+", default=DEFAULT_OWNERS)
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--max", type=int, default=10)
    a = ap.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        print("GH_TOKEN absent — surveillance impossible")
        return 0
    write = a.write and not P.vacances()
    if P.vacances():
        print("mode vacances : lecture seule forcee")
    print(f"=== KURO WATCHDOG write={write} ===")
    lines: list[str] = []
    for repo, tok in sorted(discover_all(a.owners, token).items())[:a.max]:
        try:
            lines.extend(watch_repo(repo, tok, write))
        except Exception as e:
            lines.append(f"{repo} : erreur watchdog ({e})")
    print("\n".join(lines) or "Aucun merge rouge recent.")
    if write and lines:
        P.post_discord("[WATCHDOG] Post-merge", [P.polish_fr("\n".join(lines))], color=15158332)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
