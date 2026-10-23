---
type: lesson
scope: company
applies_to: ["scripts/generate_targets.py"]
why: PowerShell 5.1 console misrenders UTF-8, masking real BOM bugs
promote_to_rule: false
---

# 2026-10-13 — Verify UTF-8 with bytes, not console output

## Lesson

`Get-Content` in PowerShell 5.1 renders UTF-8 em-dashes as `?`, identical
to a real encoding bug. 16 rule files carry a real BOM that leaked a
`\ufeff` into generated targets until the generator read with `utf-8-sig`.

## How to apply

- Read/write generated files with `encoding="utf-8-sig"` on read,
  `encoding="utf-8"` on write.
- Assert `'\ufeff' not in content` in tests instead of eyeballing console.
