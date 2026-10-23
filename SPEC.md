# SPEC — Rules vs Runbooks vs Memories (kuro-rules)

Source: `btakita/agent-rules` + `agent-rules-spec` RFC, adapted to kuro-rules.
Status: MANDATORY for new content. Existing `rules/` migrates incrementally
(check script reports warnings, not errors, on legacy files).

## Definitions

| | Rules | Runbooks | Memories |
|---|---|---|---|
| Content | Declarative policy | Imperative procedures | Learned lessons |
| Origin | Prescribed by developer | Prescribed by developer | Captured from experience |
| Format | Sections in `rules/rule_*.md` | One procedure per file in `runbooks/` | One lesson per file in `memories/` with frontmatter |
| Loading | Always-on or scoped (`trigger` in `_metadata.yaml`) | On-demand via file reference | On-demand or indexed |
| Example | "Use snake_case" / "Never commit .env" | "Step 1: run tests, Step 2: stage…" | "Mocking DB masked a broken migration" |

Rules live in `rules/`. The instruction file (AGENTS.md + generated
`.agents/rules/`, `.cursor/rules/`) **references** runbooks and memories
but **contains** rules.

## Validation rules (new content MUST pass)

1. **Actionable, not informational.** Every rule starts with an imperative
   verb (`Use, Prefer, Name, Write, Keep, Run, Check, Verify, Ensure,
   Confirm`) or `Never` / `Do not` / `Always` / `MUST`. Tables of data,
   architecture diagrams, API references belong in separate referenced files.
2. **Declarative, not imperative.** A rule states policy (*what/why*). If it
   reads like a numbered procedure (`Step 1… Step 2…`, 3+ ordered steps),
   it belongs in `runbooks/`.
3. **Size.** One rule file < 1000 lines. One fenced code block <= 10 lines;
   longer samples go to `runbooks/` or a referenced file.
4. **Portable.** Plain markdown, relative paths (`./src/`, `tests/`), no
   tool-specific syntax (`@file`, frontmatter tags) in the rule body.
   Tool wrappers live in generated frontmatter, never in the body.
5. **Atomic.** One statement per item. Split compounds
   ("Use snake_case and also run the linter and make sure tests pass").
6. **Why included.** Non-obvious rules carry the *why* in parentheses or a
   short clause, so the agent does not suggest violating alternatives.
7. **Generated files are read-only.** `.agents/rules/`, `.cursor/rules/`,
   `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, stubs: never hand-edit, run
   `python scripts/generate_targets.py --apply`.

## Directory layout

```text
rules/                  # policy (this spec)
  rule_*.md
  _metadata.yaml        # scope/priority/status/trigger/paths/globs
runbooks/               # procedures, one file per procedure
  <topic>.md            # Step 1..N, concrete commands, expected outputs
memories/               # lessons, one file per lesson
  YYYY-MM-DD-<slug>.md  # frontmatter: type/scope/why/how-to-apply
.agents/
  rules/                # GENERATED from rules/ (do not edit)
  local/rules/          # personal overrides, gitignored
.cursor/rules/          # GENERATED from rules/ (do not edit)
```

## Memory frontmatter

```yaml
---
type: lesson          # lesson | gotcha | decision
scope: company        # company | team | service
applies_to: ["src/**"]
why: one sentence
promote_to_rule: false
---
```

A memory with `promote_to_rule: true` + 2+ independent occurrences
graduates to `rules/` (R89 lessons-learned path).

## Migration

Legacy `rules/` files predate this spec. `scripts/check_rule_spec.py`
enforces hard errors on metadata/runbooks/memories/generated drift, and
reports legacy rule stats as warnings. Split on touch: when you edit a
legacy rule, externalize its procedures to `runbooks/` and its anecdotes
to `memories/`.
