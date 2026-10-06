---
name: research-package
description: >
  Use when the PM says set up a test for X or research package for a prototype/concept. Runs /discover research-package.
---

# research-package

Plain-language entry for **`/discover research-package`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/research-package.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
