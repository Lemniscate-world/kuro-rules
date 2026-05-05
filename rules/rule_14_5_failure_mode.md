# RULE 14.5: 5-Risk Failure Mode Table - Full Detail

## Trigger: Before first line of production code on any new project.

## The 5 Mandatory Risk Categories
| # | Category | Question to answer |
|---|----------|-------------------|
| 1 | Market Risk | Does the problem exist at scale? Is it painful enough to pay for? |
| 2 | Competition Risk | Is there an incumbent with distribution advantage we cannot overcome? |
| 3 | Technical Risk | Can we actually build this with our current stack and skills? |
| 4 | Regulatory Risk | Are there legal/compliance barriers? GDPR, financial regulations, etc.? |
| 5 | Adoption Risk | Even if we build it, will users change their behavior to use it? |

## Required Format per Risk
Risk: [Name]
Probability: Low / Medium / High
Impact: Low / Medium / High
Evidence FOR this risk: [specific data point or signal]
Evidence AGAINST this risk: [specific data point or signal]
Remedy: [concrete mitigation action]
Kill condition: [at what point do we stop the project over this risk?]

## Scoring
- 3+ HIGH probability + HIGH impact risks -> STOP, redesign or pivot
- 1-2 HIGH risks with clear remedies -> proceed with caution, monitor weekly
- All LOW/MEDIUM -> proceed

## Document Location
Save in: docs/failure_mode_table.md (add to .gitignore if sensitive)

## Enforcement
IF project starts without this table:
  ACTION: STOP, create table before first commit
  DO NOT: Treat this as optional documentation