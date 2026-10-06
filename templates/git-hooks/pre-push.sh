#!/bin/sh
# Kuro pre-push — R30 + R5/R6, stack auto-detecte au runtime.
# Source de verite: kuro-rules/templates/git-hooks/pre-push.sh — NE PAS EDITER
# (re-deploye par scripts/install_hooks.py --force). Remplace les copies
# "Oblivion" qui testaient un package en dur absent de ce repo.
ROOT="$(git rev-parse --show-toplevel)" || exit 1
cd "$ROOT" || exit 1
FAIL=0

# R30: nommage de branche
BRANCH="$(git symbolic-ref --short HEAD 2>/dev/null)"
case "$BRANCH" in
  main|master|develop|feat/*|fix/*|infra/*|ceo/*|sec/*|chore/*|docs/*|test/*)
    echo "[OK] branch: $BRANCH";;
  *)
    echo "[FAIL R30] branche '$BRANCH' non conforme"; exit 1;;
esac

# Python: pytest si tests detectes
if [ -d tests ] || [ -d test ] || ls test_*.py pytest.ini tox.ini setup.cfg 1>/dev/null 2>&1; then
  if command -v python >/dev/null 2>&1; then
    echo "[1] pytest"
    if ! python -m pytest -q -p no:cacheprovider; then echo "[FAIL] pytest"; FAIL=1; fi
  else
    echo "[SKIP] pytest (python absent)"
  fi
else
  echo "[SKIP] pytest (pas de tests)"
fi

# R6: bandit AVERTISSEMENT seul (jamais bloquant pre-push) : les findings
# Low/Medium pre-existants (B110 try/except/pass...) relevent du triage
# CI/revue, pas du blocage push. L'ancien hook bloquait par erreur
# (package en dur absent) ; on ne remplace pas un blocage accidentel
# par un blocage de principe. Enforcement via CI (Codacy, kuro_security).
if git ls-files '*.py' | grep -vqE '(^|/)(tests?|test_|.*_test\.py)'; then
  if command -v bandit >/dev/null 2>&1; then
    echo "[2] bandit (avertissement)"
    bandit -r . -q --exclude ./tests,./test,./node_modules,./.venv,./.git || echo "[WARN] bandit: findings a trier (non bloquant)"
  else
    echo "[SKIP] bandit (non installe)"
  fi
else
  echo "[SKIP] bandit (pas de python)"
fi

# JS: test si script present (vitest => --run anti-watch), sinon build si present
if [ -f package.json ]; then
  if command -v npm >/dev/null 2>&1; then
    if node -e "const s=(require('./package.json').scripts||{});process.exit(s.test?0:1)" 2>/dev/null; then
      echo "[3] npm test"
      if node -e "try{const d=require('./package.json');const deps=Object.assign({},d.dependencies,d.devDependencies);process.exit(deps.vitest?0:1)}catch(e){process.exit(1)}" 2>/dev/null; then
        if ! npm test --silent -- --run; then echo "[FAIL] npm test"; FAIL=1; fi
      else
        if ! npm test --silent; then echo "[FAIL] npm test"; FAIL=1; fi
      fi
    elif node -e "const s=(require('./package.json').scripts||{});process.exit(s.build?0:1)" 2>/dev/null; then
      echo "[3] npm run build"
      if ! npm run build --silent; then echo "[FAIL] build"; FAIL=1; fi
    else
      echo "[SKIP] npm (ni test ni build)"
    fi
  else
    echo "[SKIP] npm (non installe)"
  fi
else
  echo "[SKIP] npm (pas de package.json)"
fi

# Rust: cargo check si manifest present (racine ou src-tauri)
if [ -f Cargo.toml ]; then
  if command -v cargo >/dev/null 2>&1; then
    echo "[4] cargo check"
    if ! cargo check; then echo "[FAIL] cargo check"; FAIL=1; fi
  else
    echo "[SKIP] cargo (non installe)"
  fi
elif [ -f src-tauri/Cargo.toml ]; then
  if command -v cargo >/dev/null 2>&1; then
    echo "[4] cargo check (src-tauri)"
    if ! (cd src-tauri && cargo check); then echo "[FAIL] cargo check"; FAIL=1; fi
  else
    echo "[SKIP] cargo (non installe)"
  fi
else
  echo "[SKIP] cargo (pas de Cargo.toml)"
fi

# R113: tauri build complet uniquement sur demande (R113_FULL=1)
if [ "$R113_FULL" = "1" ]; then
  echo "[R113] tauri build"
  if ! npx tauri build; then echo "[FAIL] tauri build"; FAIL=1; fi
fi

if [ "$FAIL" != "0" ]; then echo "[pre-push] BLOQUE - corriger ci-dessus"; exit 1; fi
echo "[pre-push] OK - push autorise"
