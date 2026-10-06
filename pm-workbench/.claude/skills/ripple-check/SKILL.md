---
name: ripple-check
description: >
  Use when the PM asks what else does this affect, or reports a decision/news that did not go through a normal command. Runs /sync ripple-check then fan-out. Never answer from memory only.
---

# ripple-check

Plain-language entry for **`/sync ripple-check`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/ripple-check.md` in full (same gates as the slash command). Prefer dispatching via the `/sync` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
