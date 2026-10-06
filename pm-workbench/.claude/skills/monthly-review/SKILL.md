---
name: monthly-review
description: >
  Use when the PM asks if the workbench is helping, monthly review, or dropped balls / decision quality check. Runs /report monthly-review.
---

# monthly-review

Plain-language entry for **`/report monthly-review`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/monthly-review.md` in full (same gates as the slash command). Prefer dispatching via the `/report` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
