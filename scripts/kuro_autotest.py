#!/usr/bin/env python3
"""kuro_autotest.py — Kuro ecrit lui-meme les tests manquants (100% local, borne).

Deux moteurs :
  1. smoke (defaut, 0 $) : import + presence des fonctions, hermetique.
  2. llm (--llm) : le cerveau (kuro_llm.ask : OpenRouter gratuit d'abord,
     DeepSeek ensuite) genere des tests pytest pour UN module, avec boucle
     de reparation bornee (3 essais). Seuls les fichiers verts sont gardes.

Garde-fous (jamais de spam, jamais de casse) :
  - ecrit UNIQUEMENT dans tests/ : test_<stem>_smoke.py ou test_<stem>_auto.py
  - ne touche JAMAIS au code source
  - saute les stems deja couverts (test_<stem>.py existant)
  - supprime le fichier genere s'il reste rouge apres 3 essais
  - --max N fichiers par run (defaut 1), --dry-run pour relire sans ecrire
  - pytest execute sur le seul fichier genere, jamais sur toute la suite

Usage:
    python scripts/kuro_autotest.py --repo kuro-rules [--llm] [--max 2] [--dry-run]
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))
DOCS_DIR = ROOT_DIR.parent

MAX_REPAIR = 3
DENY = ("rm -rf", "shutil.rmtree", "os.remove", "os.unlink", "os.rmdir",
        "os.system", ":(){:|:&};:", "mkfs", "rd /s",
        "~/Documents", "Path.home()", "C:\\\\", "C:/",
        "Path(__file__).resolve().parent.parent")  # jamais le vrai repo : tmp_path only


def top_functions(source: str) -> list[str]:
    """Noms des fonctions/classes de niveau module. Pur."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [n.name for n in tree.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and not n.name.startswith("_")]


def smoke_source(rel_path: str, names: list[str]) -> str:
    """Test d'import + presence des symboles. Hermetique, zero effet de bord."""
    checks = "\n".join(f'    assert hasattr(mod, "{n}"), "manque {n}"' for n in names)
    return (
        '"""Smoke genere par Kuro (kuro_autotest.py) — import + symboles."""\n'
        "import importlib.util\n"
        "from pathlib import Path\n"
        "\n"
        f'MOD = Path(__file__).resolve().parent.parent / "{rel_path}"\n'
        "\n"
        "\n"
        "def _load():\n"
        '    spec = importlib.util.spec_from_file_location("mod_under_test", MOD)\n'
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(mod)\n"
        "    return mod\n"
        "\n"
        "\n"
        "def test_smoke_imports():\n"
        "    mod = _load()\n"
        f"{checks if checks else '    assert mod is not None'}\n"
    )


def extract_python(text: str) -> str:
    """Premier bloc ```python (ou brut) de la reponse LLM."""
    m = re.search(r"```python[^\n]*\n(.*?)```", text or "", re.DOTALL)
    if m:
        return m.group(1).strip() + "\n"
    m = re.search(r"```[^\n]*\n(.*?)```", text or "", re.DOTALL)
    return (m.group(1).strip() + "\n") if m else (text or "").strip() + "\n"


def looks_safe(code: str) -> bool:
    """Refuse le code destructeur. Pur."""
    low = code.lower()
    return not any(d.lower() in low for d in DENY)


def valid_test_code(code: str) -> bool:
    """Compile + contient au moins un test + sur (pas destructeur)."""
    if "def test_" not in code:
        return False
    if not looks_safe(code):
        return False
    try:
        compile(code, "<genere>", "exec")
    except SyntaxError:
        return False
    return True


def llm_prompt(rel_path: str, source: str, error: str = "") -> str:
    base = (
        f"Ecris des tests pytest pour le module {rel_path} ci-dessous.\n"
        "Contraintes STRICTES : hermetique total — tmp_path + monkeypatch.chdir "
        "uniquement, JAMAIS le vrai ~/Documents ni les vrais fichiers du repo ; "
        "si le code appelle sys.exit, tester avec pytest.raises(SystemExit) ; "
        "mocker subprocess et tout appel systeme/reseau ; 3-8 tests ciblant "
        "les branches (succes, echec, cas limites).\n"
        "Reponds avec UN seul bloc ```python contenant le fichier complet, "
        "sans prose autour.\n\nModule :\n```python\n" + source[:6000] + "\n```"
    )
    if error:
        base += ("\n\nLe test precedent echoue :\n```\n" + error[-1500:] +
                 "\n```\nCorrige et renvoie le fichier complet.")
    return base


def gen_llm_tests(rel_path: str, source: str, error: str = "") -> str:
    from kuro_llm import ask
    text = ask(llm_prompt(rel_path, source, error),
               system="Tu es ingenieur test du studio lambda-Section. "
                      "Tests hermetiques uniquement, concis, sans prose.")
    return extract_python(text or "")


def failure_excerpt(output: str, limit: int = 1200) -> str:
    """Lignes utiles (FAILED/erreurs/assert) + fin du log. Pur."""
    lines = output.splitlines()
    keep = [l for l in lines
            if "FAILED" in l or "Error" in l or "assert" in l or "E  " in l]
    tail = "\n".join(lines[-15:])
    text = ("\n".join(keep[-20:]) + "\n---\n" + tail) if keep else tail
    return text[-limit:]


def run_pytest_file(repo: Path, test_file: Path, timeout: int = 240) -> tuple[bool, str]:
    """Lance pytest sur UN fichier. Retourne (vert, extrait de log)."""
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(test_file), "-q", "-p", "no:cacheprovider"],
            cwd=repo, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired:
        return False, "timeout depasse"
    except Exception as exc:
        return False, str(exc)[:200]
    tail = failure_excerpt(proc.stdout + proc.stderr)
    return proc.returncode == 0, tail


def autotest_repo(repo_name: str, llm: bool = False, max_n: int = 1,
                  dry_run: bool = False, timeout: int = 240) -> list[dict]:
    """Genere jusqu'a max_n fichiers de tests verts. Borne et reversible."""
    import kuro_coverage
    repo = DOCS_DIR / repo_name
    if not repo.is_dir():
        return [{"repo": repo_name, "error": "repo introuvable"}]
    tests_dir = repo / "tests"
    covered = kuro_coverage.test_stems(repo)
    gaps = [u for u in kuro_coverage.static_gaps(repo)["untested"]]
    gaps.sort(key=lambda u: u["lines"])  # petits d'abord : moins cher, victoires rapides
    results: list[dict] = []
    for gap in gaps:
        if len(results) >= max_n:
            break
        stem = Path(gap["path"]).stem
        if stem in covered:
            continue
        src_path = repo / gap["path"]
        try:
            source = src_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        suffix = "auto" if llm else "smoke"
        fname = f"test_{stem}_{suffix}.py"
        dest = tests_dir / fname
        if dest.exists():
            continue
        if llm:
            code = gen_llm_tests(gap["path"], source)
        else:
            code = smoke_source(gap["path"].replace("\\", "/"), top_functions(source))
        if dry_run:
            results.append({"repo": repo_name, "file": fname, "dry_run": True,
                            "lines": len(code.splitlines())})
            continue
        if llm and not valid_test_code(code):
            results.append({"repo": repo_name, "file": fname, "kept": False,
                            "reason": "code invalide ou dangereux : jete"})
            continue
        tests_dir.mkdir(exist_ok=True)
        dest.write_text(code, encoding="utf-8")
        ok, tail = run_pytest_file(repo, dest, timeout)
        tries = 1
        while llm and not ok and tries < MAX_REPAIR:
            code = gen_llm_tests(gap["path"], source, tail)
            if not valid_test_code(code):
                break
            dest.write_text(code, encoding="utf-8")
            ok, tail = run_pytest_file(repo, dest, timeout)
            tries += 1
        if ok:
            results.append({"repo": repo_name, "file": fname, "kept": True,
                            "tries": tries})
        else:
            try:
                dest.unlink()
            except OSError:
                pass
            results.append({"repo": repo_name, "file": fname, "kept": False,
                            "tries": tries, "reason": "rouge apres "
                            + str(tries) + " essai(s) : supprime",
                            "log": tail})
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Kuro ecrit les tests manquants")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--llm", action="store_true", help="vrais tests via le cerveau (sinon smoke gratuit)")
    ap.add_argument("--max", type=int, default=1)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=int, default=240)
    args = ap.parse_args()
    results = autotest_repo(args.repo, llm=args.llm, max_n=args.max,
                            dry_run=args.dry_run, timeout=args.timeout)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0 if any(r.get("kept") or r.get("dry_run") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
