---
name: competitive-scan
description: >
  Use when the PM asks what competitors are doing or wants a competitive scan. Runs /discover competitive-scan with persistence to state/competitive and the monthly log.
---

# competitive-scan

Plain-language entry for **`/discover competitive-scan`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/competitive-scan.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
