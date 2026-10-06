---
name: context-reconcile
description: >
  Use when the PM says propagate context, backfill from archive, todos feel wrong, open questions scattered, or reconcile living context. Runs /sync context-reconcile. Dispatch heavy-read when sources are large; never skim for context constraints.
---

# context-reconcile

Plain-language entry for **`/sync context-reconcile`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/context-reconcile.md` in full (same gates as the slash command). Prefer dispatching via the `/sync` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
