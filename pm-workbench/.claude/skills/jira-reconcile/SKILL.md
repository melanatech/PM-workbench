---
name: jira-reconcile
description: >
  Use when the PM says check the Jira board, is anything stale, board hygiene, or reconcile Jira. Runs /sync jira-reconcile. Never improvise a casual Jira glance that skips snapshot/diff.
---

# jira-reconcile

Plain-language entry for **`/sync jira-reconcile`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/jira-reconcile.md` in full (same gates as the slash command). Prefer dispatching via the `/sync` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
