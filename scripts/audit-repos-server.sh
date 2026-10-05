#!/bin/bash
for d in ~/repos/*/; do
  n=$(basename "$d")
  if [ -d "$d/.git" ]; then
    echo "$n: $(git -C "$d" log --oneline -1 2>&1 | head -n 1)"
  else
    echo "$n: NO-GIT ($(ls "$d" | wc -l) entries)"
  fi
done
