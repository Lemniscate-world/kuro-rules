# RULE 3: Progress Tracking - Full Detail

## Formula
Progress = (Sum of Weight_i * Multiplier_i) - Total_Debt

## Baseline Weights (CEO/Product persona)
| Component | Weight | Complete when |
|-----------|--------|--------------|
| Mom Test | 10% | 5+ interviews, results + decision.md signed |
| Core: Data Extraction | 10% | Working, zero-overhead |
| Core: Semantic Logic | 10% | Raw data -> semantic events |
| Core: Reasoning Engine | 10% | Causal inference, hypothesis ranking |
| Core: Scale/Robustness | 10% | Stress tested, zero memory leaks |
| Test Coverage (60%+) | 20% | pytest --cov shows >= 60% |
| Security & Hardening | 10% | bandit 0 issues, safety 0 critical |
| CI/CD & DevOps | 10% | Pipeline passing on main |
| Documentation & Mkt | 10% | README, CHANGELOG, API docs, 1+ marketing metric |

## Infrastructure Grid (DevOps/MLOps persona)
| Component | Weight |
|-----------|--------|
| Assigned Linear tasks completed | 50% |
| Test coverage on infra code (60%+) | 20% |
| Security scans pass | 15% |
| Documentation updated | 15% |

## Quality Multipliers
- 1.0x: Fully documented, tested, optimized
- 0.8x: Functional and tested, lacking deep docs
- 0.5x: Functional but hacky, no tests

## Validation Debt (subtract from total)
- -10% persistent optimism bias
- -5% per milestone reached without VALIDATION_PASSED
- -5% if security scans missing or red
- -5% if R17 skipped for phase transition

## Sanity check
"If this feature were deleted today, what % of the MVP would be missing?"

## Enforcement
Never inflate progress to make user happy.
STOP and recalculate if % > actual completion.