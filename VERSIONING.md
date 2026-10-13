# VERSIONING.md — Fleet Version Governance (kuro-rules)

Single contract for versions across all OWNED products. Enforces R19
(tag every milestone) and R91 (version/CHANGELOG coherence) fleet-wide.
Status: MANDATORY. Rollout: full fleet via `sync-rules.ps1`.

## 1. One version source per product

| Stack | Source | Example |
|---|---|---|
| Node | `package.json` → `version` | `1.5.0` |
| Python | `pyproject.toml` → static `version` | `1.5.0` |
| Rust | `Cargo.toml` → `version` | `0.1.0` |
| Other / multi | `VERSION` file, plain `MAJOR.MINOR.PATCH` | `1.0.0` |

Dynamic-only versions (`attr`, `importlib.metadata` without static anchor)
are allowed only with a matching `CHANGELOG.md` entry (R91 check).

Format: SemVer. `-kuro` suffix while pre-GA (ex `0.2.1-kuro`, OpenQuant).
Git tags: `vMAJOR.MINOR.PATCH[-kuro]` at every validation milestone (R19).

## 2. CHANGELOG.md mandatory

- One `## [x.y.z] — YYYY-MM-DD` section per release.
- `Added / Changed / Fixed` bullets, no novels.
- The R91 compliance job warns when: no version source, no CHANGELOG,
  or CHANGELOG misses the current version. Graduates to blocking once
  the fleet is green (see §5).

## 3. release-please is the fleet standard

Hand-rolled tag discipline failed: 2026-10-13 inventory over 52 present
products → **29 no version, 45 no CHANGELOG, 47 no release workflow,
41 zero `v*` tags**. No `release-please-config.json` anywhere in the fleet
(the only match is inside `Console/node_modules`, a dependency).

`sync-rules.ps1` deploys to OWNED repos (never overwrites custom files):

- `.github/workflows/release-please.yml` (always-on, like compliance)
- `release-please-config.json` — release-type auto-detected:
  `package.json` → node, `Cargo.toml` → rust, `pyproject.toml` → python,
  else generic `VERSION` tracking
- `.release-please-manifest.json` — created only if missing

Existing tag-triggered build workflows (ex Helium `release.yml`) are
complementary: release-please cuts tags + CHANGELOG, they keep building
on tags. Conventional commits required (`feat:`, `fix:`, …) — anything
else is ignored for bumps, never fatal.

## 4. Visibility

- `python scripts/inventory_versions.py` — read-only fleet audit.
  `--csv` for local analysis, `--markdown FLEET_VERSIONS.md` for the
  tracked snapshot (regenerate after each sync run).
- `FLEET_VERSIONS.md` — committed snapshot, same role as `SYNC_LOG.md`.
- Dashboard wiring (versions section from the CSV) is a follow-up, not
  this batch.

## 4b. Recurrence guards (nothing relies on memory)

| Guard | Where | Effect |
|---|---|---|
| `release-please.yml` | every OWNED repo (sync) | bumps + CHANGELOG + tags + releases from commits |
| `commit-msg` git hook | every local repo (`install_hooks.py --upgrade`) | warns on non-conventional commits, blocks with `CONVENTIONAL_STRICT=1` |
| R91-fleet compliance job | every repo via `kuro-compliance.yml` | warns on missing version/CHANGELOG, fails with `VERSIONING_STRICT=1` |
| `KuroFleetSync` scheduled task | Saturdays 05:00 (`Install-KuroScheduledTask.ps1`) | regenerate + sync + hooks upgrade + snapshot refresh |
| `kuro-rules-spec` CI | kuro-rules GitHub Actions | blocks on generator drift, spec errors, bench <10/10 |

## 5. Enforcement ladder

1. **Now (warning):** R91-fleet compliance job warns on missing
   version/CHANGELOG. `VERSIONING_STRICT=1` opts into failure.
2. **Fleet green:** flip the job to blocking, remove the escape hatch.
3. **Steady state:** release-please owns bumps/tags/releases; humans own
   commit messages and milestone scope.

## 6. kuro-rules itself

Dogfoods this spec: `VERSION` + `CHANGELOG.md` + tag `v1.0.0-kuro`
(R19) on milestones. Legacy `VERSION_TEMPLATE` (shell `MAJOR=` format)
is retired — this file replaces it.
