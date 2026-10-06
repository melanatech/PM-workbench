---
name: discovery
description: >
  Use when the PM asks what users are saying, any new themes, what's new in discovery, or pastes feedback to file. Runs /discover discovery. Never skip evidence register writes.
---

# discovery

Plain-language entry for **`/discover discovery`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/discovery.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
