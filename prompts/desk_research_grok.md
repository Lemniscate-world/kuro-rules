# Desk Research Prompt - Grok

**Use this prompt for social signals, tweets, blogs, forums, and founder commentary.**

---

## Prompt

```text
I need to gather social signals and public commentary to validate a startup hypothesis.

PROJECT:
- Name: [Project Name]
- Hypothesis: [The problem you're validating]
- Target user: [Who has this problem]
- Time period: Focus on 2025-2026 signals

MISSION:
Search recent public signals from 2025-2026 across these channels:
- Twitter/X posts and threads
- LinkedIn posts
- Blog posts
- Reddit threads
- Hacker News discussions
- Discord/Slack community chatter
- App reviews (if relevant)

LOOK FOR:
1. User complaints about [problem area]
2. Recurring pain language
3. Process failures
4. Integration pain
5. Platform/tool limitations
6. Competitor weaknesses
7. Public signs of urgency

SIGNAL STRENGTH:
- STRONG: Multiple mentions, high engagement, specific examples
- MEDIUM: Some engagement, anecdotal but consistent
- WEAK: Single mention, low engagement, vague

RULES:
- Every signal MUST include direct URL and date
- Label weak signals as "weak" - do not overstate
- Do NOT present social chatter as proof of willingness to pay
- Separate operational pain from generic hype
- Prioritize verifiable accounts (real names, company affiliations)

OUTPUT FORMAT:

1. SIGNAL LOG (minimum 15 signals)
   | Date | Source Type | URL | Actor | Country | Signal | Strength | What It Suggests | Why It's Not Enough |
   |------|-------------|-----|-------|---------|--------|----------|------------------|---------------------|
   |      |             |     |       |         |        |          |                  |                     |

2. PAIN-POINT SYNTHESIS
   - Is there a real operational pain or just generic hype?
   - Frequency of mentions:
   - Consistency across sources:
   - Specificity of complaints:

3. RISK AND SAFETY SYNTHESIS
   - Platform dependency risks identified:
   - Compliance/regulatory risks:
   - Reputational risks for aggressive marketing:

4. COMPETITOR AND SUBSTITUTE SYNTHESIS
   - Real substitute is: [incumbent vendor/internal team/spreadsheet/email/agency/do nothing]
   - Why users choose current solution:
   - Pain points with current solution:

5. VALIDATION-STAGE VERDICT
   - What can public-signal research confirm?
   - What can it NOT confirm?
   - What expert calls are still mandatory?

VERDICT CRITERIA:
- Strong validation: 10+ STRONG signals, consistent pattern, clear pain language
- Partial validation: 5+ MEDIUM signals, some consistency, need more research
- Weak validation: <5 signals, inconsistent, dominated by hype/noise
```

---

## Usage Instructions

1. Fill in the PROJECT details
2. Run this prompt in Grok (grok.x.ai)
3. Cross-reference with Perplexity results
4. Copy to `validation_evidence.md` under "Social Signals"
5. Note signal strength and limitations

---

## Quality Checklist

- [ ] 15+ signals collected
- [ ] URLs and dates verified
- [ ] Signal strength labeled
- [ ] Weak signals flagged
- [ ] Pain is operational (not just hype)
- [ ] Substitute identified
- [ ] Risks assessed

