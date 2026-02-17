# Kuro Rules — AI Guidelines

Shared AI rules for all projects. **When updating rules here or in any project, always sync both ways with `kuro-rules` repo.**

## Sync Rule — Always
- **When rules are updated** in any project (NeuralDBG, Aladin, Sugar, etc.), **sync those updates to `~/Documents/kuro-rules`**.
- kuro-rules is the master copy for shared rules. Keep it updated.
- Run `install.sh` on projects to (re)link after updating kuro-rules.

## Explain as if First Time — Always
- Assume **zero prior knowledge**. Re-explain AI, ML, concepts, math as if the user knows nothing.
- The user codes while learning for the first time. Define terms, use simple analogies, break down formulas.
- Never skip explanations. "Obvious" is not obvious to someone learning.

---

## Sugar AI Guidelines (Project-Specific)

This section contains Sugar-specific rules.

## For Developers
If you are using an AI coding assistant (Cursor, Windsurf, Copilot, Antigravity, etc.), please ensure it is aware of the context rules:
- **Cursor/Windsurf**: `.cursorrules` (in root)
- **GitHub Copilot**: `.github/copilot-instructions.md`

## Core Principles

### 1. Local-First Philosophy
Sugar runs **entirely on your machine**. No paid APIs required.
- LLM inference via **Ollama** (local models)
- Conversation memory in **SQLite** (local database)
- Obsidian vault is **local markdown files**
- Only external calls: Linear API, Telegram Bot API, web search (all optional)

### 2. Connector Architecture
Sugar is a **hub with spokes**:
- **Core**: LLM engine + memory + tool router
- **Connectors**: Pluggable adapters for external tools (Linear, Obsidian, web, etc.)
- **Interfaces**: Chat frontends (CLI, Telegram, GUI)
- Adding a new tool = adding a new connector. No core changes needed.

### 3. Design Principles
- **SRP**: Single Responsibility. No "God Classes".
- **DRY**: Shared logic belongs in utilities, not duplicated.
- **KISS**: Simple is better than complex.
- **YAGNI**: Don't overengineer for hypothetical futures.
- **SOLID**: Follow the 5 commandments of OOD.
- **Duck Typing**: Embrace Python's dynamic nature.
- **Clean Code**: Readable names, small functions, no side effects.
- **Agile**: Ship > Argue. Code wins arguments.

### 4. Security — **Security First**: Always ensure the project is secure. Run `bandit` and `safety` checks. Never log secrets. Validate all user input. Protect against path traversal.
- **Pre-commit Mandate**: Every project MUST have pre-commit hooks installed and configured to match the shared standards.
- **Always** validate and sanitize user input.
- **Always** protect against path traversal (no accessing files outside allowed directories).
- **Always** use parameterized queries for database operations.
- **Always** run `bandit` security scanner before committing.
- **Always** check dependencies for known vulnerabilities.
- **Pre-commit hooks** must include `detect-private-key` and `bandit`.
- **Environment variables** for all secrets — never hardcode.

### 5. Tooling
- **Pre-commit**: Ruff, Mypy, Bandit (MANDATORY).
- **Testing**: Pytest with mocked external APIs.
- **Security**: Bandit + detect-private-key in pre-commit.

## Adding Connectors

### Adding a New Connector
1. **Subclass `BaseConnector`** in `sugar/connectors/`.
2. **Define actions**: What can this connector do? (read, write, search, etc.)
3. **Implement `execute()`**: Handle each action.
4. **Register**: Add to the connector registry in `engine.py`.
5. **Test**: Write tests with mocked API responses.

## Critical Thinking — "Devil's Advocate" Mode
AI assistants working on this project MUST NOT be passive executors. You are a **co-engineer**, not a typist.

**Before writing any code, always ask yourself:**
- **"Does this actually help users?"** — If a feature doesn't solve a real problem, push back.
- **"Is there a simpler way?"** — Challenge over-engineering.
- **"What breaks?"** — Proactively identify edge cases and failure modes.
- **"Is this secure?"** — Check for injection, traversal, leaks. Always.
- **"Does this already exist?"** — Before building, check if something already solves the problem.

**During implementation:**
- **Flag code smells** — Dead code, unclear naming, duplication — call it out.
- **Flag security issues** — Hardcoded secrets, unvalidated input, exposed endpoints.
- **Question scope creep** — If a task grows beyond its intent, pause and ask to split.
- **Challenge assumptions** — If the human says "we need X", ask "why not Y?" if Y is better.

**After implementation:**
- **Review your own work** — Re-read the diff before declaring done.
- **Run security checks** — `bandit -r sugar/ -ll` before finishing.
- **Suggest improvements** — "This works, but here's how it could be better: ..."
- **Identify technical debt** — If you cut corners, document it explicitly.

> **Every interaction should leave the codebase better, safer, and more secure than we found it.**

## Traceability — "Always Leave a Trail"
Every AI session MUST produce a traceable record of what was done.

**Commit discipline:**
- **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `style:`, `test:`, `docs:`, `chore:`.
- **Scope tag**: `feat(linear): add issue creation connector`.
- **Atomic commits**: One logical change per commit.

**Session summary (MANDATORY at end of every session):**
```
## Session Summary — [DATE]
**What was done:** (bullet list of changes)
**Files changed:** (list)
**Tests:** X passing
**Security:** bandit clean / issues found
**Next steps:** (what remains)
**Blockers:** (if any)
```

## Protocol
- **Step-by-Step**: Stick to the plan.
- **Phase Gate**: Verify Phase N completion before N+1.
- **Context Persistence**: Always update and maintain artifacts.
- **Git Tracking**: Commit artifacts regularly.
- **Pre-commit**: MUST be installed and passing before any PR or merge.

## 6. Agent Protocol
To ensure strict adherence to rules:
1.  **Read This First**: Agents MUST read this file at the start of every session.
2.  **Checklist Enforcement**: Agents MUST verify `task.md` and run `bandit` before declaring a task complete.
3.  **Explicit Confirmation**: When users ask "did you follow the rules?", Agents MUST provide proof (e.g., bandit output).
4.  **No Silent Failures**: If a step fails (e.g., artifact update), the Agent MUST report it and retry, never ignore it.
