## 2026-03-12 13:20
- Implemented proposals A-G in kuro-rules.
- Added local pre-commit audit hook using repo mode: `python audit-rules.py --mode repo --scope all`.
- Added GitHub Actions workflow `.github/workflows/rules-audit.yml` to run repo-mode audit and upload reports.
- Added advanced `audit-rules.py` with repo/workspace modes, `--fix-safe`, Markdown/CSV reports, and projects.txt duplicate checks.
- Documented canonical file map, audit modes, and projects.txt policy in README.md.
- Harmonized active rule text across AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, and copilot-instructions.md to reference the master `copilot-instructions.md` source and project target `.github/copilot-instructions.md`.
- Resynchronized tracked repositories after master rule changes.
- Final verification passed in both repo mode and workspace mode.

﻿# Sync Log

## 2026-03-12 12:58:54
- AEther : SYNCED C:\Users\Utilisateur\Documents\AEther\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\AEther\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\AEther\GAD.md, SYNCED C:\Users\Utilisateur\Documents\AEther\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\AEther\.github\copilot-instructions.md
- Astral : SYNCED C:\Users\Utilisateur\Documents\Astral\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Astral\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Astral\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Astral\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Astral\.github\copilot-instructions.md
- Automatons : SYNCED C:\Users\Utilisateur\Documents\Automatons\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Automatons\.github\copilot-instructions.md
- BloomDB : SYNCED C:\Users\Utilisateur\Documents\BloomDB\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\GAD.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\BloomDB\.github\copilot-instructions.md
- Charmed : SYNCED C:\Users\Utilisateur\Documents\Charmed\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Charmed\.github\copilot-instructions.md
- datalint : SYNCED C:\Users\Utilisateur\Documents\datalint\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\datalint\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\datalint\GAD.md, SYNCED C:\Users\Utilisateur\Documents\datalint\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\datalint\.github\copilot-instructions.md
- Dissect : SYNCED C:\Users\Utilisateur\Documents\Dissect\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Dissect\.github\copilot-instructions.md
- Echo : SYNCED C:\Users\Utilisateur\Documents\Echo\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Echo\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Echo\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Echo\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Echo\.github\copilot-instructions.md
- Helium : SYNCED C:\Users\Utilisateur\Documents\Helium\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Helium\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Helium\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Helium\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Helium\.github\copilot-instructions.md, WARN legacy root copilot-instructions.md differs from canonical .github copy in C:\Users\Utilisateur\Documents\Helium
- Iroko : SYNCED C:\Users\Utilisateur\Documents\Iroko\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Iroko\.github\copilot-instructions.md
- Kapok : SYNCED C:\Users\Utilisateur\Documents\Kapok\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Kapok\.github\copilot-instructions.md
- Lemniscate-world : SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\.github\copilot-instructions.md
- Metatron : SYNCED C:\Users\Utilisateur\Documents\Metatron\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Metatron\.github\copilot-instructions.md
- Neural-Again : SYNCED C:\Users\Utilisateur\Documents\Neural-Again\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\.github\copilot-instructions.md
- Neural-Aquarium : SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\.github\copilot-instructions.md
- NeuralDBG : SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\.github\copilot-instructions.md
- NeuralDSL : SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\.github\copilot-instructions.md
- NeuralPaper : SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\.github\copilot-instructions.md
- Neural-Research : SYNCED C:\Users\Utilisateur\Documents\Neural-Research\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\.github\copilot-instructions.md
- NeuroDose : SYNCED C:\Users\Utilisateur\Documents\NeuroDose\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\.github\copilot-instructions.md
- OpenQuant : SYNCED C:\Users\Utilisateur\Documents\OpenQuant\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\GAD.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\.github\copilot-instructions.md
- Playground : SYNCED C:\Users\Utilisateur\Documents\Playground\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Playground\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Playground\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Playground\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Playground\.github\copilot-instructions.md, WARN legacy root copilot-instructions.md differs from canonical .github copy in C:\Users\Utilisateur\Documents\Playground
- Project-Dirac : SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\.github\copilot-instructions.md
- Sagittarius : SYNCED C:\Users\Utilisateur\Documents\Sagittarius\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\.github\copilot-instructions.md, WARN legacy root copilot-instructions.md differs from canonical .github copy in C:\Users\Utilisateur\Documents\Sagittarius
- TokenWise : SYNCED C:\Users\Utilisateur\Documents\TokenWise\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\GAD.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\TokenWise\.github\copilot-instructions.md
- Vault : SYNCED C:\Users\Utilisateur\Documents\Vault\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Vault\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Vault\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Vault\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Vault\.github\copilot-instructions.md
- Verbose : SYNCED C:\Users\Utilisateur\Documents\Verbose\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Verbose\.github\copilot-instructions.md

## 2026-03-12 13:00
- Added preventive guardrails to install.sh, install.ps1, and sync-rules.ps1 so legacy root copilot-instructions.md copies are removed automatically only when they are identical to the canonical .github copy.
- Added audit-rules.py to validate repository existence, rule-file parity, AGENTS rule-number parity, canonical .github/copilot-instructions.md presence, and absence of legacy root copies.
- Updated README.md with explicit canonical path policy and audit usage instructions.
- Verification result: audit-rules.py passed for 23 repositories.

## 2026-03-12 12:30
- Canonical location decision: standardized GitHub Copilot repository instructions on .github/copilot-instructions.md based on GitHub Docs plus local install/sync scripts.
- Removed MetatronCube from projects.txt because the repository directory does not exist.
- Created backups for duplicate removal at C:/Users/Utilisateur/Documents/kuro-rules/SYNC_BACKUPS/2026-03-12_1230_copilot_dedup
- Verified all duplicate root and .github copies were byte-identical before deletion.
- Removed redundant root copilot-instructions.md copies from: Astral, Automatons, BloomDB, Charmed, datalint, Dissect, Echo, Lemniscate-world, Metatron, Neural-Again, Neural-Aquarium, Neural-Research, NeuralDBG, NeuralDSL, NeuralPaper, NeuroDose, OpenQuant, Project-Dirac, TokenWise, Vault, Verbose.
- Final verification: 23 repositories valid with canonical .github/copilot-instructions.md and no root duplicates remaining.

## 2026-03-12 12:00
- Global careful sync: verified rule-number parity before overwrite to ensure no custom rules would disappear.
- Backups created at C:/Users/Utilisateur/Documents/kuro-rules/SYNC_BACKUPS/2026-03-12_1200_rule_sync
- Synced AGENTS.md and copilot-instructions.md across: Astral, Automatons, BloomDB, Charmed, Dissect, Echo, Lemniscate-world, Metatron, Neural-Again, Neural-Aquarium, Neural-Research, NeuralDBG, NeuralDSL, NeuralPaper, NeuroDose, OpenQuant, Project-Dirac, TokenWise, Vault, Verbose, Iroko, Kapok.
- Updated all existing copilot-instructions.md locations, including duplicate .github copies, to prevent hidden rule drift.
- Verification result: 23 repositories fully aligned with kuro-rules master; MetatronCube skipped because repository directory is missing.

## 2026-03-12 11:48
- Datalint : SYNCED AGENTS.md (3315 lines, RULE 38/39 added), SYNCED copilot-instructions.md (623 lines), CREATED mom_test_template.md
- Status: All rule files now synchronized with kuro-rules master


ï»¿# Sync Log



## 2026-03-11 12:07:51

- AEther : SYNCED C:\Users\Utilisateur\Documents\AEther\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\AEther\GAD.md, SYNCED C:\Users\Utilisateur\Documents\AEther\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\AEther\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\AEther\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\AEther\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\AEther\research\README.md, CREATED C:\Users\Utilisateur\Documents\AEther\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\AEther\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\AEther\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\AEther\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\AEther\.gitignore

- Astral : SYNCED C:\Users\Utilisateur\Documents\Astral\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Astral\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Astral\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Astral\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Astral\.github\copilot-instructions.md

- Automatons : SYNCED C:\Users\Utilisateur\Documents\Automatons\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Automatons\.github\copilot-instructions.md

- BloomDB : SYNCED C:\Users\Utilisateur\Documents\BloomDB\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\GAD.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\BloomDB\.github\copilot-instructions.md

- Charmed : SYNCED C:\Users\Utilisateur\Documents\Charmed\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Charmed\.github\copilot-instructions.md

- datalint : SYNCED C:\Users\Utilisateur\Documents\datalint\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\datalint\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\datalint\GAD.md, SYNCED C:\Users\Utilisateur\Documents\datalint\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\datalint\.github\copilot-instructions.md

- Dissect : SYNCED C:\Users\Utilisateur\Documents\Dissect\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Dissect\.github\copilot-instructions.md

- Echo : SYNCED C:\Users\Utilisateur\Documents\Echo\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Echo\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Echo\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Echo\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Echo\.github\copilot-instructions.md

- Helium : SYNCED C:\Users\Utilisateur\Documents\Helium\.github\copilot-instructions.md

- Iroko : SYNCED C:\Users\Utilisateur\Documents\Iroko\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Iroko\.github\copilot-instructions.md

- Kapok : SYNCED C:\Users\Utilisateur\Documents\Kapok\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Kapok\.github\copilot-instructions.md

- Lemniscate-world : SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\.github\copilot-instructions.md

- Metatron : SYNCED C:\Users\Utilisateur\Documents\Metatron\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Metatron\.github\copilot-instructions.md

- Neural-Again : SYNCED C:\Users\Utilisateur\Documents\Neural-Again\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\.github\copilot-instructions.md

- Neural-Aquarium : SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\.github\copilot-instructions.md

- NeuralDBG : SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\.github\copilot-instructions.md

- NeuralDSL : SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\.github\copilot-instructions.md

- NeuralPaper : SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\.github\copilot-instructions.md

- Neural-Research : SYNCED C:\Users\Utilisateur\Documents\Neural-Research\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\.github\copilot-instructions.md

- NeuroDose : SYNCED C:\Users\Utilisateur\Documents\NeuroDose\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\.github\copilot-instructions.md

- OpenQuant : SYNCED C:\Users\Utilisateur\Documents\OpenQuant\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\GAD.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\.github\copilot-instructions.md

- Playground : SYNCED C:\Users\Utilisateur\Documents\Playground\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Playground\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Playground\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Playground\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Playground\.github\copilot-instructions.md

- Project-Dirac : SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\.github\copilot-instructions.md

- Sagittarius : SYNCED C:\Users\Utilisateur\Documents\Sagittarius\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\.github\copilot-instructions.md

- TokenWise : SYNCED C:\Users\Utilisateur\Documents\TokenWise\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\GAD.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\TokenWise\.github\copilot-instructions.md

- Vault : SYNCED C:\Users\Utilisateur\Documents\Vault\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Vault\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Vault\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Vault\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Vault\.github\copilot-instructions.md

- Verbose : SYNCED C:\Users\Utilisateur\Documents\Verbose\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Verbose\.github\copilot-instructions.md



## 2026-03-09
- Global: RENAMED Rule 41 to Rule 45 (PR Analysis & Improvement)
- Global: ADDED Rule 41 (Personal Quant Mode - PQPO)
- SYNCED: AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md in kuro-rules and NeuralDBG
## 2026-03-06 15:25:11

- Astral : SYNCED C:\Users\Utilisateur\Documents\Astral\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Astral\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Astral\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Astral\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Astral\.github\copilot-instructions.md

- Automatons : SYNCED C:\Users\Utilisateur\Documents\Automatons\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Automatons\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Automatons\.github\copilot-instructions.md

- BloomDB : SYNCED C:\Users\Utilisateur\Documents\BloomDB\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\GAD.md, SYNCED C:\Users\Utilisateur\Documents\BloomDB\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\BloomDB\.github\copilot-instructions.md

- Charmed : SYNCED C:\Users\Utilisateur\Documents\Charmed\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Charmed\.github\copilot-instructions.md

- datalint : SYNCED C:\Users\Utilisateur\Documents\datalint\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\datalint\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\datalint\GAD.md, SYNCED C:\Users\Utilisateur\Documents\datalint\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\datalint\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\datalint\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\datalint\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\datalint\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\datalint\research\README.md, CREATED C:\Users\Utilisateur\Documents\datalint\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\datalint\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\datalint\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\datalint\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\datalint\.gitignore

- Dissect : SYNCED C:\Users\Utilisateur\Documents\Dissect\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Dissect\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Dissect\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Dissect\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Dissect\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Dissect\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Dissect\research\README.md, CREATED C:\Users\Utilisateur\Documents\Dissect\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Dissect\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Dissect\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Dissect\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Dissect\.gitignore

- Echo : SYNCED C:\Users\Utilisateur\Documents\Echo\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Echo\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Echo\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Echo\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Echo\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Echo\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Echo\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Echo\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Echo\research\README.md, CREATED C:\Users\Utilisateur\Documents\Echo\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Echo\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Echo\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Echo\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Echo\.gitignore

- Helium : SYNCED C:\Users\Utilisateur\Documents\Helium\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Helium\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Helium\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Helium\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Helium\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Helium\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Helium\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Helium\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Helium\research\README.md, CREATED C:\Users\Utilisateur\Documents\Helium\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Helium\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Helium\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Helium\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Helium\.gitignore

- Iroko : SYNCED C:\Users\Utilisateur\Documents\Iroko\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Iroko\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Iroko\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Iroko\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Iroko\.gitignore

- Kapok : SYNCED C:\Users\Utilisateur\Documents\Kapok\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Kapok\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Kapok\.github\copilot-instructions.md

- Lemniscate-world : SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Lemniscate-world\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\research\README.md, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Lemniscate-world\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Lemniscate-world\.gitignore

- Metatron : SYNCED C:\Users\Utilisateur\Documents\Metatron\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Metatron\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Metatron\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Metatron\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Metatron\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Metatron\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Metatron\research\README.md, CREATED C:\Users\Utilisateur\Documents\Metatron\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Metatron\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Metatron\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Metatron\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Metatron\.gitignore

- Neural-Again : SYNCED C:\Users\Utilisateur\Documents\Neural-Again\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Again\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Neural-Again\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Neural-Again\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Neural-Again\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Neural-Again\research\README.md, CREATED C:\Users\Utilisateur\Documents\Neural-Again\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Neural-Again\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Neural-Again\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Neural-Again\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Neural-Again\.gitignore

- Neural-Aquarium : SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Aquarium\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\research\README.md, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Neural-Aquarium\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Neural-Aquarium\.gitignore

- NeuralDBG : SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralDBG\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\research\README.md, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\NeuralDBG\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\NeuralDBG\.gitignore

- NeuralDSL : SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralDSL\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\research\README.md, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\NeuralDSL\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\NeuralDSL\.gitignore

- NeuralPaper : SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuralPaper\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\research\README.md, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\NeuralPaper\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\NeuralPaper\.gitignore

- Neural-Research : SYNCED C:\Users\Utilisateur\Documents\Neural-Research\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Neural-Research\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Neural-Research\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Neural-Research\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Neural-Research\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Neural-Research\research\README.md, CREATED C:\Users\Utilisateur\Documents\Neural-Research\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Neural-Research\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Neural-Research\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Neural-Research\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Neural-Research\.gitignore

- NeuroDose : SYNCED C:\Users\Utilisateur\Documents\NeuroDose\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\GAD.md, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\NeuroDose\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\NeuroDose\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\NeuroDose\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\NeuroDose\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\NeuroDose\research\README.md, CREATED C:\Users\Utilisateur\Documents\NeuroDose\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\NeuroDose\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\NeuroDose\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\NeuroDose\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\NeuroDose\.gitignore

- OpenQuant : SYNCED C:\Users\Utilisateur\Documents\OpenQuant\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\GAD.md, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\OpenQuant\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\OpenQuant\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\OpenQuant\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\OpenQuant\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\OpenQuant\research\README.md, CREATED C:\Users\Utilisateur\Documents\OpenQuant\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\OpenQuant\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\OpenQuant\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\OpenQuant\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\OpenQuant\.gitignore

- Playground : SYNCED C:\Users\Utilisateur\Documents\Playground\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Playground\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Playground\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Playground\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Playground\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Playground\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Playground\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Playground\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Playground\research\README.md, CREATED C:\Users\Utilisateur\Documents\Playground\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Playground\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Playground\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Playground\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Playground\.gitignore

- Project-Dirac : SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Project-Dirac\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\research\README.md, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Project-Dirac\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Project-Dirac\.gitignore

- Sagittarius : SYNCED C:\Users\Utilisateur\Documents\Sagittarius\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Sagittarius\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Sagittarius\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Sagittarius\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Sagittarius\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Sagittarius\research\README.md, CREATED C:\Users\Utilisateur\Documents\Sagittarius\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Sagittarius\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Sagittarius\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Sagittarius\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Sagittarius\.gitignore

- TokenWise : SYNCED C:\Users\Utilisateur\Documents\TokenWise\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\GAD.md, SYNCED C:\Users\Utilisateur\Documents\TokenWise\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\TokenWise\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\TokenWise\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\TokenWise\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\TokenWise\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\TokenWise\research\README.md, CREATED C:\Users\Utilisateur\Documents\TokenWise\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\TokenWise\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\TokenWise\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\TokenWise\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\TokenWise\.gitignore

- Vault : SYNCED C:\Users\Utilisateur\Documents\Vault\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Vault\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Vault\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Vault\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Vault\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Vault\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Vault\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Vault\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Vault\research\README.md, CREATED C:\Users\Utilisateur\Documents\Vault\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Vault\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Vault\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Vault\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Vault\.gitignore

- Verbose : SYNCED C:\Users\Utilisateur\Documents\Verbose\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Verbose\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Verbose\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Verbose\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Verbose\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Verbose\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Verbose\research\README.md, CREATED C:\Users\Utilisateur\Documents\Verbose\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Verbose\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Verbose\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Verbose\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Verbose\.gitignore



## 2026-03-06 15:25:03

- Charmed : SYNCED C:\Users\Utilisateur\Documents\Charmed\AGENTS.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\AI_GUIDELINES.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\GAD.md, SYNCED C:\Users\Utilisateur\Documents\Charmed\.cursorrules, SYNCED C:\Users\Utilisateur\Documents\Charmed\.github\copilot-instructions.md, CREATED C:\Users\Utilisateur\Documents\Charmed\decision-memo.md, CREATED C:\Users\Utilisateur\Documents\Charmed\prompts\perplexity.md, CREATED C:\Users\Utilisateur\Documents\Charmed\prompts\grok.md, CREATED C:\Users\Utilisateur\Documents\Charmed\research\README.md, CREATED C:\Users\Utilisateur\Documents\Charmed\research\evidence-matrix.csv, CREATED C:\Users\Utilisateur\Documents\Charmed\research\scorecard.md, CREATED C:\Users\Utilisateur\Documents\Charmed\research\open-questions.md, CREATED C:\Users\Utilisateur\Documents\Charmed\research\.gitignore, UPDATED C:\Users\Utilisateur\Documents\Charmed\.gitignore



## 2026-03-06

- Added RULE 39: Pre-Marketing Pain-Point Due Diligence to AGENTS.md, AI_GUIDELINES.md, .cursorrules, copilot-instructions.md, and GAD.md.

- Added reusable prompt templates:

  - MARKETING_MEMORY/perplexity-pain-point-due-diligence.md

  - MARKETING_MEMORY/grok-pain-point-due-diligence.md

- Registered new projects in projects.txt:

  - Iroko

  - Kapok



## 2026-03-04 22:28:26

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuralDBG : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Playground : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py



## 2026-03-02 13:02:27

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 11:38:21

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDBG : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## [2026-03-01] â€” Sync Rule 34 & File Protection

**Author**: Antigravity

**Changes**:

- Added **RULE 34: Strict Project Isolation** to all rule files.

- Reason: Enforce strict scope filtering for project **Sagittarius** on Linear/GitHub.

- Updated `.gitignore` in both `Sagittarius` and `kuro-rules` to include reflection files (`mom_test_script.md`, `decision.md`, `concept/`, etc.).

- Verified parity across: `AGENTS.md`, `AI_GUIDELINES.md`, `.cursorrules`, `copilot-instructions.md`, `GAD.md`.



---



## 2026-03-01 11:19:20

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 11:15:32

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 11:11:49

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 11:08:57

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 11:04:11

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 10:50:47

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 10:50:19

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 10:48:47

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 10:45:38

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 10:37:40

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-03-01 10:33:05

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDBG : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-02-28 09:30:37

- Astral : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Automatons : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- BloomDB : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Charmed : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- datalint : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Dissect : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Echo : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Helium : AGENTS.md, AI_GUIDELINES.md, GAD.md, copilot-instructions.md

- Lemniscate-world : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Metatron : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- MetatronCube : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Neural-Again : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Neural-Aquarium : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Neural-Research : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuralDBG : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuralDSL : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuralPaper : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- NeuroDose : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- OpenQuant : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Project-Dirac : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Sagittarius : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- TokenWise : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Vault : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py

- Verbose : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md, acquisition_tracker.md, sync_summary.py



## 2026-02-27 08:18:11

- Astral : AGENTS.md

- Automatons : AGENTS.md

- BloomDB : AGENTS.md

- Charmed : AGENTS.md

- datalint : AGENTS.md

- Dissect : AGENTS.md

- Echo : AGENTS.md

- Lemniscate-world : AGENTS.md

- Metatron : AGENTS.md

- MetatronCube : AGENTS.md

- Neural-Again : AGENTS.md

- Neural-Aquarium : AGENTS.md

- Neural-Research : AGENTS.md

- NeuralDBG : AGENTS.md

- NeuralDSL : AGENTS.md

- NeuralPaper : AGENTS.md

- NeuroDose : AGENTS.md

- OpenQuant : AGENTS.md

- Project-Dirac : AGENTS.md

- TokenWise : AGENTS.md

- Vault : AGENTS.md

- Verbose : AGENTS.md



## 2026-02-27 06:13:12

- Astral : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AGENTS.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDBG : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-02-27 06:10:00

- **Project Source**: Charmed

- **Files Synced**: AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- **Rule Added**: RULE 22: Feature Focus Rule (MANDATORY)

- **Status**: Synchronized to kuro-rules master.



## 2026-02-26 10:06:03

- Charmed : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



## 2026-02-26 08:56:01

- Astral : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Automatons : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- BloomDB : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Charmed : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- datalint : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Dissect : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Echo : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Lemniscate-world : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Metatron : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- MetatronCube : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Again : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Aquarium : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Neural-Research : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDBG : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralDSL : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuralPaper : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- NeuroDose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- OpenQuant : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Project-Dirac : AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- TokenWise : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Vault : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md

- Verbose : AGENTS.md, AI_GUIDELINES.md, GAD.md, .cursorrules, copilot-instructions.md



# AI Rules Sync Log



## Sync Operation: 2026-02-25



### Files Synced from Master (kuro-rules)

The following rule files were synced to all projects:



1. **AGENTS.md** - Strict, enforceable rules (12 rules)

2. **.cursorrules** - Cursor IDE rules

3. **AI_GUIDELINES.md** - Comprehensive AI guidelines

4. **GAD.md** - General AI directives

5. **copilot-instructions.md** - GitHub Copilot instructions



### Projects Updated



| Project | AGENTS.md | .cursorrules | AI_GUIDELINES.md | GAD.md | copilot-instructions.md |

|---------|-----------|--------------|------------------|--------|-------------------------|

| Neural-Again | Ã¢Å“â€¦ Created | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| Neural-Aquarium | Ã¢Å“â€¦ Created | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| Neural-Research | Ã¢Å“â€¦ Created | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| NeuralDSL | Ã¢Å“â€¦ Created | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| Project-Dirac | Ã¢Å“â€¦ Created | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| OpenQuant | Ã¢Å“â€¦ Created | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| Echo | Ã¢Å“â€¦ Current | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| NeuralDBG | Ã¢Å“â€¦ Source | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced | Ã¢Å“â€¦ Synced |

| Astral | - | - | Ã¢Å“â€¦ Existing | - | Ã¢Å“â€¦ Existing |

| Charmed | - | - | Ã¢Å“â€¦ Existing | - | Ã¢Å“â€¦ Existing |



### Master Copy Location

`c:\Users\Utilisateur\Documents\kuro-rules\`



### Summary

- **Total projects synced**: 10

- **Newly created AGENTS.md**: 6

- **Files synced per project**: 4-5 rule files

- **Total rules in AGENTS.md**: 12 comprehensive rules



### AGENTS.md Rules Included

1. Read Rules First

2. Mom Test Gate  

3. Progress Tracking

4. Session Summary

5. Testing Requirements

6. Security Scanning

7. No Silent Failures

8. Critical Thinking

9. File Protection

10. Sync Rule

11. Roadmap Adherence

12. Roadmap Duration



### Ignored Files

- **NeuroDose\web\node_modules\recharts\AGENTS.md** - Third-party dependency, not a project



All projects now follow the same strict, enforceable rules for AI agent development.






---

## SYNC ENTRY â€“ 2026-03-11

### Action: Manual Sync to Helium Project

**Project**: Helium
**Files Synced**:
- `.cursorrules` â€“ Synced from kuro-rules master
- `AGENTS.md` â€“ Synced from kuro-rules master
- `AI_GUIDELINES.md` â€“ Synced from kuro-rules master
- `copilot-instructions.md` â€“ Synced from kuro-rules master
- `GAD.md` â€“ Synced from kuro-rules master
- `acquisition_tracker.md` â€“ Already identical (no change needed)

**Reason**: User requested verification of rule sync status. Comparison showed 5 out of 6 files were out of sync (missing Rules 41, 45, 47 and encoding differences). All files now synced to match kuro-rules master copy.

**Verification**: All 5 files verified as IDENTICAL after sync.

**Trigger**: User request: "verify if all my rules are synced from kuro-rules"

---

## SYNC ENTRY - 2026-03-12

### Action: Final H-plan audit refinement

**Project**: kuro-rules
**Files Updated**:
- `audit-rules.py` - promoted final staged H-plan logic
- `.pre-commit-config.yaml` - removed duplicated `stages: [pre-commit]`
- `README.md` - documented `NOTICE` behavior for untracked repositories

**Reason**: Finalize the governance adjustment so workspace audits keep visibility into untracked git repositories without failing, and fix a Windows false positive caused by case-sensitive name comparison for tracked paths.

**Verification**:
- `python audit-rules.py --mode repo --scope all` -> PASSED
- `python audit-rules.py --mode workspace --scope all` -> PASSED
- `python -m bandit -r audit-rules.py` -> PASSED
- Remaining untracked repositories are reported as `NOTICE` only

**Backup**:
- `SYNC_BACKUPS/2026-03-12_140026_final_h_plan_notice`

**Timestamp**: 2026-03-12T14:03:16Z
