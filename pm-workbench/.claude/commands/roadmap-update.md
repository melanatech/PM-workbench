---
description: Apply a roadmap change across every surface it lives on - Jira board, Slack update, tracking spreadsheet, leadership deck - handling multiple features in one pass
argument-hint: [what changed, plain language - can cover several features at once]
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Roadmap changes: $ARGUMENTS

The roadmap lives in more than one place, and a change that lands in only one of them is how versions drift. One input, every surface reconciled:

1. **Parse per feature.** The input may cover several initiatives at once ("scorecards slips a sprint; export reliability enters Next"). Split into one change set per initiative, each cross-referenced against its `registers/initiatives.csv` row and linked decisions — never blur two features' changes together.
2. **Propose, per surface, per feature:**
   - Jira: the specific ticket/epic field changes (dates, status, rank)
   - The roadmap spreadsheet: the exact row edits, matching its existing columns
   - Slack `#product-updates` draft: a short human announcement of what moved and why (draft only)
   - The leadership deck: the replacement bullet(s) for the roadmap slide, matching the deck's existing phrasing style
3. **Present one grouped diff across all surfaces** for batched review; date/priority/scope changes still called out individually. On approval: apply what's applicable (Jira via the established path), hand over paste-ready text for the surfaces only you can touch (spreadsheet, deck), and verify applied changes by re-reading them.
4. Log the change to `registers/decisions.csv` if it reflects a decision (with source), and update each affected initiative's row.

**Required input:** the change and its reason. If the reason is missing ("scorecards slips" — why?), ask — a roadmap change without a stated reason becomes an unanswerable question in three weeks.

**First run:** ask where the roadmap spreadsheet and deck live (links → `reference/links.csv`) and which Slack channel carries roadmap updates.


## Durable cross-surface change record

A roadmap change touches surfaces that can end up partially updated (Jira applied,
spreadsheet not). Before applying anything, write `reference/change-manifests/[date]-roadmap.md`
with one row per surface per feature and its state, and keep it updated as you go:

| surface | feature | intended change | state |
|---|---|---|---|
| Jira | ... | ... | applied ✓ / pending / FAILED |
| roadmap spreadsheet | ... | ... | drafted — needs your paste |
| Slack #product-updates | ... | ... | drafted — needs your send |
| leadership deck | ... | ... | drafted — needs your paste |

The transaction is only "complete" when every required surface reads `applied` or
you've explicitly accepted a `drafted` handoff. If any surface is `FAILED`, say so
loudly and do not report the roadmap as updated. This manifest is the single
durable record governing the whole cross-surface change.


When surfaces disagree, resolve by the **Roadmap surface authority** table in `SOURCE-POLICY.md` — Slack and slides never outrank Jira status or approved scope.
