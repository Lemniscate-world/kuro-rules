# apply_kuro_proposals report

Timestamp: 2026-03-12_125713
Repository root: C:\Users\Utilisateur\Documents\Datalint
kuro-rules: C:\Users\Utilisateur\Documents\kuro-rules
Backup directory: C:\Users\Utilisateur\Documents\kuro-rules\SYNC_BACKUPS\2026-03-12_125713_apply_kuro_proposals

## Changes applied
- Installed audit-rules.py from staging
- Installed .github/workflows/rules-audit.yml from staging
- Added local kuro-rules audit hook to .pre-commit-config.yaml
- Added canonical file map, audit modes, and projects.txt policy to README.md
- Harmonized active policy text in AGENTS.md
- Harmonized active policy text in AI_GUIDELINES.md
- Harmonized active policy text in GAD.md
- Harmonized active policy text in .cursorrules
- Harmonized active policy text in copilot-instructions.md

## Repo mode audit
Return code: 0
Stdout:
AUDIT PASSED: 1 target(s) conform to kuro-rules policy (mode=repo, scope=all)
POLICY: repo mode validates the current kuro-rules repository itself, including master rule files and the root source copilot-instructions.md.
RULE_SET: AGENTS.md, AI_GUIDELINES.md, .cursorrules, GAD.md, copilot-instructions.md -> .github/copilot-instructions.md

Stderr:
(empty)

## Workspace mode audit
Return code: 1
Stdout:
AUDIT FAILED
- Astral: diff .cursorrules
- Astral: diff AGENTS.md
- Astral: diff AI_GUIDELINES.md
- Astral: diff GAD.md
- Astral: diff .github/copilot-instructions.md
- Automatons: diff .cursorrules
- Automatons: diff AGENTS.md
- Automatons: diff AI_GUIDELINES.md
- Automatons: diff GAD.md
- Automatons: diff .github/copilot-instructions.md
- BloomDB: diff .cursorrules
- BloomDB: diff AGENTS.md
- BloomDB: diff AI_GUIDELINES.md
- BloomDB: diff GAD.md
- BloomDB: diff .github/copilot-instructions.md
- Charmed: diff .cursorrules
- Charmed: diff AGENTS.md
- Charmed: diff AI_GUIDELINES.md
- Charmed: diff GAD.md
- Charmed: diff .github/copilot-instructions.md
- datalint: diff .cursorrules
- datalint: diff AGENTS.md
- datalint: diff AI_GUIDELINES.md
- datalint: diff GAD.md
- datalint: diff .github/copilot-instructions.md
- Dissect: diff .cursorrules
- Dissect: diff AGENTS.md
- Dissect: diff AI_GUIDELINES.md
- Dissect: diff GAD.md
- Dissect: diff .github/copilot-instructions.md
- Echo: diff .cursorrules
- Echo: diff AGENTS.md
- Echo: diff AI_GUIDELINES.md
- Echo: diff GAD.md
- Echo: diff .github/copilot-instructions.md
- Lemniscate-world: diff .cursorrules
- Lemniscate-world: diff AGENTS.md
- Lemniscate-world: diff AI_GUIDELINES.md
- Lemniscate-world: diff GAD.md
- Lemniscate-world: diff .github/copilot-instructions.md
- Metatron: diff .cursorrules
- Metatron: diff AGENTS.md
- Metatron: diff AI_GUIDELINES.md
- Metatron: diff GAD.md
- Metatron: diff .github/copilot-instructions.md
- Neural-Again: diff .cursorrules
- Neural-Again: diff AGENTS.md
- Neural-Again: diff AI_GUIDELINES.md
- Neural-Again: diff GAD.md
- Neural-Again: diff .github/copilot-instructions.md
- Neural-Aquarium: diff .cursorrules
- Neural-Aquarium: diff AGENTS.md
- Neural-Aquarium: diff AI_GUIDELINES.md
- Neural-Aquarium: diff GAD.md
- Neural-Aquarium: diff .github/copilot-instructions.md
- Neural-Research: diff .cursorrules
- Neural-Research: diff AGENTS.md
- Neural-Research: diff AI_GUIDELINES.md
- Neural-Research: diff GAD.md
- Neural-Research: diff .github/copilot-instructions.md
- NeuralDBG: diff .cursorrules
- NeuralDBG: diff AGENTS.md
- NeuralDBG: diff AI_GUIDELINES.md
- NeuralDBG: diff GAD.md
- NeuralDBG: diff .github/copilot-instructions.md
- NeuralDSL: diff .cursorrules
- NeuralDSL: diff AGENTS.md
- NeuralDSL: diff AI_GUIDELINES.md
- NeuralDSL: diff GAD.md
- NeuralDSL: diff .github/copilot-instructions.md
- NeuralPaper: diff .cursorrules
- NeuralPaper: diff AGENTS.md
- NeuralPaper: diff AI_GUIDELINES.md
- NeuralPaper: diff GAD.md
- NeuralPaper: diff .github/copilot-instructions.md
- NeuroDose: diff .cursorrules
- NeuroDose: diff AGENTS.md
- NeuroDose: diff AI_GUIDELINES.md
- NeuroDose: diff GAD.md
- NeuroDose: diff .github/copilot-instructions.md
- OpenQuant: diff .cursorrules
- OpenQuant: diff AGENTS.md
- OpenQuant: diff AI_GUIDELINES.md
- OpenQuant: diff GAD.md
- OpenQuant: diff .github/copilot-instructions.md
- Project-Dirac: diff .cursorrules
- Project-Dirac: diff AGENTS.md
- Project-Dirac: diff AI_GUIDELINES.md
- Project-Dirac: diff GAD.md
- Project-Dirac: diff .github/copilot-instructions.md
- TokenWise: diff .cursorrules
- TokenWise: diff AGENTS.md
- TokenWise: diff AI_GUIDELINES.md
- TokenWise: diff GAD.md
- TokenWise: diff .github/copilot-instructions.md
- Vault: diff .cursorrules
- Vault: diff AGENTS.md
- Vault: diff AI_GUIDELINES.md
- Vault: diff GAD.md
- Vault: diff .github/copilot-instructions.md
- Verbose: diff .cursorrules
- Verbose: diff AGENTS.md
- Verbose: diff AI_GUIDELINES.md
- Verbose: diff GAD.md
- Verbose: diff .github/copilot-instructions.md
- Iroko: diff .cursorrules
- Iroko: diff AGENTS.md
- Iroko: diff AI_GUIDELINES.md
- Iroko: diff GAD.md
- Iroko: diff .github/copilot-instructions.md
- Kapok: diff .cursorrules
- Kapok: diff AGENTS.md
- Kapok: diff AI_GUIDELINES.md
- Kapok: diff GAD.md
- Kapok: diff .github/copilot-instructions.md

Stderr:
(empty)
