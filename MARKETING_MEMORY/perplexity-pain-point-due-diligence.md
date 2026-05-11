# Perplexity pain-point due diligence prompt

Copy and paste this into Perplexity before marketing a new idea or making a strong product claim.

```text
You are doing pre-marketing pain-point due diligence.

Project:
- Name: [PROJECT_NAME]
- Geo: [COUNTRY_OR_REGION]
- Target user: [TARGET_USER]
- Pain point hypothesis: [PAIN_POINT]
- Proposed product or wedge: [PRODUCT_WEDGE]
- Main alternatives today: [ALTERNATIVES]

Research rules:
- Prefer sources from 2025-2026.
- If you need a 2024 source, use it only if it is official and structurally important, such as regulation or infrastructure.
- Search in both French and English.
- Prioritize official sources, regulators, company pages, strong local business press, recent blogs, and public market analysis.
- Do not invent evidence.
- Separate verified facts from inference.

Return these sections:

1. Executive verdict
- Is this pain point real enough to market now?
- Answer: yes, no, or partial.

2. Evidence table
- Use exactly these columns:
  claim | source_url | source_date | geo | signal_type | confidence | what_it_proves | what_it_does_not_prove | open_question
- Allowed values for signal_type:
  existence du marche
  urgence
  faisabilite
  ne prouve pas la volonte de payer

3. Competitor and substitute map
- List direct competitors, internal workflows, and "do nothing" substitutes.
- Explain whether the pain point is already well served.

4. Risk scan
- Cover platform risk, compliance risk, operational risk, and reputational risk.
- Explicitly say whether the pain point is safe to build a product around.

5. Buyer and budget signal
- Identify the likely buyer, budget line, and any public signal that money is already moving.
- Be explicit about what does NOT prove willingness to pay.

6. Desk-research sufficiency
- Is desk research enough to start outreach?
- If not, list the minimum 3-5 expert calls still required.
```
