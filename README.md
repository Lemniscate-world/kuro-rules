# Kuro Rules ⬛

Centralized AI coding guidelines and configuration for all my projects.

## How It Works (Symlinks)

This repository contains the **master copies** of your rules.
When you run the install script, we create **symbolic links** (symlinks) in your target project pointing back here.

```mermaid
graph LR
    A[kuro-rules/AI_GUIDELINES.md] -->|Symlink| B[Sugar/AI_GUIDELINES.md]
    A -->|Symlink| C[Dissect/AI_GUIDELINES.md]
    A -->|Symlink| D[NewProject/AI_GUIDELINES.md]
```

**Benefit:** Edit `kuro-rules/AI_GUIDELINES.md` once, and **ALL** projects are instantly updated.

## Usage

### On Linux / macOS / WSL (Recommended)

1. **Install in a project:**
   ```bash
   ~/Documents/kuro-rules/install.sh /path/to/my-project
   ```

2. **Update all projects:**
   Since they are symlinks, just edit the files in this repo!

### On Windows (PowerShell)

If you are using native Windows (not WSL), symlinks behave differently.
You should check out this repo to `C:\Users\kuro\Documents\kuro-rules`.

**Option A: Junctions (Recommended for Windows)**
Windows "Junctions" or "Soft Links" work similar to Linux symlinks.
You can create a `install.ps1` script (coming soon) or use:
```powershell
New-Item -ItemType SymbolicLink -Path "C:\Path\To\Project\AI_GUIDELINES.md" -Target "C:\Path\To\kuro-rules\AI_GUIDELINES.md"
```

**Option B: Copy Mode**
If symlinks give you trouble on Windows, you can simply *copy* the files. The downside is you lose the "update once, update everywhere" feature.

## New Machine Setup

1. Clone this repo:
   ```bash
   git clone https://github.com/yourusername/kuro-rules.git ~/Documents/kuro-rules
   ```
2. Run `install.sh` on your existing projects.

## The Rules

- **AI_GUIDELINES.md**: High-level principles (Security, Quality, Architecture).
- **.cursorrules**: Instructions for Cursor AI.
- **.pre-commit-config.yaml**: Standard git hooks (linting, security).
- **copilot-instructions.md**: Instructions for GitHub Copilot.

## Kuro Control Center

`kuro-rules` can now act as a local agent intelligence hub for the repos listed in `projects.txt`.
The dashboard turns the rule repository into a control plane for:

- tracked projects across repos and organizations
- rule sync coverage and repo hygiene
- post-mortems, Mom Test artifacts, and knowledge memory
- failure visibility and workflow drift

### Launch the GUI

From PowerShell:

```powershell
.\run-dashboard.ps1
```

This refreshes a local snapshot, serves the dashboard on `http://127.0.0.1:8765`, and opens it in your browser.

### Dashboard data sources

- `projects.txt`
- `KNOWLEDGE_BASE/`
- `AGENTS.md`
- `SYNC_LOG.md`
- git metadata from the tracked repositories in `~/Documents`
