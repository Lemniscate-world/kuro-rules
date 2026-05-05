# Desk Research Prompt - Perplexity

**Use this prompt for citation-heavy desk research with verifiable sources.**

---

## Prompt

```text
You are conducting rigorous desk research to validate a startup hypothesis.

PROJECT:
- Name: [Project Name]
- Hypothesis: [The problem you're validating]
- Target user: [Who has this problem]
- Time period: Focus on 2025-2026 sources

RESEARCH QUESTION:
[Clear, specific question - e.g., "Do developers in large monorepos struggle with cross-project navigation?"]

SEARCH REQUIREMENTS:
1. Find 10+ verifiable sources (Tier 1 preferred: GitHub issues +10 upvotes, Reddit +50 votes, official forums)
2. Identify 3+ behavioral proofs (pain demonstration, cobbled solutions, willingness to pay, business impact)
3. Use date filters: after:2025-01-01
4. Search in both English and French if applicable

SOURCE TIERS:
- Tier 1 (HIGH): GitHub issues +10 upvotes, Reddit +50 votes, official forums, published studies
- Tier 2 (MEDIUM): Tech blogs, Twitter/LinkedIn threads, Discord communities
- Tier 3 (LOW): Marketing articles, anonymous sources (avoid or flag)

BEHAVIORAL PROOF TYPES:
- Type A - Pain demonstration: "I lose X hours daily on...", vote counts, post frequency
- Type B - Cobbled solutions: "I built a script...", "we use a workaround..."
- Type C - Willingness to pay: "I would pay for...", "if only [tool] existed..."
- Type D - Business impact: "delayed release", "lost $X", "productivity dropped X%"

OUTPUT FORMAT:

1. EXECUTIVE VERDICT
   - Verdict: [ ] GO | [ ] NO-GO | [ ] ADJUST
   - Confidence: [ ] High | [ ] Medium | [ ] Low
   - Summary: 2-3 sentences

2. SOURCES MATRIX (minimum 10)
   | # | Source | Date | Tier | Type | Signal Strength | URL |
   |---|--------|------|------|------|-----------------|-----|
   | 1 |        |      |      |      |                 |     |

3. BEHAVIORAL PROOFS (minimum 3)
   
   Proof 1: [Type - A/B/C/D]
   - Source: 
   - Quote: 
   - What it proves:
   
   Proof 2: [Type - A/B/C/D]
   - Source: 
   - Quote: 
   - What it proves:
   
   Proof 3: [Type - A/B/C/D]
   - Source: 
   - Quote: 
   - What it proves:

4. PATTERNS IDENTIFIED
   - Pattern 1: [Name] - [Description] - Evidence count: X
   - Pattern 2: [Name] - [Description] - Evidence count: X
   - Pattern 3: [Name] - [Description] - Evidence count: X

5. COMPETITIVE LANDSCAPE
   | Competitor | Strength | Weakness | Gap |
   |------------|----------|----------|-----|
   |            |          |          |     |

6. RISK ASSESSMENT
   | Risk | Probability | Impact | Mitigation |
   |------|-------------|--------|------------|
   |      |             |        |            |

7. METHODOLOGY NOTES
   - Search queries used:
   - Channels explored:
   - Limitations:
   - Time spent:

VERDICT CRITERIA:
- GO if: 10+ Tier 1 sources, 3+ behavioral proofs, clear pattern, no critical contradictions
- NO-GO if: <5 sources, <2 proofs, contradictory evidence dominant, problem not validated
- ADJUST if: Partial validation, need more research on specific aspect
```

---

## Usage Instructions

1. Fill in the PROJECT details at the top
2. Run this prompt in Perplexity (perplexity.ai)
3. Review the output for quality
4. Copy results to `validation_evidence.md`
5. Verify all URLs are accessible

---

## Quality Checklist

- [ ] 10+ sources found
- [ ] Sources are Tier 1 or Tier 2
- [ ] 3+ behavioral proofs identified
- [ ] URLs are accessible and dated
- [ ] Direct quotes are exact
- [ ] Verdict is justified by evidence
- [ ] Limitations are documented

