# Project-local Perplexity prompt

Use this prompt for citation-heavy desk research before any marketing, outreach, or strong product claim.

```text
You are doing pre-marketing pain-point due diligence.

Project:
- Name: {{PROJECT_NAME}}
- Geo: {{PRIMARY_GEO}}
- Target user: {{TARGET_USER}}
- Buyer hypothesis: {{BUYER}}
- Pain point hypothesis: {{PAIN_POINT}}
- Proposed product or wedge: {{PRODUCT_WEDGE}}
- Main alternatives today: {{ALTERNATIVES}}

Validation stage:
- Current stage: {{VALIDATION_STAGE}}
- Goal of this run: move from the current stage to the next stage with evidence, not hype.

Research rules:
- Prefer sources from 2025-2026.
- Use a 2024 source only if it is official and structurally important.
- Search in both French and English.
- Prioritize regulators, company pages, primary documentation, strong local business press, recent blogs, and public market analysis.
- Separate verified facts from inference.
- Do not treat market growth or digitization headlines as proof of willingness to pay.

Return these sections:

1. Executive verdict
- Is this pain point real enough to keep validating now?
- Answer: yes, no, or partial.

2. Evidence table
- Use exactly these columns:
  venture | claim | source_url | source_date | geo | signal_type | confidence | what_it_proves | open_question
- Allowed values for signal_type:
  existence du marche
  urgence
  faisabilite
  ne prouve pas la volonte de payer

3. Buyer and budget signal
- Identify the likely buyer, budget line, procurement path, and approval signal if visible.
- Explicitly say what does NOT prove willingness to pay.

4. Competitor and substitute map
- List direct competitors, internal workflows, integrators, and "do nothing" substitutes.

5. Risk scan
- Cover compliance risk, platform risk, operational risk, and reputational risk.
- Explicitly say whether this pain point is safe to market aggressively yet.

6. Validation-stage verdict
- Say whether the evidence is enough to move from:
  - L0 to L1
  - L1 to L2
  - L2 to L3
- If not, list the minimum next research or expert calls still required.
```
