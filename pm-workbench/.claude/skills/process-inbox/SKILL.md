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
2. Run and paste **full stdout**:

```bash
python3 scripts/intake_status.py --root "$(pwd)"
```

   Use `--root "$HOME/pm-live"` if cwd is wrong.

3. Then read and follow `.claude/workflows/process-inbox.md` from Step 0 onward (intake already done — continue with every `inbox:` path listed). Prefer dispatching `/capture process-inbox` via the cluster protocol when in a router session; if you are already in-session, execute the workflow inline the same way.

## Forbidden

- Looking only at `inbox/` (or only at Downloads) and declaring empty
- Saying "nothing found" / "inbox is empty" without `intake_status.py` stdout showing `STATUS: nothing waiting`
- Skipping the pull because the user said "documents" or "clips" instead of `/capture process-inbox`
- Asking "did you mean process-inbox?" when the phrasing clearly matches this skill — just run it
