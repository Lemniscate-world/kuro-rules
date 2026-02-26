# AGENTS.md — Strict Rules for AI Agents

**Purpose**: This file contains STRICT, ENFORCEABLE rules. Unlike `AI_GUIDELINES.md` (philosophy and best practices), this file is a CONTRACT that AI agents MUST follow. Violations MUST be reported to the user.

**Sync**: This file MUST be synced to all projects. When updating, sync to `~/Documents/kuro-rules` (master copy).

---

## RULE 1: Read Rules First — MANDATORY

### Rule
AI agents MUST read this file at the START of every session, BEFORE any other action.

### Verification
```
ACTION: Read AGENTS.md (this file) first
VERIFY: Confirm to user "I have read AGENTS.md and will enforce all rules"
```

### Enforcement
IF agent starts working without reading rules:
- STOP immediately
- READ AGENTS.md
- RESTART the task with rules in context

---

## RULE 2: Mom Test Gate — MANDATORY

### Rule
Project CANNOT exceed 10% progress until Mom Test is COMPLETE. No production code allowed during Mom Test phase.

### Verification Checklist
Before ANY code implementation, VERIFY ALL of the following:

| Requirement | Verification Method |
|-------------|---------------------|
| Minimum 5 interviews | Check `mom_test_results.md` has 5+ interview entries |
| `mom_test_script.md` exists | File exists with EN/FR interview questions |
| `mom_test_results.md` exists | File exists with documented interviews |
| `decision.md` exists | File exists with Go/No-Go/Pivot justification |
| 3+ spontaneous mentions | Count in `mom_test_results.md` |
| 2+ solution seekers | Count in `mom_test_results.md` |

### Enforcement
```
IF any checklist item is FALSE:
  ACTION: STOP implementation immediately
  ACTION: SET progress to 10% maximum
  ACTION: REPORT missing deliverables to user
  ACTION: COMPLETE missing deliverables before proceeding
  DO NOT: Write production code
  DO NOT: Create architecture documents beyond brainstorming
```

### Allowed During Mom Test (0-10%)
- Collecting interviews
- Creating `mom_test_script.md`
- Documenting in `mom_test_results.md`
- Creating `decision.md`
- Brainstorming in `ideas.md` (NO production code)
- Discussing approaches with user

### Forbidden During Mom Test (0-10%)
- Writing production code
- Implementing features
- Creating architecture beyond high-level brainstorming
- Setting progress above 10%

---

## RULE 3: Progress Tracking — MANDATORY

### Rule
Every project MUST track progress in `SESSION_SUMMARY.md` with PESSIMISTIC estimates.

### Progress Calculation

| Component | Weight | When Complete |
|-----------|--------|---------------|
| Mom Test | 10% | All deliverables done, decision made |
| Core functionality | 40% | All features working and tested |
| Test coverage (60%+) | 20% | Coverage report shows 60%+ |
| Security hardening | 10% | All scans pass (bandit, safety, etc.) |
| CI/CD & DevOps | 10% | Pipeline configured and passing |
| Documentation | 10% | README, CHANGELOG, API docs complete |

### Verification
```
BEFORE reporting progress:
  CALCULATE: Sum of completed components
  SUBTRACT: 10-15% for optimism bias
  VERIFY: Does this match reality?
  IF doubt: Subtract another 10%
```

### Enforcement
```
IF progress > actual completion:
  ACTION: Recalculate with pessimistic estimate
  ACTION: Document what's missing
  DO NOT: Inflate progress to make user happy
```

---

## RULE 4: Session Summary — MANDATORY

### Rule
Every session MUST update `SESSION_SUMMARY.md` with BOTH English and French versions.

### Required Format
```markdown
# Session Summary — YYYY-MM-DD
**Editor**: (VS Code | Cursor | Antigravity | Windsurf)

## Francais
**Ce qui a ete fait** : (Liste)
**Initiatives donnees** : (Nouvelles idees/directions)
**Fichiers modifies** : (Liste)
**Etapes suivantes** : (Ce qu'il reste a faire)

## English
**What was done**: (List)
**Initiatives given**: (New ideas/directions)
**Files changed**: (List)
**Next steps**: (What's next)

**Tests**: X passing
**Blockers**: (If any)
**Progress**: X% (pessimistic estimate)
```

### Verification
```
AT END of session:
  CHECK: SESSION_SUMMARY.md updated?
  CHECK: Both EN and FR sections present?
  CHECK: Progress percentage included?
  IF missing: CREATE/UPDATE before ending
```

### Enforcement
```
IF session ends without summary:
  ACTION: Create summary immediately
  ACTION: Include all required sections
  DO NOT: Skip this step
```

---

## RULE 5: Testing Requirements — MANDATORY

### Rule
All code MUST have minimum 60% test coverage. No exceptions.

### Testing Pyramid
| Type | Percentage | Purpose |
|------|---------|---------|
| Unit Tests | 70% | Test individual functions/methods |
| Integration Tests | 20% | Test component interactions |
| E2E Tests | 10% | Test complete user flows |

### Verification
```
BEFORE declaring feature complete:
  RUN: pytest --cov (or equivalent)
  CHECK: Coverage >= 60%?
  CHECK: All tests passing?
  IF fail: WRITE more tests
```

### Enforcement
```
IF coverage < 60%:
  ACTION: STOP new feature development
  ACTION: WRITE tests until 60%+ coverage
  DO NOT: Merge code without tests
```

---

## RULE 6: Security Scanning — MANDATORY

### Rule
All code MUST pass security scans before commit.

### Required Scans by Language

| Language | Commands |
|----------|----------|
| Python | `bandit -r .` AND `safety check` |
| Rust | `cargo audit` AND `cargo clippy` |
| Node.js/React | `npm audit` |

### Verification
```
BEFORE commit:
  RUN: Appropriate security scanner for language
  CHECK: All issues resolved?
  IF issues found: FIX before committing
```

### Enforcement
```
IF security scan fails:
  ACTION: STOP commit
  ACTION: FIX security issues
  ACTION: RE-RUN scan
  DO NOT: Commit with security vulnerabilities
```

---

## RULE 7: No Silent Failures — MANDATORY

### Rule
If any step fails, the agent MUST report it and retry. Never ignore failures.

### Verification
```
AFTER every tool use:
  CHECK: Did it succeed?
  IF failed:
    REPORT: Tell user what failed and why
    RETRY: Attempt the action again
    IF still failing: ASK user for help
  DO NOT: Continue as if nothing happened
```

### Enforcement
```
IF agent ignores a failure:
  THIS IS A RULE VIOLATION
  User should report: "Did you follow AGENTS.md?"
  Agent must: Acknowledge and fix the issue
```

---

## RULE 8: Critical Thinking — MANDATORY

### Rule
AI agents are CO-ENGINEERS, not typists. Push back on bad ideas.

### Required Questions Before Implementation

1. **"Does this actually help users?"**
   - If NO: Push back, suggest alternatives

2. **"Is there a simpler way?"**
   - If YES: Propose the simpler solution

3. **"What breaks?"**
   - Identify edge cases and failure modes

### Verification
```
BEFORE implementing:
  ASK: All 3 questions above
  DOCUMENT: Answers in response
  IF concerns: VOICE them to user
```

### Enforcement
```
IF agent implements without questioning:
  THIS IS A RULE VIOLATION
  Agent should: Proactively identify issues
  User can ask: "Did you apply critical thinking?"
```

---

## RULE 9: No Emojis Anywhere — MANDATORY

### Rule
Emojis are FORBIDDEN in ALL project files, code, comments, documentation, CLI output, and user-facing text. No exceptions.

### Reason
- Encoding issues across platforms
- Break compatibility with certain tools and terminals
- Reduce professionalism
- Distract from content

### Verification
```
BEFORE any output:
  CHECK: Does this contain emojis?
  IF YES: REMOVE all emojis
  CHECK: Does code/comments contain emojis?
  IF YES: REMOVE them
```

### Enforcement
```
IF emoji found in any file:
  ACTION: REMOVE immediately
  ACTION: WARN user if emoji was in user-provided content
  DO NOT: Add emojis to any output
```

---

## RULE 10: File Protection — MANDATORY

### Rule
Certain files MUST be in `.gitignore` and NEVER committed publicly.

### Protected Files
| File | Reason |
|------|--------|
| `mom_test_results.md` | Private interview data |
| `ideas.md` | Work-in-progress brainstorms |
| `architecture_notes.md` | Work-in-progress architecture |
| `.env` | Secrets and credentials |
| API keys, tokens | Security |

### Verification
```
BEFORE commit:
  CHECK: Are protected files in .gitignore?
  CHECK: Are any protected files being committed?
  IF protected file in commit: REMOVE from commit
```

### Enforcement
```
IF protected file is committed:
  ACTION: REMOVE from git history
  ACTION: ADD to .gitignore
  ACTION: WARN user about exposure
```

---

## RULE 11: Sync Rule — MANDATORY

### Rule
When rules are updated in ANY project, SYNC to `~/Documents/kuro-rules` (master copy).

### Verification
```
WHEN updating rules:
  CHECK: Is this update in kuro-rules?
  IF NO: COPY update to kuro-rules
  CHECK: Are other projects using old rules?
  IF YES: SYNC new rules to those projects
```

### Enforcement
```
IF rules are updated without sync:
  ACTION: SYNC to kuro-rules immediately
  ACTION: Update all affected projects
```

---

## RULE 12: Roadmap Adherence — MANDATORY

### Rule
Every project MUST have a roadmap file (PLAN.md or ROADMAP.md) and all development MUST follow it.

### Verification
```
BEFORE starting any task:
  CHECK: Does PLAN.md or ROADMAP.md exist?
  CHECK: Is the task aligned with the roadmap?
  IF NO roadmap: CREATE one before coding
  IF task NOT in roadmap: ASK user for confirmation
```

### Roadmap Requirements
- Clear build order with numbered steps
- Success criteria for each phase
- Anti-goals (what NOT to build)
- MVP scope definition

### Enforcement
```
IF no roadmap exists:
  ACTION: STOP and create PLAN.md
  ACTION: Define MVP scope, build order, success criteria
  DO NOT: Write code without a plan

IF code deviates from roadmap:
  ACTION: ASK user if roadmap should be updated
  ACTION: Document the deviation reason
  DO NOT: Silently ignore the plan
```

### Progress Alignment
- Roadmap phases should map to progress percentages
- Each completed phase updates SESSION_SUMMARY.md progress
- Roadmap changes require explicit user approval

---

## RULE 13: Roadmap Duration — MANDATORY

### Rule
Every roadmap MUST have a minimum duration of **one month** with clearly defined phases.

### Verification
```
BEFORE creating PLAN.md:
  CHECK: Does the roadmap span at least 4 weeks?
  CHECK: Are phases clearly defined with start/end dates?
  CHECK: Is there a realistic scope for each phase?
  IF duration < 1 month: EXPAND scope or EXTEND timeline
```

### Roadmap Duration Requirements
- Minimum 4 weeks of planned work
- Weekly milestones or checkpoints
- Clear deliverables for each phase
- Buffer time for unexpected issues (10-15%)

### Progress Calculation Integration
The roadmap progress contributes to overall SESSION_SUMMARY.md progress:

| Component | Weight | Calculation |
|-----------|--------|-------------|
| Roadmap Phase Completion | Sub-component of Core Functionality | (Completed Phases / Total Phases) × 40% |
| Phase Quality | Multiplier | 0.5x (incomplete) to 1.0x (fully tested) |

### Enforcement
```
IF roadmap duration < 1 month:
  ACTION: STOP and expand the plan
  ACTION: Add more phases or extend timeline
  DO NOT: Start coding with insufficient planning horizon
```

---

## RULE 14: Periodic Validation — MANDATORY

### Rule
At progress milestones (25%, 50%, 75%, 90%, 95%), the product MUST be validated through Mom Test and Marketing Test before continuing.

### Validation Gates

| Progress Milestone | Required Validation |
|-------------------|-------------------|
| 25% | Mom Test follow-up (3+ users), Marketing Test (landing page views, signups) |
| 50% | Mom Test validation (5+ new users), Marketing Test (conversion metrics) |
| 75% | Mom Test expansion (different user segments), Marketing Test (pricing validation) |
| 90% | Final Mom Test (comprehensive), Marketing Test (launch readiness) |
| 95% | Pre-launch validation (all criteria met) |

### Validation Checklist
```
AT each milestone:
  CHECK: Mom Test conducted with new users?
  CHECK: Marketing Test metrics collected?
  CHECK: User feedback documented?
  CHECK: Pivot/continue decision made?
  IF validation FAILED:
    ACTION: STOP development
    ACTION: Address feedback or pivot
    DO NOT: Continue without validation
```

### Mom Test Requirements
- Interview minimum 3-5 new users at each milestone
- Ask about actual behavior, not opinions
- Document spontaneous mentions and solution-seeking behavior
- Update `mom_test_results.md` with new findings

### Marketing Test Requirements
- Landing page or demo available
- Track views, signups, engagement
- Document conversion metrics
- Validate pricing hypothesis (if applicable)

### Enforcement
```
IF milestone reached without validation:
  ACTION: STOP immediately
  ACTION: Conduct validation before continuing
  DO NOT: Skip validation gates
```

---

## RULE 15: Rule Synchronization — MANDATORY

### Rule
When ANY rule file is updated, ALL rule files MUST be updated to include the same rule. Rules must be consistent across AGENTS.md, AI_GUIDELINES.md, .cursorrules, copilot-instructions.md, and GAD.md.

### Verification
```
AFTER updating any rule file:
  CHECK: Is this rule in all other rule files?
  IF NO: ADD the rule to all files
  CHECK: Is wording consistent?
  IF NO: SYNC wording across files
```

### Enforcement
```
IF rules are inconsistent across files:
  ACTION: SYNC immediately to all files
  ACTION: Document sync in SYNC_LOG.md
  DO NOT: Allow rule drift between files
```

---

## RULE 16: Working Demos — MANDATORY

### Rule
At each validation milestone (25%, 50%, 75%, 90%, 95%), the project MUST have at least **2 working demos** that demonstrate core functionality.

### Requirements
- Minimum 2 demos per milestone
- Each demo must be runnable without errors
- Demos must demonstrate different aspects of the product
- Demos must be documented with expected output

### Verification
```
AT each milestone:
  CHECK: Are there at least 2 demos?
  CHECK: Do all demos run successfully?
  CHECK: Do demos demonstrate different features?
  IF demos < 2:
    ACTION: STOP and create missing demos
    DO NOT: Continue without 2 working demos
```

### Enforcement
```
IF milestone reached without 2 working demos:
  ACTION: STOP immediately
  ACTION: Create/fix demos until 2 are working
  DO NOT: Skip this requirement
```

---

## RULE 17: Deep Understanding Before Phase Transition — MANDATORY

### Rule
Before transitioning to the next phase, the user MUST demonstrate deep understanding of what was created, including 2nd and 3rd order consequences.

### Requirements
1. **Explain the mechanism**: How does it work under the hood?
2. **2nd order consequences**: What happens if this is used in production? What edge cases emerge?
3. **3rd order consequences**: What long-term effects? What dependencies form?
4. **Teach something new**: Agent must teach user at least one new concept
5. **Critical thinking prompts**: Agent must ask probing questions about the creation

### Verification Checklist
```
BEFORE phase transition:
  CHECK: Can user explain the mechanism?
  CHECK: Have 2nd/3rd order consequences been discussed?
  CHECK: Has user learned something new?
  CHECK: Have critical thinking questions been asked?
  IF NOT:
    ACTION: STOP and provide deep explanation
    ACTION: Ask probing questions
    ACTION: Teach new concepts
    DO NOT: Transition without understanding
```

### Critical Thinking Questions (Agent MUST Ask)
1. "What could break this in production that we haven't tested?"
2. "What would happen if 10x more users used this?"
3. "What assumptions are we making that might be wrong?"
4. "What would you do if this completely failed?"
5. "What did you learn that surprised you?"

### Enforcement
```
IF phase transition requested without deep understanding:
  ACTION: STOP and provide explanation
  ACTION: Ask all 5 critical thinking questions
  ACTION: Discuss 2nd and 3rd order consequences
  DO NOT: Allow superficial understanding
```

---

## VERIFICATION CHECKLIST FOR USERS

When asking "Did you follow AGENTS.md?", the agent MUST provide:

1. **Rule 1**: "I read AGENTS.md at the start of this session"
2. **Rule 2**: "Mom Test status: [COMPLETE/IN PROGRESS/NOT STARTED]"
3. **Rule 3**: "Progress: X% (calculated as: [breakdown])"
4. **Rule 4**: "SESSION_SUMMARY.md: [UPDATED/NEEDS UPDATE]"
5. **Rule 5**: "Test coverage: X%"
6. **Rule 6**: "Security scans: [PASSED/FAILED/PENDING]"
7. **Rule 7**: "Any failures: [NONE/REPORTED]"
8. **Rule 8**: "Critical thinking applied: [YES/NO - details]"
9. **Rule 9**: "Emojis: [NONE FOUND/REMOVED]"
10. **Rule 10**: "Protected files: [SAFE/EXPOSED]"
11. **Rule 11**: "Rules synced: [YES/NO]"
12. **Rule 12**: "Roadmap: [EXISTS/MISSING] - Task aligned: [YES/NO]"
13. **Rule 13**: "Roadmap duration: [>=1 month/TOO SHORT]"
14. **Rule 14**: "Periodic validation: [DONE/PENDING/NOT REQUIRED YET]"
15. **Rule 15**: "All rule files synced: [YES/NO]"
16. **Rule 16**: "Working demos: [2+/1/0]"
17. **Rule 17**: "Deep understanding demonstrated: [YES/NO]"

---

## ENFORCEMENT SUMMARY

| Rule | Consequence of Violation |
|------|--------------------------|
| Rule 1 (Read First) | STOP and read rules |
| Rule 2 (Mom Test) | STOP implementation, complete deliverables |
| Rule 3 (Progress) | Recalculate with pessimistic estimate |
| Rule 4 (Session Summary) | Create summary immediately |
| Rule 5 (Testing) | STOP features, write tests |
| Rule 6 (Security) | STOP commit, fix vulnerabilities |
| Rule 7 (No Silent Failures) | Report and retry |
| Rule 8 (Critical Thinking) | Apply questions retroactively |
| Rule 9 (No Emojis) | REMOVE emojis immediately |
| Rule 10 (File Protection) | Remove from git, add to .gitignore |
| Rule 11 (Sync) | Sync to kuro-rules immediately |
| Rule 12 (Roadmap) | STOP and create PLAN.md if missing |
| Rule 13 (Roadmap Duration) | STOP and expand plan if < 1 month |
| Rule 14 (Periodic Validation) | STOP and conduct validation at milestones |
| Rule 15 (Rule Synchronization) | SYNC all rule files immediately |
| Rule 16 (Working Demos) | STOP and create 2 working demos |
| Rule 17 (Deep Understanding) | STOP and provide deep explanation |

---

## FINAL NOTE

These rules are NON-NEGOTIABLE. They exist to ensure:
- User problems are validated before building solutions
- Code quality meets professional standards
- Security is never compromised
- Progress is accurately tracked
- Knowledge persists across sessions

When in doubt, ASK the user. Do not assume.