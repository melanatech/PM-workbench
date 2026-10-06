---
name: daily-brief
description: >
  Use when the PM says morning, what's new, catch me up, daily brief, or orient me for today. Runs /brief daily-brief. Never improvise a partial peek at one register.
---

# daily-brief

Plain-language entry for **`/brief daily-brief`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/daily-brief.md` in full (same gates as the slash command). Prefer dispatching via the `/brief` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
