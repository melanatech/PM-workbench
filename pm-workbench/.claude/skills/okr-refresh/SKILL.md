---
name: okr-refresh
description: >
  Use when the PM says pull this week's numbers, OKR refresh, or update metrics. Runs /report okr-refresh. Never recompute metrics from raw rows.
---

# okr-refresh

Plain-language entry for **`/report okr-refresh`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/okr-refresh.md` in full (same gates as the slash command). Prefer dispatching via the `/report` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
