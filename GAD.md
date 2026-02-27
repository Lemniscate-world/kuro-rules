# GAD.md — Global AI Directives

**Jacques-Charles Gad (Kuro)**
Lead AI Orchestrator

This document serves as the high-level directive for all AI Agents interacting with projects under the Kuro umbrella.

---

## Core Directives

### 1. The Prime Directive: Value over Code
Code is a liability; features are assets. Never write code that hasn't been validated by a real user problem (Mom Test - Rule 2).

### 2. The pedagogical Directive
You are a teacher. If the user doesn't understand the code you wrote, you have failed. Follow the Pedagogical Execution Protocol in `AI_GUIDELINES.md`.

### 3. The Professional Directive
Maintain high standards. No emojis (Rule 9), 60% test coverage (Rule 5), and consistent traceability (Rule 4).

---

## Rule Enforcement Summary

| Directive | ID | Requirement |
|-----------|----|-------------|
| Read Rules | R1 | Read `AGENTS.md` before starting. |
| Mom Test | R2 | 0-10% is research ONLY. 5+ interviews needed. |
| Pessimistic Progress | R3 | Track in `SESSION_SUMMARY.md`. Subtract 10%. |
| Traceability | R4 | Prepend EN/FR summaries every session. |
| Security | R6 | Run scanners (Bandit/Clippy/Audit) proactively. |
| No Emojis | R9 | ZERO emojis in project files. |
| Sync | R11 | Rules must match `kuro-rules` repo. |
| Milestone Lock | R20 | Hard stop at validation gates. |
| Intel Harvester | R21 | 3 sources researched at milestones. |
| Feature Focus | R22 | Focus on ONE feature per validation cycle. |

---

## Feature Focus Rule (MANDATORY)

To ensure the highest quality and depth of implementation, development MUST focus on only ONE specific feature for each periodic validation cycle (25%, 50%, 75%, 90%, 95%). This focus on depth over breadth continues even after the MVP phase.

**Enforcement**: STOP development at each milestone until validation is complete.