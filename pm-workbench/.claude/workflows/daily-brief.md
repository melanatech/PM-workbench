---
description: Morning brief - what changed overnight/since last run, with choices, not auto-work
model: haiku
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Context dependencies: soft: current-priorities, kr-metric-map | hard: none

## Gather plan

List these reads, then batch the independent ones in one turn. Sequence only a step that depends on an earlier result (the brief text depends on the counts). If this session already read a file, pass the distilled brief onward instead of re-reading the raw file. Re-reading the same file for a different task is fine; prompt caching makes that cheap. No session cache.

Independent (batch together):

- `state/last-brief-date.txt`
- `registers/evidence.csv` (rows since the last brief only)
- `registers/commitments.csv` (due today or overdue)
- `python3 scripts/todo_register.py counts`
- `python3 scripts/todo_register.py reconcile --count`
- `registers/initiatives.csv` (last_updated versus stage)
- `inbox/` (counts by type)
- latest `outputs/weekly/*-jira-reconcile.md` (open flags)
- `reference/context/current-priorities.md`
- `python3 scripts/context_health.py --root <live> --brief`
- `python3 scripts/analysis_index.py stale --root <live> --living`
- `outputs/todo-drafts/` and `outputs/todo-proposals/` (names and counts of what I have not reviewed)
- `logs/scheduled-runs.csv` and `logs/run-log.csv` (`BLOCKED:` lines since the last brief)
- `inbox/meetings/` and living context, for meetings that need prep
- `python3 scripts/recurring_corrections.py --root <live>` when `state/usage-history.csv` exists

Then write the brief from those results. Do not run the suggested commands.

Summarize what's new since the last brief (check `state/last-brief-date.txt`; create it if absent), reading counts and deltas only — this is a digest, not a deep dive:

- New rows in `registers/evidence.csv` since last brief (count + one-line themes)
- `registers/commitments.csv` — anything due today or overdue
- To-dos: run `python3 scripts/todo_register.py counts` and report its line (due today, overdue, blocked, open). Counts only; if `registers/todos.csv` does not exist, skip the line. Do not read the rows. Also run `python3 scripts/todo_register.py reconcile --count`. If it prints `likely_done=N` with N greater than 0, add one line: "N to-dos look done, run /todo reconcile". Do not mark them done from the brief.
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

**Suppression rule: if nothing material changed and nothing is due, say exactly that in one line and stop** — "Nothing needs you today." A brief that always produces content trains you to skim it; one that's silent when silence is true stays trustworthy. Still add the context-health line and the stale-deliverable line when those scripts report a gap. Those are not invented brief content.

**Do not run any of those commands automatically.** The whole point of this brief is that scheduled time triggers a decision point, not unattended work. I pick; you execute.

**If `reference/context/current-priorities.md` is blank or template-empty:** say so in one line and offer `/brief context-setup`. If you derive a stand-in from open initiatives and key results, label it "derived, not stated priorities" and ask me to confirm. Never frame the brief against priorities that were never stated.

**Context health:** if `context_health.py --brief` prints `context: ok`, omit the line. Otherwise include that line verbatim.

**Stale living deliverables:** if `analysis_index.py stale --living` prints `stale: none`, omit the line. Otherwise list each PRD, brief, strategy, or roadmap with its `stale_since` and offer a refresh. Do not rewrite them from the brief.

**Blocked scheduled runs:** read `logs/run-log.csv` for any `BLOCKED:` lines since the last brief and list each as a decision point with what the run needed (CLAUDE.md rule 22). Never re-run the blocked command from here — offer it.

**Recurring corrections (when present):** if `state/usage-history.csv` exists, run `python3 scripts/recurring_corrections.py --root <live>` once. If it prints themes, add one short line under Suggested (e.g. "recurring: nonexistent_id — needs a hook, not another rule"). Skip silently when the script reports none.
