---
description: Close out a meeting - decisions, commitments, and risks flow into the registers
argument-hint: [paste notes/transcript, or filename in inbox/meetings/]
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Meeting input: $ARGUMENTS

(This can be typed notes, a downloaded meeting transcript/AI summary (Teams, Zoom, Meet) if you organized the meeting, whatever your meeting tool's AI summary produces if you didn't, or a dictated voice memo transcript — treat all of them the same way below.)

1. Extract: decisions, commitments (owner + due date), risks, assumptions stated, unresolved questions, and anything that changed a prior decision.
2. **Reconcile against current state:** compare extracted items with `registers/decisions.csv`, `registers/commitments.csv`, and (if provided or fetchable) relevant Jira tickets. Flag conflicts explicitly — e.g., "meeting moved readiness to Aug 19 but ticket still says Aug 5."
3. **Cross-check against `registers/initiatives.csv`:** if a decision or commitment touches a feature already in motion, name it explicitly — "this affects [initiative], currently at [stage]" — and note whether it implies re-running `/prd-package`, `/prototype-build`, or `/experiment-package` for that initiative. This is what stops a hallway decision from silently going stale in someone's PRD.
4. Write clear, unambiguous register updates directly (per CLAUDE.md, internal writes don't need live approval) — tell me what got logged. For anything genuinely ambiguous (unclear owner, conflicting dates, a decision that reads differently depending on tone), show it as a proposed diff and ask, rather than guessing or blocking on approval for everything.
4. Save the summary to `outputs/daily/[date]-[topic]-meeting.md`: summary, decisions, action items, risks, open questions, and "changes from prior decisions."
5. Draft (do not send): any follow-up message needed, and the text of any Jira comment or ticket the meeting implies — formatted for the internal tool, ready for me to paste or approve.

The measure of this command is not the summary — it's that the registers stay true. A meeting isn't closed out until its decisions and commitments are reconciled with the system of record.
