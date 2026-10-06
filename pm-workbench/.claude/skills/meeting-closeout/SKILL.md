---
name: meeting-closeout
description: >
  Use when the PM pastes meeting notes/transcript/AI summary or says close out this meeting, log this meeting, capture this meeting, or process these meeting notes. Runs /capture meeting-closeout. Never improvise a lighter summary-only path that skips registers and fan-out.
---

# meeting-closeout

Plain-language entry for **`/capture meeting-closeout`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/meeting-closeout.md` in full (same gates as the slash command). Prefer dispatching via the `/capture` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / intake / reconciliation / subagent requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command.
