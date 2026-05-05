# Source Quality Checklist

**Purpose**: Evaluate the quality and reliability of sources for Desk Research  
**Version**: 1.0  
**Date**: 2026-04-05

---

## Quick Evaluation Matrix

### Tier 1 - High Confidence (Always Prioritize)

| Source Type | Minimum Criteria | Examples |
|-------------|------------------|----------|
| **GitHub Issues** | +10 upvotes, recent, team response | Cursor indexing issues, Nx discussions |
| **Reddit Threads** | +50 votes, 20+ comments, recent | r/ExperiencedDevs, r/webdev |
| **Official Forums** | Verified staff response, pinned | forum.cursor.com, nx.dev/community |
| **Published Studies** | Citable, methodology clear | McKinsey, Stack Overflow Survey |
| **Company Reports** | Recognized entity, data-driven | Gartner, Forrester, company engineering blogs |

**Score**: 10/10 reliability  
**Usage**: Primary evidence, can drive verdict

---

### Tier 2 - Medium Confidence (Verify Before Using)

| Source Type | Verification Steps | Examples |
|-------------|-------------------|----------|
| **Tech Blogs** | Check author credentials, date, citations | Personal blogs of known engineers |
| **Twitter/X** | Verify account (blue check, company affiliation), engagement | @seniordev at @company |
| **LinkedIn** | Professional profile, company, post engagement | Posts by tech leads |
| **Discord/Slack** | Check community size, message history | Nx Discord, Reactiflux |
| **YouTube/Podcasts** | Transcripts available, speaker credentials | Tech talks, podcast interviews |

**Score**: 6-8/10 reliability  
**Usage**: Supporting evidence, needs cross-verification

---

### Tier 3 - Low Confidence (Avoid or Contextualize)

| Source Type | Why Low Confidence | How to Use If Necessary |
|-------------|-------------------|------------------------|
| **Marketing Articles** | Biased, no methodology | Flag as "vendor perspective" |
| **Anonymous Posts** | No accountability | Note "unverified source" |
| **Old Sources (2020-2023)** | Market may have changed | Contextualize with date |
| **Low Engagement** | <5 votes, <3 comments | "Single anecdote, not pattern" |
| **"I heard that..."** | Second-hand information | Exclude unless corroborated |

**Score**: 2-4/10 reliability  
**Usage**: Context only, never primary evidence

---

## Detailed Evaluation Criteria

### For Each Source, Check:

#### 1. Recency

- [ ] **Excellent**: 2025-2026 (within 12 months)
- [ ] **Good**: 2024 (if structural/official source)
- [ ] **Acceptable**: 2023 (only if no recent equivalent)
- [ ] **Poor**: 2022 or earlier (likely outdated)

**Rule**: Prioritize sources from 2025-2026. Use older sources only if they provide structural context.

---

#### 2. Engagement

- [ ] **High**: 100+ votes, 50+ comments, multiple threads
- [ ] **Medium**: 20-99 votes, 10-49 comments
- [ ] **Low**: <20 votes, <10 comments
- [ ] **Minimal**: Single post, no engagement

**Rule**: High engagement = many people share this pain. Low engagement = niche or weak problem.

---

#### 3. Specificity

- [ ] **High**: Exact numbers, dates, tool names, versions
  - Example: "Cursor 0.42, monorepo with 144k files, 8GB RAM, crashes every 90s"
- [ ] **Medium**: Specific scenario but no numbers
  - Example: "Large monorepo, Cursor freezes frequently"
- [ ] **Low**: Vague complaints
  - Example: "Monorepos are hard"

**Rule**: High specificity = real operational pain. Low specificity = generic opinion.

---

#### 4. Author Credibility

- [ ] **Verified**: Real name, company affiliation, professional profile
- [ ] **Semi-verified**: Consistent handle, post history, community recognition
- [ ] **Anonymous**: No identifying information
- [ ] **Suspicious**: New account, single post, no history

**Rule**: Verified authors = higher reliability. Anonymous = lower weight.

---

#### 5. Corroboration

- [ ] **Multiple**: Same pain mentioned by 3+ independent sources
- [ ] **Some**: 2 sources mention similar issue
- [ ] **Single**: Only 1 source mentions this
- [ ] **Contradictory**: Other sources say opposite

**Rule**: Corroborated pain = validated problem. Single source = possible outlier.

---

## Red Flags (Exclude or Flag)

| Red Flag | Why It Matters | Action |
|----------|---------------|--------|
| **No date** | Can't verify recency | Exclude |
| **No URL** | Can't verify existence | Exclude |
| **Marketing content** | Biased by definition | Flag as "vendor" |
| **Vague complaints** | No operational proof | Lower weight |
| **Outliers** | Single user, extreme case | Note "outlier, not pattern" |
| **Conflicts of interest** | Author works for competitor | Flag bias |
| **Old data in new context** | Market evolved | Contextualize or exclude |

---

## Source Scoring System

### Calculate Score (0-10)

**Base Score**: Start at 5

**Add for positives**:
- Tier 1 source: +2
- 2025-2026 date: +1
- High engagement (100+): +1
- High specificity (numbers/details): +1
- Verified author: +1
- Corroborated (3+ sources): +1

**Subtract for negatives**:
- Tier 3 source: -2
- 2022 or earlier: -1
- Low engagement (<20): -1
- Low specificity (vague): -1
- Anonymous author: -1
- Single source (no corroboration): -1
- Red flag present: -2

### Score Interpretation

| Score | Quality | Usage |
|-------|---------|-------|
| 9-10 | Excellent | Primary evidence |
| 7-8 | Good | Strong supporting evidence |
| 5-6 | Acceptable | Context only, needs more |
| 3-4 | Weak | Exclude or flag heavily |
| 0-2 | Unreliable | Exclude |

---

## Quick Checklist Per Source

For every source you collect:

- [ ] **Tier assigned**: 1, 2, or 3
- [ ] **Date verified**: 2025-2026 preferred
- [ ] **URL accessible**: Tested and works
- [ ] **Engagement noted**: Vote/comment count
- [ ] **Specificity checked**: Numbers/names mentioned?
- [ ] **Author verified**: Real person/company?
- [ ] **Quote exact**: Not paraphrased
- [ ] **Context captured**: Background information
- [ ] **Score calculated**: 0-10
- [ ] **Decision**: Include / Exclude / Flag

---

## Examples

### Example 1: Excellent Source (Score: 10)

**Source**: Cursor Forum - "Codebase indexing causing cursor to freeze up repeatedly?"  
**Tier**: 1  
**Date**: 2025-03-15  
**Engagement**: 150+ replies, official response from Cursor team  
**Specificity**: "Every time index resyncs, cursor becomes unresponsive. 100GB monorepo."  
**Author**: Verified user with history  
**Corroboration**: 5+ similar threads  
**URL**: https://forum.cursor.com/t/...

**Decision**: ✅ INCLUDE as primary evidence

---

### Example 2: Weak Source (Score: 3)

**Source**: Random blog post  
**Tier**: 2 (could be 3)  
**Date**: 2023-08-01  
**Engagement**: No comments, unknown traffic  
**Specificity**: "Monorepos are complicated" (no details)  
**Author**: Anonymous blogger  
**Corroboration**: None  
**URL**: https://randomblog.com/...

**Decision**: ❌ EXCLUDE or use as context only

---

### Example 3: Good with Caveats (Score: 7)

**Source**: Twitter thread  
**Tier**: 2  
**Date**: 2025-01-20  
**Engagement**: 200 likes, 30 retweets  
**Specificity**: "Our 50k file Nx monorepo takes 45 min to build. We built a custom cache."  
**Author**: Tech lead at known startup (verified)  
**Corroboration**: 2 similar mentions  
**URL**: https://twitter.com/.../status/...

**Decision**: ✅ INCLUDE with note "needs more corroboration"

---

## Usage in Validation

### For GO Verdict:

- Minimum 5 sources scoring 8+
- At least 3 Tier 1 sources
- No critical red flags

### For NO-GO Verdict:

- Majority of sources score <5
- High contradiction between sources
- Mostly Tier 3 sources

### For ADJUST Verdict:

- Mixed scores (some good, some weak)
- Partial corroboration
- Need specific aspect validated

---

## Documentation

**Always record in `validation_evidence.md`**:

```markdown
### Source Quality Assessment

| Source | Tier | Score | Date | Engagement | Specificity | Author | Decision |
|--------|------|-------|------|------------|-------------|--------|----------|
| Cursor forum | 1 | 10 | 2025-03 | High | High | Verified | Include |
| Reddit thread | 1 | 9 | 2025-02 | High | Medium | Verified | Include |
| Twitter | 2 | 7 | 2025-01 | Medium | High | Verified | Include |
```

---

## Summary

**Golden Rule**: Quality > Quantity. 5 excellent sources > 20 weak sources.

**Always prioritize**:
1. Recent (2025-2026)
2. High engagement
3. Specific details
4. Verified authors
5. Corroborated patterns

**Always exclude**:
1. Unverifiable claims
2. Marketing content without data
3. Anonymous complaints without engagement
4. Outdated sources (2022 or earlier, unless structural)

