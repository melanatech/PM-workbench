---
description: Turn a feature or question into a research plan - screening criteria, an outreach strategy with message drafts, and a research/interview guide
argument-hint: [feature or discovery question to research]
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Research target: $ARGUMENTS

This system has no customer directory and no CRM access, and it must never invent one: it does NOT try to be a user-lookup tool and never outputs names of specific people. A name this workflow produced would be a fabrication in the exact format of a real query result. It produces the thinking around research: who to talk to, how to reach them, and what to ask. Three parts, as one package to `outputs/research/[topic]/`:

**1. Screening criteria** — grounded in the feature and the evidence behind it (pull from `/discovery` / `registers/evidence.csv`):
   - Who qualifies: the behaviors, segment, role, and recency that make someone a relevant voice (e.g. "admins at multi-location accounts who ran a scheduled export in the last 30 days")
   - Who to exclude and why (recently interviewed; in an active escalation; internal test accounts)
   - A diversity guard: the criteria that keep the slate from being five near-identical customers (segment mix, tenure mix, an anti-happy-path quota) — hand these to whoever can query your customer records (the account team, an analyst, or you with an export).

**2. Outreach strategy + drafts** — the sequence (who reaches out — you, the CSM, the account manager — and in what order), timing, incentive if any, and per-segment message drafts that reference the specific problem without leading the witness. Drafts only; sending is yours, and account owners get a heads-up first.

**3. Research design** — the outcome/decision the research informs, then a short interview guide: mostly past-behavior questions ("walk me through the last time you…") over hypotheticals, with the specific assumptions each question is meant to test. If a survey fits better than interviews for part of it, say which and draft those items. Write the decision rules — what a finding would have to look like to change the plan — BEFORE any session runs, so conclusions can't drift to fit what we hoped.

If the evidence base is too thin to write good criteria yet, say so and point back to `/discovery` — a research plan built on no evidence just launders assumptions.
