# Runbook: regenerate + deploy rule targets

Goal: regenerate all distribution targets from `rules/` and sync to projects.

## Prerequisites

- Python 3.10+ with `pyyaml`
- PowerShell 5.1+ (for `sync-rules.ps1`)

## Steps

1. Preview drift:
   ```bash
   python scripts/generate_targets.py --dry-run
   ```
   Expected: list of files that would change, or "propre".
2. Apply:
   ```bash
   python scripts/generate_targets.py --apply
   ```
   Expected: `OK: wrote 132 targets (N changed).`
3. Verify:
   ```bash
   python scripts/generate_targets.py --check
   python scripts/check_rule_spec.py
   ```
   Expected: exit 0 on both.
4. Deploy to tracked projects (Windows):
   ```powershell
   .\sync-rules.ps1 -DryRun
   .\sync-rules.ps1
   ```
   Expected: `SYNCED -> <project>` lines + `SYNC_LOG.md` entry.
5. Run affected tests:
   ```bash
   python -m pytest tests/test_generate_targets.py tests/test_rule_spec.py -q
   ```
   Expected: all pass.

## Rollback

```bash
git status --short
git checkout -- AGENTS.md .cursor/rules .agents/rules
```
