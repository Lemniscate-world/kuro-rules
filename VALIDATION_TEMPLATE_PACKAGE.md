# Validation Automation Template Package (R84)

## Overview

Template files for implementing automated validation pipelines across all lambda-Section projects.
Based on Hermes implementation (R84 compliant).

## Files to Copy to New Projects

### Required Structure
```
project/
├── .windsurf/
│   └── workflows/
│       └── validation-automation.md     # Workflow skill
├── landing/
│   ├── index.html                       # Presentation page
│   ├── formulaire-supabase.html         # Form with Supabase POST
│   ├── dashboard.html                   # Real-time stats
│   └── config.js                        # Configuration (gitignored)
├── scripts/
│   └── analyze_responses.py             # Analytics + CSV export
├── supabase-schema.sql                  # PostgreSQL schema
└── AUTOMATION_SETUP.md                  # Documentation
```

## Synchronization Status

### Synchronized to 35 repos (AGENTS.md)
- ✅ R83: Discord investor summary
- ✅ R84: Validation automation mandate
- ✅ MCP Supabase reference

### NOT Automatically Synced (Project-Specific)
These files are templates in `kuro-rules/templates/validation/`:
- `formulaire-supabase.html`
- `dashboard.html`
- `analyze_responses.py`
- `supabase-schema.sql`
- `validation-automation.md` (workflow)

## Usage for New Projects

### Option 1: Copy from Hermes
```bash
cd ~/Documents/YourNewProject
mkdir -p landing scripts .windsurf/workflows

cp ~/Documents/Hermes/landing/formulaire-supabase.html landing/
cp ~/Documents/Hermes/landing/dashboard.html landing/
cp ~/Documents/Hermes/scripts/analyze_responses.py scripts/
cp ~/Documents/Hermes/supabase-schema.sql .
cp ~/Documents/Hermes/.windsurf/workflows/validation-automation.md .windsurf/workflows/
cp ~/Documents/Hermes/AUTOMATION_SETUP.md .
```

### Option 2: Manual Setup
Follow `AUTOMATION_SETUP.md` in any project after copying template files.

## Customization Required

### Per Project
1. **Branding**: Update colors, logo, project name in HTML files
2. **Questions**: Adapt form fields to project context
3. **Schema**: Modify `supabase-schema.sql` for different data needs
4. **Analytics**: Update `analyze_responses.py` metrics

### Example Adaptations

#### For AI/ML Projects (NeuralDbg, Dissect)
- Form: Focus on "pain points in debugging/visualization"
- Dashboard: Track "willingness to pay for AI tools"

#### For Fintech (G&S Solutions, Iroko, Kapok)
- Form: Focus on "compliance pain points"
- Dashboard: Track "regulatory concerns"

#### For Consumer Apps (Charmed, Echo)
- Form: Focus on "daily usage patterns"
- Dashboard: Track "feature prioritization"

## Cost Estimate

All projects use Supabase free tier:
- 500MB storage per project
- 75K connections/day
- Sufficient for 10,000+ validation responses

## Verification Checklist (R84)

Before declaring validation ready:
- [ ] Supabase project created
- [ ] Schema deployed with RLS
- [ ] Form submits successfully
- [ ] Dashboard shows real-time data
- [ ] Python analytics script works
- [ ] No manual CSV exports needed
- [ ] R83 investor summary generated

## Projects Needing Validation Pipeline

### High Priority (Active/Validation phase)
1. **Hermes** 10% - ✅ DONE (reference implementation)
2. **DataLint** 5% - Needs validation setup
3. **Charmed** 50% - Could benefit from feedback collection
4. **Echo** 5% - Needs user validation

### Medium Priority (Prototyping)
5. **NeuroDose** 0% - Nootropics tracking validation
6. **Thanatos** 0% - Fitness app validation
7. **Metatron** 0% - Debugger validation
8. **Aquarium** 3% - IDE validation

### Future (When reaching validation phase)
9. G&S Solutions, Iroko, Kapok - Fintech validation
10. All 0% projects when they reach validation phase

## Next Steps

1. **Q2 2026**: Deploy validation pipelines for DataLint, Charmed, Echo
2. **Create template repository**: Make `lambda-validation-template` repo with all files
3. **Document in AGENTS.md**: Add R85 for "validation pipeline template usage"

---

**Master copy**: ~/Documents/kuro-rules/VALIDATION_TEMPLATE_PACKAGE.md
**Reference implementation**: ~/Documents/Hermes/
**Rule**: R84 (AGENTS.md)
