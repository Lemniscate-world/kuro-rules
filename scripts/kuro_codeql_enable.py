import json
import subprocess
import sys
import urllib.request
import urllib.error

TOKEN = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True).stdout.strip()
API = "https://api.github.com"


def api(method, path, payload=None):
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "Kuro/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode(errors="replace"))
        except Exception:
            return e.code, {}


def repos_of(owner):
    st, data = api("GET", f"/users/{owner}/repos?per_page=100")
    if st != 200:
        return []
    return [
        f"{owner}/{r['name']}"
        for r in data
        if not r.get("archived") and not r.get("fork") and not r.get("disabled")
    ]


ok, skipped, errors = [], [], []
for owner in ["LambdaSection", "Lemniscate-world"]:
    for repo in repos_of(owner):
        st, resp = api(
            "PATCH",
            f"/repos/{repo}/code-scanning/default-setup",
            {"query_suite": "default", "state": "configured"},
        )
        if st in (200, 202):
            ok.append(repo)
            print(f"CODEQL ON  {repo}")
        elif st == 409 and "already" in str(resp).lower():
            ok.append(repo)
            print(f"CODEQL ON  {repo} (déjà actif)")
        else:
            msg = str(resp.get("message", ""))[:80]
            skipped.append(repo)
            print(f"SKIP       {repo}: HTTP {st} {msg}")

print("---")
print(f"CodeQL actif: {len(ok)} · ignorés (langage non supporté/autre): {len(skipped)}")
