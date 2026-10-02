---
description: Morning brief - what changed overnight/since last run, with choices, not auto-work
model: haiku
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Summarize what's new since the last brief (check `state/last-brief-date.txt`; create it if absent), reading counts and deltas only — this is a digest, not a deep dive:

- New rows in `registers/evidence.csv` since last brief (count + one-line themes)
- `registers/commitments.csv` — anything due today or overdue
- To-dos: run `python3 scripts/todo_register.py counts` and report its line (due today, overdue, blocked, open). Counts only; if `registers/todos.csv` does not exist, skip the line. Do not read the rows.
- `registers/initiatives.csv` — anything whose last_updated is stale relative to its stage
- New files in `inbox/` awaiting processing (count by type)
- Latest jira-reconcile output — open flags not yet resolved
- `reference/context/current-priorities.md` — restate my stated priorities for the week so the brief is framed against them
- Overnight work (from the scheduled routines): drafts in `outputs/todo-drafts/` and queued proposals in `outputs/todo-proposals/` that I have not reviewed (names and counts only), and any `failed` or `skipped-paused` rows in `logs/scheduled-runs.csv` since the last brief. Offer `/todo propose` for a queue and `/todo work TODO-nnn` for a draft. Skip the line if none.
- Calendar-relevant: if I've noted meetings in `inbox/meetings/` or the living context, flag any needing prep

Then present choices, not actions:
```
Good morning. Since [date]:
- Evidence: N new (themes: ...)
- Commitments: N due today, N overdue
- To-dos: N due today, N overdue, N blocked
- Inbox: N unprocessed
- Stale initiatives: [names]
- Jira flags open: N

Suggested: 1) /capture process-inbox  2) /sync jira-reconcile  3) prep for [meeting]  4) /todo list --filter overdue (if any overdue)  5) nothing urgent — carry on
```

**Suppression rule: if nothing material changed and nothing is due, say exactly that in one line and stop** — "Nothing needs you today." A brief that always produces content trains you to skim it; one that's silent when silence is true stays trustworthy.

**Do not run any of those commands automatically.** The whole point of this brief is that scheduled time triggers a decision point, not unattended work. I pick; you execute.

**If `reference/context/current-priorities.md` is blank:** say so in one line and offer to capture this week's top 3 now — never frame the brief against priorities that were never stated.

**Blocked scheduled runs:** read `logs/run-log.csv` for any `BLOCKED:` lines since the last brief and list each as a decision point with what the run needed (CLAUDE.md rule 22). Never re-run the blocked command from here — offer it.
