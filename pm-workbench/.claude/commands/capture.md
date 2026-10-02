---
description: Get something in - close out a meeting into the registers, or sweep the inbox into structured records. For a 60-second capture use /quick-close.
model: haiku
argument-hint: [meeting-closeout|process-inbox] [notes, a file in inbox/meetings/, or nothing for the inbox]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `capture`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `meeting-closeout` | Meeting notes, a transcript or an AI summary, pasted or as a file: decisions, commitments and risks flow into the registers |
| `process-inbox` | Everything new in `inbox/`: classify, extract, file to registers, archive |

## Choosing

- Pasted text, or a path in `inbox/meetings/`, that reads as a meeting: `meeting-closeout`.
- No input, "catch up the inbox", or a request to process what is waiting: `process-inbox`.
- A three-to-five word dictated note or "I only have a minute": that is `/quick-close`, its own command; tell me and stop. Do not route it here.
- Several meeting files at once: `process-inbox` handles them with the same reconciliation.
