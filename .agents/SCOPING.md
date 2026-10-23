# Scoping — comment le chargement ciblé fonctionne

Source : `agent-rules-spec` RFC + `rules/_metadata.yaml`. Voir `SPEC.md`.

## Triggers

| trigger | Chargement | Usage |
|---|---|---|
| `always` | Session start, tout contexte | Policy globale (sécurité, entrypoint) |
| `auto` | Quand un fichier match `paths`/`globs` | Code quality sur `src/**`, tests sur `tests/**` |
| `manual` | Uniquement sur demande explicite | Marketing (R119-121), procédures situationnelles |

## Champs

- `.agents/rules/*.md` : `name/description/trigger/paths/scope/priority/status`
  (`paths` = globs gitignore-style).
- `.cursor/rules/*.mdc` : `description/alwaysApply/globs`
  (`alwaysApply: true` = always, `false` + `globs` = auto, `false` sans globs = manual).

## Overrides personnels

`.agents/local/rules/*.md` (gitignoré) : même format, jamais écrasé par
`generate_targets.py` ni `sync-rules.ps1`. Le générateur ne touche jamais
à `.agents/local/`.

## Exemples actuels (`rules/_metadata.yaml`)

- `rule_05_06_18_19_38_58_59` : `auto` sur `src/**`, `**/*.py`, `tests/**`
- `rule_119/120/121_marketing*` : `manual`, jamais injectées
- `rule_30_branching` : `auto` sur `.git/**`
- `rule_01_foundation`, `rule_100*` : `always`, priorité 10
