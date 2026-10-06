---
name: return-brief
description: >
  Use when the PM is back from leave or asks what changed while I was out / back from PTO. Runs /brief return-brief (needs leave dates if missing). Never skim Slack from memory instead of the workflow.
---

# return-brief

Plain-language entry for **`/brief return-brief`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/return-brief.md` in full (same gates as the slash command). Prefer dispatching via the `/brief` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
