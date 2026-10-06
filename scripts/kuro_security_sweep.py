#!/usr/bin/env python3
"""kuro_security_sweep.py — releve CodeQL + Sonar de tout le portfolio (100% local sauf APIs).

Lecons du pilote (Dissect PR #10, Charmed archive) bakes dedans :
- ignore les repos ARCHIVES (push 403) et les forks (miroirs tiers : findings upstream) ;
- signale les analyses Sonar PÉRIMÉES (ex Charmed : findings sur fichiers supprimes) ;
- lit la cle projet Sonar depuis sonar-project.properties, sinon devine.

Sources : GitHub REST (GITHUB_TOKEN) + SonarCloud REST (SONAR_TOKEN optionnel,
lecture publique sinon). Zero dependance, jamais d exception levee.

Usage:
    GITHUB_TOKEN=... SONAR_TOKEN=... python scripts/kuro_security_sweep.py [--docs DIR] [--json]
    Sortie : reports/security-sweep.json (+ resume humain sans --json).
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DOCS = ROOT_DIR.parent
OUTPUT_FILE = ROOT_DIR / "reports" / "security-sweep.json"
STALE_DAYS = 30


def _github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "kuro-security-sweep/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _sonar_headers() -> dict[str, str]:
    token = os.environ.get("SONAR_TOKEN") or ""
    headers = {"User-Agent": "kuro-security-sweep/1.0"}
    if token:
        basic = base64.b64encode(f"{token}:".encode()).decode()
        headers["Authorization"] = f"Basic {basic}"
    return headers


def _get_json(url: str, headers: dict, timeout: int = 20) -> tuple[Any | None, int]:
    """(data, status). 404/403 -> (None, code), jamais d exception."""
    import urllib.request
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "null"), resp.status
    except Exception as exc:
        code = getattr(exc, "code", 0) or 0
        try:
            code = int(code)
        except Exception:
            code = 0
        return None, code


def parse_github_url(url: str) -> tuple[str, str]:
    """(org, repo) depuis URL https ou git@. ("", "") si illisible."""
    try:
        m = re.search(r"[:/]([^/]+)/([^/]+?)(?:\.git)?$", (url or "").strip())
        if not m:
            return "", ""
        return m.group(1), m.group(2)
    except Exception:
        return "", ""


def local_repos(docs: Path) -> list[dict[str, Any]]:
    """Clones git un niveau sous docs : nom, org, repo, branche. Jamais d exception."""
    out = []
    try:
        children = sorted([p for p in docs.iterdir() if p.is_dir()],
                          key=lambda p: p.name.lower())
    except Exception:
        return out
    for child in children:
        try:
            if child.name == docs.name or child.name == "kuro-rules":
                pass
            done = subprocess.run(
                ["git", "-C", str(child), "config", "--get", "remote.origin.url"],
                capture_output=True, text=True, timeout=15,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            org, repo = parse_github_url(done.stdout.strip()) if done.returncode == 0 else ("", "")
            if not org:
                continue
            br = subprocess.run(
                ["git", "-C", str(child), "branch", "--show-current"],
                capture_output=True, text=True, timeout=15,
                encoding="utf-8", errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            out.append({"name": child.name, "org": org, "repo": repo,
                        "branch": br.stdout.strip() if br.returncode == 0 else ""})
        except Exception:
            continue
    return out


CENTRAL_SONAR_ORG = "Lemniscate-world"


def sonar_key_for(repo_dir: Path, org: str, repo: str) -> str:
    """Cle projet Sonar : sonar-project.properties d abord, sinon Org_Repo."""
    for candidate in (repo_dir / "sonar-project.properties",
                      repo_dir / ".sonarcloud.properties"):
        try:
            if candidate.exists():
                for line in candidate.read_text(encoding="utf-8",
                                                errors="replace").splitlines():
                    line = line.strip()
                    if line.startswith("sonar.projectKey="):
                        return line.split("=", 1)[1].strip()
        except Exception:
            continue
    return f"{org}_{repo}"


def sonar_key_candidates(repo_dir: Path, org: str, repo: str) -> list[str]:
    """Cles essayees dans l ordre : props, Org_Repo, puis org centrale.

    Les projets Sonar vivent souvent sous l org centrale alors que le depot
    est ailleurs (ex Dissect chez AI8, cle Lemniscate-world_Dissect).
    """
    first = sonar_key_for(repo_dir, org, repo)
    keys = [first]
    central = f"{CENTRAL_SONAR_ORG}_{repo}"
    if central not in keys:
        keys.append(central)
    return keys


def check_github(org: str, repo: str) -> dict[str, Any]:
    """Repo GH : archive? + alertes code scanning ouvertes. Jamais d exception."""
    headers = _github_headers()
    info, code = _get_json(f"https://api.github.com/repos/{org}/{repo}", headers)
    if info is None:
        return {"available": False, "http": code, "archived": None, "alerts": []}
    if info.get("archived"):
        return {"available": True, "archived": True, "default_branch": info.get("default_branch"),
                "alerts": [], "note": "archive : corriger = desarchiver d abord"}
    alerts, acode = _get_json(
        f"https://api.github.com/repos/{org}/{repo}/code-scanning/alerts"
        f"?state=open&per_page=100", headers)
    if alerts is None:
        reason = "code scanning non active" if acode in (403, 404) else f"http {acode}"
        return {"available": True, "archived": False,
                "default_branch": info.get("default_branch"),
                "alerts": [], "note": reason}
    slim = [{"number": a.get("number"),
             "severity": ((a.get("rule") or {}).get("severity") or "?"),
             "rule": ((a.get("rule") or {}).get("id") or "?"),
             "path": (((a.get("most_recent_instance") or {}).get("location") or {}).get("path")),
             "line": (((a.get("most_recent_instance") or {}).get("location") or {}).get("start_line"))}
            for a in alerts if isinstance(a, dict)]
    return {"available": True, "archived": False,
            "default_branch": info.get("default_branch"), "alerts": slim}


def check_sonar(key: str) -> dict[str, Any]:
    """Projet Sonar : gate + top issues HIGH/BLOCKER + fraicheur. Jamais d exception."""
    headers = _sonar_headers()
    comp, _ = _get_json(
        "https://sonarcloud.io/api/components/show?component=" + key, headers)
    if not comp:
        return {"available": False, "key": key}
    analyses, _ = _get_json(
        "https://sonarcloud.io/api/project_analyses/search?project=" + key + "&ps=1",
        headers)
    last = ((analyses or {}).get("analyses") or [{}])[0].get("date")
    stale: bool | None = None
    if last:
        try:
            dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if not dt.tzinfo:
                dt = dt.astimezone()
            stale = (datetime.now().astimezone() - dt).days > STALE_DAYS
        except Exception:
            stale = None
    gate, _ = _get_json(
        "https://sonarcloud.io/api/qualitygates/project_status?projectKey=" + key,
        headers)
    issues, _ = _get_json(
        "https://sonarcloud.io/api/issues/search?componentKeys=" + key
        + "&impactSoftwareQualities=SECURITY&issueStatuses=OPEN,CONFIRMED&ps=20",
        headers)
    top = [{"key": i.get("key"), "rule": i.get("rule"),
            "severity": i.get("severity"),
            "file": str(i.get("component", "")).split(":")[-1],
            "line": ((i.get("textRange") or {}).get("startLine")),
            "message": str(i.get("message", ""))[:120]}
           for i in ((issues or {}).get("issues") or [])]
    return {"available": True, "key": key, "last_analysis": last,
            "stale": stale,
            "quality_gate": ((gate or {}).get("projectStatus") or {}).get("status"),
            "security_open": ((issues or {}).get("paging") or {}).get("total"),
            "top_security": top}


def sweep_repo(entry: dict, docs: Path) -> dict[str, Any]:
    """Un repo : GH puis Sonar (cle lue ou devine). Forks et archives signales, pas corriges."""
    name, org, repo = entry["name"], entry["org"], entry["repo"]
    if name.lower().endswith(("-fork", "_fork")):
        return {"name": name, "org": org, "skipped": "fork/miroir : findings upstream, hors scope"}
    gh = check_github(org, repo)
    out: dict[str, Any] = {"name": name, "org": org, "repo": repo,
                           "branch": entry.get("branch", ""), "github": gh,
                           "sonar": {"available": False}}
    if gh.get("archived"):
        return out
    tried = []
    sonar: dict[str, Any] = {"available": False}
    for key in sonar_key_candidates(docs / name, org, repo):
        tried.append(key)
        found = check_sonar(key)
        if found.get("available"):
            sonar = found
            break
    sonar["key_tried"] = ", ".join(tried)
    out["sonar"] = sonar
    return out


def render_human(payload: dict) -> str:
    lines = [f"Security sweep {payload['generated_at']} "
             f"({payload['repo_count']} repos, {payload['with_alerts']} avec alertes)"]
    for r in payload["repos"]:
        if r.get("skipped"):
            lines.append(f"  - {r['name']:<28} SKIP : {r['skipped']}")
            continue
        gh = r.get("github", {})
        sonar = r.get("sonar", {})
        if gh.get("archived"):
            lines.append(f"  - {r['name']:<28} ARCHIVE (desarchiver pour corriger)")
            continue
        bits = []
        alerts = gh.get("alerts", [])
        if alerts:
            sev = {}
            for a in alerts:
                sev[a.get("severity", "?")] = sev.get(a.get("severity", "?"), 0) + 1
            bits.append(f"CodeQL {len(alerts)} ({', '.join(f'{k}:{v}' for k, v in sorted(sev.items()))})")
        if sonar.get("available"):
            stale = " STALE" if sonar.get("stale") else ""
            bits.append(f"Sonar gate={sonar.get('quality_gate')}{stale} "
                        f"secu_ouvertes={sonar.get('security_open')}")
        elif sonar.get("key_tried"):
            bits.append("Sonar absent")
        if not gh.get("available"):
            bits.append(f"GH http={gh.get('http')}")
        elif not alerts and not sonar.get("available"):
            bits.append("RAS")
        lines.append(f"  - {r['name']:<28} " + " · ".join(bits))
    stale_repos = [r["name"] for r in payload["repos"]
                   if (r.get("sonar") or {}).get("stale")]
    if stale_repos:
        lines.append("Analyses Sonar perimees (>30 j, findings peut-etre sur code supprime) : "
                     + ", ".join(stale_repos))
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Releve CodeQL + Sonar du portfolio")
    ap.add_argument("--docs", default=str(DEFAULT_DOCS))
    ap.add_argument("--only", default="",
                    help="noms separes par virgule (defaut : tous)")
    ap.add_argument("--json", action="store_true", help="sortie JSON brute")
    args = ap.parse_args()
    docs = Path(args.docs).expanduser()
    only = {n.strip().lower() for n in args.only.split(",") if n.strip()}
    entries = [e for e in local_repos(docs)
               if not only or e["name"].lower() in only]
    repos = [sweep_repo(e, docs) for e in entries]
    with_alerts = sum(1 for r in repos if (r.get("github") or {}).get("alerts"))
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "repo_count": len(repos), "with_alerts": with_alerts, "repos": repos}
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(payload, indent=1, ensure_ascii=False),
                           encoding="utf-8")
    if args.json:
        print(json.dumps(payload, indent=1, ensure_ascii=False))
    else:
        print(render_human(payload))
        print(f"[+] {OUTPUT_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
