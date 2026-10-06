---
name: experiment-analyze
description: >
  Use when the PM asks what experiment results said or to analyze an experiment export. Runs /build experiment-analyze with integrity review.
---

# experiment-analyze

Plain-language entry for **`/build experiment-analyze`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/experiment-analyze.md` in full (same gates as the slash command). Prefer dispatching via the `/build` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
