---
description: Standard validation pipeline for any startup project
---

# Validation Automation Workflow

## Trigger
Any project classified as `startup` requiring field validation before build.

## Steps

### 1. Create Supabase Project
// turbo
Use Playwright MCP to navigate to https://supabase.com and create a free project.
Extract the Project URL and Anon Key.

### 2. Configure Database
Run the SQL from `supabase-schema.sql` in Supabase SQL Editor.
Verify RLS policies are active.

### 3. Configure Landing
Update `landing/config.js` with Supabase URL + Key.
Verify `formulaire-supabase.html` and `dashboard.html` exist.

### 4. Test Submission
// turbo
Use Playwright MCP to:
1. Open the deployed landing page
2. Fill and submit the form with test data
3. Verify the response appears in Supabase
4. Verify the dashboard updates

### 5. Generate Analytics
Run `python scripts/analyze_responses.py` to verify the pipeline works end-to-end.

### 6. Document
Update `SESSION_SUMMARY.md` with investor summary (R83).
Update `Epingle_Projets.md` (R80).

## Verification Checklist
- [ ] Supabase project created
- [ ] Table `landing_responses` exists with RLS
- [ ] Form submission works from mobile
- [ ] Dashboard shows real-time stats
- [ ] Python script connects and exports CSV
- [ ] R83 summary generated

## Failure Mode
If any step fails, do NOT proceed to distribution. Fix the pipeline first.
