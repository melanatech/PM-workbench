---
description: Be oriented - today's morning brief, the return-to-work brief after leave, or a pre-meeting prep.
model: haiku
argument-hint: [daily-brief|return-brief|meeting-prep] [meeting topic, or leave dates]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `brief`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `daily-brief` | What changed since the last brief, with choices and no auto-work |
| `return-brief` | One-time delta after leave; needs the leave start and return dates |
| `meeting-prep` | Before a named meeting: what was decided, what is open, what to watch for |

## Choosing

**Plain language:** follow `.claude/workflows/_plain-language.md` — match → run; never improvise a lighter path.

- "Morning", "what's new", "catch me up", or a scheduled run: `daily-brief`.
- "What changed while I was out", or two dates: `return-brief`. If the dates are missing, ask for them before dispatching.
- "Prep me for", a meeting name, or people and a topic: `meeting-prep`.
