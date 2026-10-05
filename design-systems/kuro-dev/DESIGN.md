# Design System Kuro Dev

> Category: Devtool / audience dev
> R109.1 choice: GitHub Primer + mono dense. Reason: dense functional UI for developers (docs, CLI, dashboards techniques). Deliberately distinct from Stripe fintech luxury and Linear dark marketing.

## 1. Visual Theme & Atmosphere

Kuro Dev is a working tool, not a showcase. Light canvas `#ffffff`, subtle surface `#f6f8fa`, visible functional borders `#d0d7de`. No hero marketing, no dark immersion, no violet atmosphere. Information density first: 14px base text, 12px metadata, tabular numerals for every number, monospace for code/IDs/paths.

The typeface is the system stack itself (`-apple-system, Segoe UI, Noto Sans, Helvetica, Arial`), not a brand display font. There is no whisper-weight headline, no geometric OpenType set, no aggressive negative tracking. Tracking is `0`: tool text must never compress. Weight 400 reads, 500 emphasizes, 600 announces. Nothing above 600.

The only chromatic color is Primer blue `#0969da` (links, primary buttons, focus, selected states). Success `#1a7f37`, warning `#9a6700`, danger `#d1242c` appear only as status, never as decoration. Elevation is Primer's neutral layered shadow, never Stripe's blue-tinted glow, never Linear's white-border luminance trick.

**Key Characteristics:**
- Light functional canvas: `#ffffff` page, `#f6f8fa` raised, `#eaeef2` inset/warm
- System font stack everywhere, monospace for code/data, `tnum` on numbers
- Base 14px (not 16px), metadata 12px, display ceiling 40px (not 56/72px)
- Primer blue `#0969da` only for action/focus/selection, capped at 2 visible uses per screen
- Borders always visible: `#d0d7de` default, `#eaeef2` muted
- Radius 6px functional, 12px panels only, pill 9999px reserved for status counts
- Primer neutral shadow: `0 1px 2px rgba(31,35,40,0.06), 0 8px 24px rgba(66,74,83,0.12)`

## 2. Color Palette & Roles

### Surfaces
- **Background** (`#ffffff`): page canvas.
- **Surface** (`#f6f8fa`): cards, panels, table headers, code blocks background tint.
- **Surface Warm** (`#eaeef2`): inset wells, drop zones, hover wash on rows.

### Text
- **Foreground** (`#1f2328`): headings, body, strong labels. Never pure black.
- **Foreground 2** (`#59636e`): secondary text, descriptions. Primer muted.
- **Muted** (`#656c76`): placeholders, captions. Must still pass 4.5:1 on white (checked in CI per pair).
- **Meta** aliases `--muted`: no fourth tier in this tool (timestamps use muted at 12px).

### Borders
- **Border** (`#d0d7de`): cards, inputs, tables, dividers. Always 1px solid, always visible.
- **Border Soft** (`#eaeef2`): row separators, nested dividers.

### Accent
- **Accent** (`#0969da`): primary buttons, links, checkboxes/radios checked, focus ring base, selected nav.
- **Accent On** (`#ffffff`): text on accent.
- **Accent Hover** (`#0550ae`): hover/pressed on primary.
- **Accent Active** (`#0550ae`): active/selected state.

### Status (never decorative)
- **Success** (`#1a7f37`): merged, passing, open-issue counts on green.
- **Warning** (`#9a6700`): draft, attention, flaky.
- **Danger** (`#d1242c`): failing, destructive, closed-alert.

## 3. Typography Rules

### Font Family
- **Primary**: `-apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif`
- **Monospace**: `ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace`
- **Numerals**: `font-variant-numeric: tabular-nums` on all data, counts, timestamps.

### Hierarchy

| Role | Size | Weight | Line Height | Tracking | Notes |
|------|------|--------|-------------|----------|-------|
| Display | 40px (2.50rem) | 600 | 1.25 | 0 | Rare: empty-state titles only, never marketing hero |
| Heading 1 | 32px (2.00rem) | 600 | 1.25 | 0 | Page titles |
| Heading 2 | 24px (1.50rem) | 600 | 1.25 | 0 | Section titles |
| Heading 3 | 20px (1.25rem) | 600 | 1.50 | 0 | Panel titles |
| Body Large | 16px (1.00rem) | 400 | 1.50 | 0 | Long-form docs only |
| Body | 14px (0.88rem) | 400 | 1.50 | 0 | Default UI text |
| Body Medium | 14px | 500 | 1.50 | 0 | Emphasis, nav labels |
| Small | 12px (0.75rem) | 400 | 1.67 | 0 | Metadata, help text |
| Small Medium | 12px | 500 | 1.67 | 0 | Counts, labels |
| Code | 12px mono | 400 | 1.67 | 0 | Code blocks, paths, IDs |
| Caption Tabular | 12px | 400 | 1.67 | 0 + tnum | Timestamps, numbers |

### Principles
- **14px is the default**, not 16px. Density is the feature.
- **Tracking is always 0.** No `-1.4px` Stripe compression, no `-1.584px` Linear engineering. Tool text must stay scannable.
- **600 is the ceiling.** No 700 bold, no 300 whisper-light.
- **Mono for machine text**: hashes, paths, commands, IDs, diffs. Never proportional font for code.
- **`tnum` for human numbers**: issue counts, timestamps, table cells.

## 4. Component Stylings

### Buttons
**Primary**
- Background: `#0969da`, text `#ffffff`, 6px radius, padding 5px 16px, font 14px/500
- Hover: `#0550ae`. Focus: Primer ring (see §6). Disabled: `#eaeef2` bg, `#656c76` text.
- Use: one primary per view ("Run", "Create", "Merge").

**Default / Secondary**
- Background: `#f6f8fa`, text `#1f2328`, `1px solid #d0d7de`, 6px radius, 5px 16px
- Hover: `#eaeef2` bg. Use: secondary actions,Cancel/Back.

**Danger**
- Background: `#d1242c` (or default button + `#d1242c` text for non-destructive-danger), 6px radius.
- Use: destructive confirmations only, always behind a confirm step.

**Icon Button**
- Background: transparent, text `#59636e`, 6px radius, `1px solid transparent`
- Hover: `#eaeef2` bg. Use: toolbar, row actions. Hit area >= 28px (44px on touch).

### Cards & Panels
- Background: `#ffffff` page cards, `#f6f8fa` raised panels
- Border: `1px solid #d0d7de`, radius 6px standard, 12px large panels only
- Shadow: none by default; `--elev-raised` only for popovers/dialogs (Primer layered shadow)
- Header: 14px/600 title + 12px muted description + row of actions right-aligned

### Inputs & Forms
- Border: `1px solid #d0d7de`, radius 6px, background `#ffffff`, text `#1f2328`, 12-14px
- Padding: 5px 12px. Placeholder: `#656c76`. Label: 14px/500 `#1f2328` above input.
- Focus: `2px solid #0969da` outline offset -1px + Primer ring shadow. Never blur-only focus.
- Help: 12px `#59636e` below input. Error: 12px `#d1242c` + `1px solid #d1242c` border.
- Tables: header `#f6f8fa` bg, 12px/600 uppercase? No uppercase (R108 heritage) — 12px/600 sentence case, row separators `1px solid #eaeef2`, row hover `#f6f8fa`, tabular numbers.

### Badges / Counters
- **State open**: transparent bg, `#1a7f37` text? Primer open uses green. Keep: `1px solid #d0d7de`, 9999px pill, 12px/500, tabular count.
- **Counter**: `#eaeef2` bg, `#1f2328` text, 9999px, 12px/500 tabular. Never violet by default.
- **Success/Danger dots**: 8px solid dot + 12px label, status only.

### Navigation
- Left sidebar `#f6f8fa`? No — sidebar `#ffffff` with `1px solid #d0d7de` right border, 14px/500 links `#1f2328`, selected: `#eaeef2` bg + `#0969da` left indicator via `box-shadow: inset 2px 0 0 var(--accent)` (never border-left épaisse décorative).
- Top bar: `#ffffff`, bottom border `#d0d7de`, search input monospace-aware, 6px radius.

## 5. Layout Principles

### Spacing System
- Base unit: 4px (Primer). Scale: 4, 8, 12, 16, 20, 24, 32, 48.
- Dense rhythm: section-y 64px desktop / 48px tablet / 32px phone (vs Stripe 96 / Linear 80+). Tool pages scroll, they don't stage.

### Grid & Container
- Max content width: 1280px (wide tables, diff views). Gutters 32/24/16.
- Layouts: sidebar 264px + fluid main; list/detail split; full-width tables with sticky header.
- No centered marketing hero. Page head = title + description + actions on one row, then content.

### Whitespace Philosophy
- **Density with scan lines**: rows separated by `#eaeef2` hairlines, not by vast empty sections.
- **Headers carry context**: every number shows `n / total (fenêtre)` — never a bare count (anti-R108 §5).
- **One focal accent per view**: the primary button OR the selected nav item, never five blue things competing.

### Border Radius Scale
- Small 6px: buttons, inputs, badges, cards — the workhorse (Primer medium).
- Medium 6px: same tier (Primer has no 8px middle) — intentional flat scale, unlike Stripe 4-8 / Linear 6-8.
- Large 12px: dialogs, large panels only.
- Pill 9999px: counters, status pills only.

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (0) | none | page, rows, inline |
| Ring | `0 0 0 1px var(--border)` | cards, inputs at rest |
| Raised | `0 1px 2px rgba(31,35,40,0.06), 0 8px 24px rgba(66,74,83,0.12)` | popovers, dialogs, dropdowns |
| Focus | `0 0 0 3px color-mix(in oklab, var(--accent), transparent 70%)` + `2px solid` outline | keyboard focus, always visible |

**Shadow Philosophy**: Primer shadows are neutral and functional. No brand tint (Stripe blue), no border-as-shadow luminance trick (Linear dark). Shadow means "this floats above the work surface" and nothing else. Cards at rest have no shadow — border does the job.

## 7. Do's and Don'ts

### Do
- Use 14px/400 as default body, 12px muted for metadata, mono + tnum for data.
- Keep tracking at 0 everywhere. Density comes from size and-hairlines, not compression.
- Use `#0969da` only for action/focus/selection, max 2 visible uses per screen.
- Keep borders visible (`#d0d7de` / `#eaeef2`). Structure beats shadow.
- Write numbers with context: `12/48 (7j)`, never bare `12`.
- UI language = user language (French here unless asked otherwise).

### Don't
- Don't use sohne-var/Inter display heroes, weight 300 whisper headlines, or -1.4px tracking — that's Stripe, not a devtool.
- Don't use dark `#08090a` canvas + white-translucent borders + indigo glow — that's Linear, not a devtool.
- Don't use gradients, glassmorphism, glow, neon, bounce easing (anti-slop R108/R109).
- Don't animate width/height — transform/opacity only, 80-160ms, `cubic-bezier(0.33,1,0.68,1)`.
- Don't use pill radius on cards or 700 bold or uppercase labels.
- Don't put status colors (green/yellow/red) on interactive primary elements — status is status, action is blue.

## 8. Responsive Behavior

| Breakpoint | Width | Changes |
|------------|-------|---------|
| Phone | <640px | single column, sidebar -> top bar + overflow menu, tables -> horizontal scroll with sticky first column |
| Tablet | 640-1024px | sidebar collapses to icons, 2-col grids |
| Desktop | 1024-1280px | full sidebar 264px, tables full-bleed in 1280 container |
| Large | >1280px | centered 1280, generous side margins, diff views keep 80-char code measure |

- Touch targets: 28px minimum desktop density, 44px on coarse pointers (media query bumps padding).
- Tables never wrap code: horizontal scroll, mono preserved.
- Dialogs: full-screen sheet on phone, centered 480-640px modal on desktop.

## 9. Agent Prompt Guide

### Quick Color Reference
- Primary action: `#0969da`, hover `#0550ae`, on-accent `#ffffff`
- Page: `#ffffff`, raised `#f6f8fa`, inset `#eaeef2`
- Text: `#1f2328`, secondary `#59636e`, muted `#656c76`
- Borders: `#d0d7de` default, `#eaeef2` soft
- Status: `#1a7f37` / `#9a6700` / `#d1242c` (status only)

### Example Component Prompts
- "Create a devtool page head on white: title 20px/600 #1f2328, description 14px #59636e, primary button #0969da 6px radius 5px 16px + default button #f6f8fa with 1px solid #d0d7de. Base font 14px system stack, tracking 0."
- "Design a data table: header #f6f8fa bg, 12px/600 #1f2328 labels, rows separated by 1px solid #eaeef2, row hover #f6f8fa, 12px tabular numbers, mono for IDs/hashes. Container max 1280."
- "Build a status counter pill: #eaeef2 bg, #1f2328 text, 9999px radius, 12px/500 tabular. Never violet."
- "Create a form field: label 14px/500 #1f2328, input white with 1px solid #d0d7de 6px radius 5px 12px, placeholder #656c76, focus 2px solid #0969da + Primer ring, help 12px #59636e."
- "Design a dialog: white, 12px radius, Primer raised shadow, title 20px/600, actions right-aligned primary + default, 64px section rhythm."

### Iteration Guide
1. Base font is 14px system stack, tracking 0 — never compress.
2. One accent use per view: primary button OR selected nav, not both shouting.
3. Borders do the structure: `#d0d7de` containers, `#eaeef2` row hairlines. Shadow only when floating.
4. Mono + tabular numbers for anything countable or copyable.
5. Radius stays 6px functional, 12px dialogs. No marketing curves.
6. Motion 80-160ms `cubic-bezier(0.33,1,0.68,1)`, transform/opacity only, `prefers-reduced-motion` freezes.
7. Every number ships with context `n/total (fenêtre)`.
8. Critique loop: re-check against this DESIGN.md + R109 before shipping; batch 1 token family per PR.
