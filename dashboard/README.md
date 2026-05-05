# Kuro Control Center

This folder contains a zero-dependency local dashboard for turning `kuro-rules`
into an agent intelligence workspace.

## What it shows

- tracked repos from `projects.txt`
- git branch, remote, dirty state, and last commit per project
- organization grouping inferred from remote URLs
- rule highlights parsed from `AGENTS.md`
- knowledge memory from `KNOWLEDGE_BASE`
- latest sync pulse from `SYNC_LOG.md`

## Refresh the data

```powershell
python .\dashboard\generate_dashboard.py
```

## Launch the GUI

```powershell
.\run-dashboard.ps1
```
