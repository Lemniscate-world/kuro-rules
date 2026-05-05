# RULE 3.5: AI Time Estimation - Full Detail

## Core Principle
Never give deadlines in weeks/months for first estimation. Always decompose into hours/days first.

## MVP Timeline Framework
| Phase | Duration | What it means |
|-------|----------|---------------|
| Prototype | 2-4 days | Core mechanic working, no polish |
| MVP | 2-4 weeks | Usable by 1 real user end-to-end |
| Beta | 4-8 weeks | Usable by 10+ users, feedback loop active |
| V1 | 2-3 months | Stable, documented, distributable |

## Estimation Rules
- Break every feature into tasks <= 4h each
- If a task estimate > 4h, split it
- Add 30% buffer to any estimate
- State estimates as ranges: "2-4 hours" not "3 hours"
- Never say "a few days" - say "2-3 days"

## Red Flags (recalculate if these appear)
- Any single task > 8h -> not decomposed enough
- MVP estimate > 4 weeks for solo dev -> scope too large
- No buffer included -> subtract 15%

## Enforcement
IF user asks "how long will X take?":
  1. Break X into sub-tasks
  2. Estimate each in hours
  3. Sum + 30% buffer
  4. Give range, not point estimate
  DO NOT: Give a single number with false precision