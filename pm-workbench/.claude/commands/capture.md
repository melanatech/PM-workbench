---
description: Get something in - close out a meeting into the registers, or pull Downloads clips + sweep inbox into structured records. For a 60-second capture use /quick-close.
model: haiku
argument-hint: [meeting-closeout|process-inbox] [notes, a file in inbox/meetings/, or nothing for the inbox]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `capture`. Do not run anything before you have read it. Do not narrate that read (or `routes.json`) in chat — keep plumbing in thinking. If prep finishes and the next step is obvious (e.g. inbox staged to reprocess), dispatch that workflow in the **same turn** — never end on "Ready to reprocess." After the runner returns: paste its RESULT/PROPOSALS/QUESTIONS once and stop — no "Done." wrap-up.

## What this command covers

| Workflow | Use it for |
|---|---|
| `meeting-closeout` | Meeting notes, a transcript or an AI summary, pasted or as a file: decisions, commitments and risks flow into the registers |
| `process-inbox` | **Always** starts by pulling `~/Downloads/pm-workbench-inbox/` into `inbox/`, then processes everything waiting (clips, PDFs, docs, meetings) |

## Choosing

**Plain language:** follow `.claude/workflows/_plain-language.md` — match → run; never improvise a lighter path.

- Pasted text, or a path in `inbox/meetings/`, that reads as a meeting: `meeting-closeout`.
- **Any** of these plain-language asks → **`process-inbox` immediately** (no "did you mean?", no bare `ls inbox/`): process clips, web clips, chrome clips, clipper, process documents, process PDFs, I uploaded something, something new, what's waiting, catch up the inbox, pull Downloads, anything in Downloads.
- A three-to-five word dictated note or "I only have a minute": that is `/quick-close`, its own command; tell me and stop. Do not route it here.
- Several meeting files at once: `process-inbox` handles them with the same reconciliation.
