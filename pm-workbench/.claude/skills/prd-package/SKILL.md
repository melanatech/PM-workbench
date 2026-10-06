---
name: prd-package
description: >
  Use when the PM says spec out X, write a PRD, or PRD package. Runs /build prd-package. Required-input rules still apply; a name alone is not enough.
---

# prd-package

Plain-language entry for **`/build prd-package`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/prd-package.md` in full (same gates as the slash command). Prefer dispatching via the `/build` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
