---
name: workbench-health
description: >
  Use when the PM asks how the workbench is doing or what workflows are used. Runs /report workbench-health from script numbers only.
---

# workbench-health

Plain-language entry for **`/report workbench-health`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/workbench-health.md` in full (same gates as the slash command). Prefer dispatching via the `/report` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
