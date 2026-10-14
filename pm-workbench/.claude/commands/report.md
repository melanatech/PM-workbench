---
description: Say where things stand - the weekly leadership update, OKR refresh, strategy refresh, a roadmap from scratch, or how the workbench itself is doing (usage, or the monthly review of dropped balls and decision quality).
model: haiku
argument-hint: [weekly-update|okr-refresh|strategy-refresh|roadmap-build|workbench-health|monthly-review|ship-signal] [audience or period or release-id]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `report`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `weekly-update` | The leadership update, drafted from maintained state |
| `okr-refresh` | Retrieve already-calculated OKR values, log them, draft the destinations |
| `strategy-refresh` | Refresh the strategy, or draft it from scratch when none exists (opus; Standard by default) |
| `roadmap-build` | Build a roadmap from scratch: Now / Next / Later, every item sourced (sonnet; Deep upgrades the runner to opus) |
| `workbench-health` | Which workflows you use, which fail or never run |
| `monthly-review` | Monthly: dropped balls and decision quality first, with a recorded baseline; runs on a schedule |
| `ship-signal` | Advance one stage of the post-ship measurement loop (notes → metrics → data request → readout → report) |

## Choosing

**Plain language:** follow `.claude/workflows/_plain-language.md` — match → run; never improvise a lighter path.

- "Draft my weekly update": `weekly-update`. "Pull this week's or month's numbers": `okr-refresh`. "Update the strategy doc" or "strategy from scratch": `strategy-refresh` (Standard by default; Deep prints the usage estimate first). "Build a roadmap" or "draft a roadmap from scratch": `roadmap-build` (sonnet; Deep prints the usage estimate, then the runner is opus). "How is the workbench doing": `workbench-health`. "Monthly review", "is the workbench helping", "dropped balls": `monthly-review`. "Ship signal", "did this release move the needle", "advance the release loop", "readout for release X": `ship-signal`.
- "The roadmap changed" or features moved is `/sync roadmap-update`, not `roadmap-build`.
- Audience and cadence words (leadership, weekly, monthly) pick between `weekly-update` and `strategy-refresh`; ask if they do not settle it.
