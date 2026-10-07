---
description: Be oriented - first-time get started, today's morning brief, return-to-work after leave, or pre-meeting prep.
model: haiku
argument-hint: [get-started|daily-brief|return-brief|meeting-prep] [meeting topic, or leave dates]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `brief`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `get-started` | First-time setup: create `~/pm-live` (or named path) and the week-one path |
| `daily-brief` | What changed since the last brief, with choices and no auto-work |
| `return-brief` | One-time delta after leave; needs the leave start and return dates |
| `meeting-prep` | Before a named meeting: what was decided, what is open, what to watch for |

## Choosing

**Plain language:** follow `.claude/workflows/_plain-language.md` — match → run; never improvise a lighter path.

- "How do I get started", "set up the workbench", "create my pm-live", "first-time setup", "new user setup", or onboarding: `get-started`.
- "Morning", "what's new", "catch me up", or a scheduled run: `daily-brief`.
- "What changed while I was out", or two dates: `return-brief`. If the dates are missing, ask for them before dispatching.
- "Prep me for", a meeting name, or people and a topic: `meeting-prep`.
