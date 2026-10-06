#!/usr/bin/env python3
"""kuro_compute — client Helium pour Kuro (S2, zero dependance).

Kuro demande du compute au mesh Helium quand un projet en a besoin :
- list_offers()                  <- Helium GET /offers
- create_request(...)            -> Helium POST /requests (201)
- get_request_status(request_id) <- Helium GET /requests/{id} + matches

Config (env, tout optionnel) :
  HELIUM_API_URL   defaut http://127.0.0.1:8787 (loopback ; distant via SSH -L
                   ou WireGuard, jamais d exposition 0.0.0.0)
  HELIUM_API_TOKEN Bearer envoye si defini (le daemon Helium l exige sauf /health)

Persistance : chaque demande acceptee (201) est ajoutee a
~/.kuro/compute_queue.json (ecriture atomique tmp->replace) pour survivre
au restart de l API Kuro. Sans mesh, ComputeError est levee et Kuro
continue en local (degradation gracieuse, jamais d invention silencieuse).
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HELIUM_DEFAULT_URL = "http://127.0.0.1:8787"
QUEUE_PATH = Path.home() / ".kuro" / "compute_queue.json"


class ComputeError(Exception):
    """Echec compute avec statut HTTP (4xx passthrough Helium, 502 si injoignable)."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def _base() -> str:
    return os.environ.get("HELIUM_API_URL", HELIUM_DEFAULT_URL).rstrip("/")


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    token = os.environ.get("HELIUM_API_TOKEN", "")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _call(method: str, path: str, payload=None, timeout: int = 10):
    url = f"{_base()}{path}"
    scheme = urllib.parse.urlparse(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ComputeError(502, f"schema URL Helium refuse : {scheme or '(vide)'}")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        # Schema http/https verifie ci-dessus, URL construite (pas d input brut).
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        try:
            body = json.loads(exc.read().decode("utf-8"))
            message = body.get("error", exc.reason) if isinstance(body, dict) else exc.reason
        except Exception:
            message = exc.reason
        raise ComputeError(exc.code, str(message))
    except urllib.error.URLError as exc:
        raise ComputeError(502, f"helium injoignable ({url}) : {exc.reason}")


def list_offers() -> list:
    """Offres GPU/RAM ouvertes sur le mesh (liste vide si aucune)."""
    result = _call("GET", "/offers")
    return result if isinstance(result, list) else []


def _check_request(project: str, rtype: str, amount, max_price, hours, image: str, gpus, template: str = "", min_bench: float = 0.0) -> None:
    if not (project or "").strip():
        raise ComputeError(400, "project est requis (ex. openquant)")
    if not (rtype or "").strip():
        raise ComputeError(400, "rtype est requis (ex. gpu)")
    if not isinstance(amount, int) or isinstance(amount, bool) or not 1 <= amount <= 1024:
        raise ComputeError(400, "amount doit etre un entier entre 1 et 1024")
    if not isinstance(max_price, (int, float)) or isinstance(max_price, bool):
        raise ComputeError(400, "max_price doit etre un nombre")
    if not 0 < float(max_price) <= 1000:
        raise ComputeError(400, "max_price doit etre > 0 et <= 1000")
    if not isinstance(hours, int) or isinstance(hours, bool) or not 1 <= hours <= 720:
        raise ComputeError(400, "hours doit etre un entier entre 1 et 720")
    if len(image or "") > 256:
        raise ComputeError(400, "image doit faire 256 caracteres ou moins")
    if not isinstance(gpus, int) or isinstance(gpus, bool) or not 0 <= gpus <= 16:
        raise ComputeError(400, "gpus doit etre un entier entre 0 et 16")
    if not isinstance(template, str) or len(template or "") > 64:
        raise ComputeError(400, "template doit faire 64 caracteres ou moins")
    if not isinstance(min_bench, (int, float)) or isinstance(min_bench, bool):
        raise ComputeError(400, "min_bench doit etre un nombre")
    if not 0 <= float(min_bench) <= 1e6:
        raise ComputeError(400, "min_bench doit etre entre 0 et 1000000")


def create_request(project: str, rtype: str = "gpu", amount: int = 16,
                   max_price: float = 1.0, hours: int = 2,
                   image: str = "", gpus: int = 0, template: str = "",
                   min_bench: float = 0.0) -> dict:
    """Cree une demande Helium pour un projet Kuro. 201 -> file locale + retour."""
    _check_request(project, rtype, amount, max_price, hours, image, gpus, template, min_bench)
    body = _call("POST", "/requests", {
        "requester": f"kuro:{project.strip()}",
        "rtype": rtype.strip(),
        "amount": amount,
        "max_price": max_price,
        "hours": hours,
        "image": (image or "").strip(),
        "gpus": gpus,
        "template": (template or "").strip(),
        "min_bench": min_bench,
    })
    entry = {
        "request_id": body.get("id", ""),
        "project": project.strip(),
        "rtype": rtype.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": body.get("status", "open"),
    }
    queue_append(entry)
    return {"request_id": entry["request_id"], "project": entry["project"], **body}


def get_request_status(request_id: str) -> dict:
    """Demande + matches courants (404 si inconnue)."""
    if not (request_id or "").strip():
        raise ComputeError(400, "request_id est requis")
    rid = request_id.strip()
    return {
        "request": _call("GET", f"/requests/{rid}"),
        "matches": _call("GET", f"/requests/{rid}/matches"),
    }


def queue_load() -> list:
    try:
        return json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def queue_save(entries: list) -> None:
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = QUEUE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(QUEUE_PATH)


def queue_append(entry: dict) -> list:
    entries = queue_load()
    entries.append(entry)
    queue_save(entries)
    return entries


if __name__ == "__main__":
    import sys
    try:
        if len(sys.argv) > 1 and sys.argv[1] == "offers":
            print(json.dumps(list_offers(), indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"queue": queue_load()}, indent=2, ensure_ascii=False))
    except ComputeError as exc:
        print(json.dumps({"error": exc.message, "status": exc.status}))
        raise SystemExit(1)
