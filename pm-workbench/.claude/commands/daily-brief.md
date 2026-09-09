---
description: Morning brief - what changed overnight/since last run, with choices, not auto-work
model: haiku
execution_mode: fast   # fast=0 reviewers, standard=1-2, deep=full panel (see CLAUDE.md)
---

Summarize what's new since the last brief (check `state/last-brief-date.txt`; create it if absent), reading counts and deltas only — this is a digest, not a deep dive:

- New rows in `registers/evidence.csv` since last brief (count + one-line themes)
- `registers/commitments.csv` — anything due today or overdue
- `registers/initiatives.csv` — anything whose last_updated is stale relative to its stage
- New files in `inbox/` awaiting processing (count by type)
- Latest jira-reconcile output — open flags not yet resolved
- `reference/context/current-priorities.md` — restate my stated priorities for the week so the brief is framed against them
- Calendar-relevant: if I've noted meetings in `inbox/meetings/` or the living context, flag any needing prep

Then present choices, not actions:
```
Good morning. Since [date]:
- Evidence: N new (themes: ...)
- Commitments: N due today, N overdue
- Inbox: N unprocessed
- Stale initiatives: [names]
- Jira flags open: N

Suggested: 1) /process-inbox  2) /jira-reconcile  3) prep for [meeting]  4) nothing urgent — carry on
```

**Suppression rule: if nothing material changed and nothing is due, say exactly that in one line and stop** — "Nothing needs you today." A brief that always produces content trains you to skim it; one that's silent when silence is true stays trustworthy.

**Do not run any of those commands automatically.** The whole point of this brief is that scheduled time triggers a decision point, not unattended work. I pick; you execute.

**If `reference/context/current-priorities.md` is blank:** say so in one line and offer to capture this week's top 3 now — never frame the brief against priorities that were never stated.
