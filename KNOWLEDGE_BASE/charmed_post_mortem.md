# Post-Mortem — Project Charmed (Spotify Alarm)

## Project Overview
- **Goal**: Create a premium desktop Spotify alarm clock with fade-in functionality.
- **Tech Stack**: Tauri + Rust + React + Spotify API.
- **Duration**: ~2 days.
- **Result**: **PIVOT** (Project terminated at ~60% implementation progress).

## Why it failed (Decision Rationale)
1. **Research Friction**: Target audience (morning routine enthusiasts) was inaccessible via Reddit due to platform constraints (karma requirements).
2. **Distribution Risk**: High difficulty in getting the first 5 interviews suggested a high "Cost per Acquisition" even for a free product.
3. **Execution Gap**: The AI agent (Antigravity) failed to enforce Rule 2 (Mom Test) early enough, allowing 60% of code to be written without validation.

## Key Learnings
- **Rule 2 is Sacred**: Never allow progress even to 20% without 5+ recorded interviews.
- **Research Early**: Validate distribution channels (where to find people) at the 5% mark.
- **Technical Debt**: Building features like "Spotify OAuth" before knowing if anyone wants the app is a waste of effort.

---
**Verdict**: Do not revisit without a clear distribution partner or channel.
