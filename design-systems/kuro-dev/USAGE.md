# Kuro Dev Usage

Design System 2.0 package guide for OpenDesign agents and reviewers.

## Read Order

1. Read this file first to understand the package contract.
2. Read `DESIGN.md` for visual intent, constraints, and anti-patterns.
3. Paste `tokens.css` into the first artifact `<style>` block before writing component CSS.
4. Use `components.manifest.json` for the compact component inventory; open `components.html` when exact selectors or states matter.
5. Inspect `preview/` pages when a visual sanity check is useful.

## Design Highlights

- Primer-dense devtool: functional light canvas, visible borders, zero marketing decoration
- System fonts + tabular numerals for data density, no negative tracking, no custom display font
- Primer blue `#0969da` as the only chromatic accent, capped at primary actions and focus
- Elevation via Primer layered shadow, never blue-tinted (Stripe) nor luminance-stepping (Linear)

## Do

- Preserve the schema token names exactly so cross-brand switching stays reliable.
- Use `--accent` for primary actions, links, focus states, and one clear focal element.
- Reuse component groups from `components.manifest.json` before inventing new controls.
- Treat `source/` files as audit evidence for the bundled fixture backfill.

## Avoid

- Avoid raw hex values outside the copied `:root` token block.
- Avoid redefining Tailwind or design-token values independently of `tokens.css`.
- Avoid claiming original upstream source evidence; this package is based on the curated bundled fixture.
- Avoid adding new component recipes that are not represented in `components.html` or `DESIGN.md`.
- Avoid importing Stripe/Linear decorative patterns (whisper-weight heroes, dark luminance surfaces, blue-tinted shadows) into this devtool identity.
