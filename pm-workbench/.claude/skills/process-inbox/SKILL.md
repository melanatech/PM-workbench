---
name: process-inbox
description: >
  Use whenever the PM wants newly captured or uploaded material processed into the
  workbench — including plain language like "process the web clips", "process new
  documents", "I uploaded something", "catch up the inbox", "pull clips", "chrome
  clips", "clipper stuff", "anything waiting", "process what's in Downloads", or
  "there are new PDFs". Always pull ~/Downloads/pm-workbench-inbox into inbox/
  first via scripts/intake_status.py; never answer from a bare ls of inbox/ alone
  or say "nothing found" without that script's STATUS line.
---

# Process inbox (plain-language entry)

This skill exists so **natural language** still runs the real intake path.
Do **not** improvise a lighter check.

## Required — do this in the same turn

1. Working directory must be the live workspace (`~/pm-live` as first Cursor folder). If not, say so and stop.
2. Run intake (full stdout stays in thinking/logs — **not** user-facing RESULT):

```bash
python3 scripts/intake_status.py --root "$(pwd)"
```

   Use `--root "$HOME/pm-live"` if cwd is wrong. RESULT gets one line only (e.g. `Intake: pulled 1 from Downloads; 5 unprocessed`).

3. Then read and follow `.claude/workflows/process-inbox.md` from Step 0 onward (intake already done — continue with every `inbox:` path listed). Prefer dispatching `/capture process-inbox` via the cluster protocol when in a router session; if you are already in-session, execute the workflow inline the same way.

## Forbidden

- Looking only at `inbox/` (or only at Downloads) and declaring empty
- Saying "nothing found" / "inbox is empty" without `intake_status.py` stdout showing `STATUS: nothing waiting`
- Pasting the full `intake_status.py` stdout into user-facing RESULT
- Skipping the pull because the user said "documents" or "clips" instead of `/capture process-inbox`
- Asking "did you mean process-inbox?" when the phrasing clearly matches this skill — just run it
- Indexing a house-format doc in `found-templates-index.md` without a Tier 2 PROPOSAL when no real `reference/templates/<slug>.md` exists yet
- Auto-writing a new template file without approval
- Stopping at a one-line `learning/[area].md` update when named-entity back-propagation applies (see process-inbox learning compile)
- Treating `capture_kind: screenshot` stub body as a failed capture (vision-read the PNG)
- Treating `capture_kind: walkthrough` packages as failed because the md body is a timeline (vision-read `*.step-NN.png`)
- Routing `inbox/slack/` as meetings by default (discovery-adjacent unless clearly a meeting summary)
