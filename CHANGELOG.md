# Changelog — kuro-rules

Format: `[MAJOR.MINOR.PATCH]` + git tag `vMAJOR.MINOR.PATCH-kuro` (R19).
`pyproject.toml` version and CHANGELOG entry must match (R91).

## [1.2.0] — 2026-10-13

### Added — recurrence guards (nothing relies on memory)
- `templates/git-hooks/commit-msg.sh` : conventional-commits hook (warn by
  default, `CONVENTIONAL_STRICT=1` to block). release-please depends on it.
- `scripts/install_hooks.py` : deploys `pre-push` + `commit-msg`, `--upgrade`
  replaces kuro-owned hooks only (8 foreign customs left untouched fleet-wide).
- kuro-rules dogfoods release-please (`release-please-config.json` generic /
  `VERSION`, manifest, workflow).
- `scripts/fleet_sync_scheduled.ps1` + `KuroFleetSync` Saturdays 05:00 :
  regenerate + sync + hooks upgrade + snapshot refresh, logged.
- `VERSIONING.md §4b` : guard table.
- Fleet deploy executed: 4663 file syncs, release workflows 5 → 35 OWNED
  repos (17 remaining are EXTERNAL/UNKNOWN forks, correctly excluded per R87).

### Tests
- `test_versioning.py` extended (hooks marker, dogfood, automation wiring).

## [1.1.0] — 2026-10-13

### Added
- `VERSIONING.md` : fleet version governance (one version source per product,
  CHANGELOG mandatory, release-please standard, enforcement ladder).
- `templates/release-please{,-config-node,-config-python,-config-rust,-config-generic}.yml/json`
  + `templates/release-please.yml` : fleet release automation templates.
- `sync-rules.ps1` : deploys release-please workflow (always-on) + config and
  manifest (only if missing, type auto-detected, manifest seeded from current
  version) to OWNED repos.
- `templates/kuro-compliance.yml` : R91-fleet job (warning, `VERSIONING_STRICT=1`
  to fail).
- `scripts/inventory_versions.py` : read-only fleet audit (`--csv`,
  `--markdown`), `FLEET_VERSIONS.md` tracked snapshot (52 tracked, 29 no
  version, 45 no CHANGELOG, 47 no release workflow, 41 zero `v*` tags).
- `VERSION_TEMPLATE` retired (pointer to `VERSIONING.md`).

### Tests
- `test_versioning.py` (7) — configs, workflow, compliance job, snapshot.

## [1.0.0] — 2026-10-13

### Added
- `scripts/generate_targets.py` : canonical generator (`--dry-run` by default,
  `--check` for CI, `--apply` to write). Replaces symlink-only distribution.
- Multi-format targets from `rules/rule_*.md` : `AGENTS.md`, `CLAUDE.md`,
  `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `AI_GUIDELINES.md`,
  `copilot-instructions.md`, `.cursor/rules/*.mdc`, `.agents/rules/*.md`,
  `.cursor-plugin/marketplace.json`.
- `rules/_metadata.yaml` : per-rule `scope` (company/team/service),
  `priority`, `status` (active/draft/deprecated), `trigger` (always/auto/manual),
  `paths`/`globs`, `description`. Inheritance `company -> team -> service`.
- `VERSION` : single version source, embedded in generated headers.
- `SPEC.md` : rules vs runbooks vs memories contract (+ validation rules,
  memory frontmatter, migration path). `runbooks/` (with `sync-rules.md`),
  `memories/` (with template + first lesson).
- `scripts/check_rule_spec.py` : hard errors on metadata/runbooks/memories,
  migration warnings on legacy rules.
- `.agents/SCOPING.md` + `.agents/local/` (gitignored personal overrides).
- `scripts/bench_rules.py` : 10/10 controlled mini-benchmark, offline.
- `.github/workflows/kuro-rules-spec.yml` : blocking CI (drift + spec + bench).
- `sync-rules.ps1` : deploys `CLAUDE.md`/`GEMINI.md` + `.cursor/rules`,
  `.agents/rules`, `.cursor-plugin`; step 1 delegates to the generator.
- `install.sh` / `install.ps1` : copy generated targets (no symlinks by
  default), regenerate first, convert legacy symlinks.

### Tests
- `test_generate_targets.py` (9), `test_rule_spec.py` (7),
  `test_scoping.py` (5), `test_bench_rules.py` (2) — 23 new, all green.
- `audit-rules.py --mode repo` green; `ruff` clean on touched files.
