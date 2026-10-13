#!/bin/sh
# Kuro commit-msg — conventional commits pour release-please (VERSIONING.md §3).
# Source de verite: kuro-rules/templates/git-hooks/commit-msg.sh — NE PAS EDITER
# (re-deploye par scripts/install_hooks.py --upgrade).
# Avertit par defaut ; bloque si CONVENTIONAL_STRICT=1.
# Formats acceptes: type: sujet | type(scope): sujet
# types: feat fix docs style refactor perf test build ci chore revert
MSG_FILE="$1"
SUBJECT="$(head -n 1 "$MSG_FILE" 2>/dev/null)"
case "$SUBJECT" in
  feat:*|fix:*|docs:*|style:*|refactor:*|perf:*|test:*|build:*|ci:*|chore:*|revert:*|\
feat\(*\):*|fix\(*\):*|docs\(*\):*|style\(*\):*|refactor\(*\):*|perf\(*\):*|test\(*\):*|\
build\(*\):*|ci\(*\):*|chore\(*\):*|revert\(*\):*)
    exit 0;;
esac
echo "[WARN conventional] '$SUBJECT' n'est pas un conventional commit." >&2
echo "       release-please l'ignorera (pas de bump). Attendu: type: sujet (feat, fix, chore...)." >&2
echo "       Bloquer: CONVENTIONAL_STRICT=1." >&2
if [ "$CONVENTIONAL_STRICT" = "1" ]; then
  echo "[FAIL conventional] commit refuse." >&2
  exit 1
fi
exit 0
