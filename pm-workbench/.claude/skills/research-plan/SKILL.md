---
name: research-plan
description: >
  Use when the PM says plan research, who should we talk to, or find people to talk to about X. Runs /discover research-plan (criteria and questions only — never names of people).
---

# research-plan

Plain-language entry for **`/discover research-plan`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/research-plan.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
