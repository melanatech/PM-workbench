---
name: learn-product-flow
description: >
  Use when the PM says I need to understand how X works in the product, walk the flow, or learn a product flow. Runs /discover learn-product-flow.
---

# learn-product-flow

Plain-language entry for **`/discover learn-product-flow`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/learn-product-flow.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
