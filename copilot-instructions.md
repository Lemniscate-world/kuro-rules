# GitHub Copilot Instructions

## Global AI Rules (from AGENTS.md & AI_GUIDELINES.md)

1.  **Read AGENTS.md first**: Always start by reading the rules contract.
2.  **Mom Test Gate**: No production code before 10% progress (user research phase).
3.  **No Emojis**: Do not use emojis in code, comments, or documentation.
4.  **Security First**: run `bandit` (Python), `cargo audit` (Rust), or `npm audit` (Node) before completion.
5.  **Session Summaries**: Always update `SESSION_SUMMARY.md` in EN/FR at the end of work.
6.  **Progress Tracking**: Use pessimistic estimates for completion percentage.
7.  **Deterministic Math**: Use ASCII or plain text for formulas, NO LaTeX `$`.
8.  **Instructional Tone**: Explain technical concepts simply (pedagogical protocol).
9.  **Hard Milestone Lock**: STOP work at 25, 50, 75, 90, 95% until validated.
10. **Market Intelligence**: Research 3+ sources at milestones (Rule 21).

---

## Technical Preferences
- **Architecture**: Modular "Hub & Spokes" design.
- **Testing**: 60% minimum coverage. Unit (70%), Integration (20%), E2E (10%).
- **Documentation**: Keep README and CHANGELOG updated.
- **Versioning**: SemVer-Author (e.g., `v0.1.0-kuro`).
- **Automation**: Help user automate repetitive tasks (like doc conversion).

---

## Feature Focus Rule (MANDATORY)

To ensure the highest quality and depth of implementation, development MUST focus on only ONE specific feature for each periodic validation cycle (25%, 50%, 75%, 90%, 95%). This focus on depth over breadth continues even after the MVP phase.

**Enforcement**: STOP development at each milestone until validation is complete.