---
description: Under 60 seconds - capture a meeting's raw essentials and get out. Deep processing happens later, unattended.
model: haiku
argument-hint: [3-5 words max, or dictated voice-to-text]
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Input: $ARGUMENTS (typed, dictated as a voice memo, or pasted from a meeting-tool AI summary — see below)

This is the between-meetings version of `/meeting-closeout` — built for the 90 seconds you have before your next call or before you have to leave. Do the minimum, fast:

1. Save the raw input verbatim to `inbox/meetings/[timestamp]-quick.md` with a timestamp. Nothing else required.
2. If it's obviously one clear decision or one clear commitment (owner + date stated plainly), log it directly to the register. If it's ambiguous or needs judgment, don't guess — just save it raw and stop there.
3. Respond with ONE line: what got saved, nothing more. No summary, no analysis, no "here's what I noticed."

**Full reconciliation against registers, initiatives, and Jira happens later** — at the next `/daily-brief` or nightly `/process-inbox` run, when there's actually time to do it right. This command exists specifically so "I don't have 5 minutes right now" is never a reason a decision goes unrecorded. If you have the actual 5 minutes, use `/meeting-closeout` instead — it does the real reconciliation this command defers.

**If this is a meeting you organized and your meeting tool records it:** its auto-transcript/AI summary is usually richer than what you'd type by hand — worth grabbing if you have 20 extra seconds, but don't let waiting for it delay this command.

**Even faster path:** dictate a 10-second voice memo on your phone/Mac as you're walking out ("decided X, John owns Y by Friday") and drop the transcript in `inbox/meetings/` yourself — that's faster than typing this command at all, and `/process-inbox` picks it up the same way.
