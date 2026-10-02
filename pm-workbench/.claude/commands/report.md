---
description: Say where things stand - the weekly leadership update, OKR refresh, strategy refresh, or how the workbench itself is doing (usage, or the monthly review of dropped balls and decision quality).
model: haiku
argument-hint: [weekly-update|okr-refresh|strategy-refresh|workbench-health|monthly-review] [audience or period]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `report`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `weekly-update` | The leadership update, drafted from maintained state |
| `okr-refresh` | Retrieve already-calculated OKR values, log them, draft the destinations |
| `strategy-refresh` | Refresh the strategy from accumulated state (opus) |
| `workbench-health` | Which workflows you use, which fail or never run |
| `monthly-review` | Monthly: dropped balls and decision quality first, with a recorded baseline; runs on a schedule |

## Choosing

- "Draft my weekly update": `weekly-update`. "Pull this week's or month's numbers": `okr-refresh`. "Update the strategy doc": `strategy-refresh` (Deep: print the usage estimate first). "How is the workbench doing": `workbench-health`. "Monthly review", "is the workbench helping", "dropped balls": `monthly-review`.
- Audience and cadence words (leadership, weekly, monthly) pick between `weekly-update` and `strategy-refresh`; ask if they do not settle it.
