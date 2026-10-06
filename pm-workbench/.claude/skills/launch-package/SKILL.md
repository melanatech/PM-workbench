---
name: launch-package
description: >
  Use when the PM says get this ready to launch or launch package. Runs /build launch-package (drift detection first).
---

# launch-package

Plain-language entry for **`/build launch-package`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/launch-package.md` in full (same gates as the slash command). Prefer dispatching via the `/build` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
