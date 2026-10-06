---
name: code-dive
description: >
  Use when the PM says how does X work in the code or code dive. Runs /discover code-dive via code-repo-explorer — never dump a whole repo into chat.
---

# code-dive

Plain-language entry for **`/discover code-dive`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/code-dive.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
