---
description: "Monthly look at whether the workbench is helping: dropped balls and decision quality first, then rework and to-dos. Counts come from code, never from a model."
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

This is the monthly check on the workbench itself. It measures two things first: **fewer dropped balls** (things promised, owed or blocked that slipped) and **decision quality** (decisions with an owner and a source, few reversals). Time saved is secondary and is not estimated here. See `reference/workbench-metrics.md` for what each number means and what it cannot tell you.

Input: $ARGUMENTS (optional: a month, e.g. `2026-10`; default is today)

## Steps

1. **Take the snapshot.** Run `python3 scripts/workbench_metrics.py --snapshot` (add `--today YYYY-MM-DD` only if I named a date). Use ONLY the numbers it prints. Never estimate, round, or fill in a count yourself. A metric shown as `n/a` is a missing source, not a zero; say so.
2. **Run the usage report.** Run `python3 scripts/workbench_health.py` for which workflows ran, failed, were blocked, or never ran.
3. **Check the baseline.** If the metrics output says the baseline period is still open, label every change **provisional** and say how many days remain. Do not call anything an improvement or a regression during the baseline period. There are no pre-system numbers; the first snapshot is the starting point.
4. **Read my manual notes.** `logs/review-notes.csv` (columns `date,metric,value,note`) holds the things code cannot see: flags raised by the kit that I acted on or ignored, how many times I had to correct an update before sending it, and my own read on decision quality. Show the last month's rows. If the file is missing or has nothing for this month, list the questions below as `[NEEDS INPUT]` and continue without them:
   - Of the flags the kit raised this month, how many did you act on, and how many were noise?
   - How many updates or PRDs did you have to correct materially before sending?
   - Any decision this month you would now make differently, and was the reason missing from the register?
5. **Write the review** to `outputs/monthly/[date]-workbench-review.md`, under 400 words, in this order:
   - **Dropped balls**: the Dropped balls table rows, with change since the last snapshot and the one or two that moved most.
   - **Decision quality**: the Decision quality rows; name any decision with no source or no owner by ID (read them from `registers/decisions.csv`, do not guess).
   - **Rework and to-dos**: one short paragraph. Repeat runs and edited outputs point at workflows to tighten; say that, and say that edited outputs are a heuristic.
   - **What the numbers cannot tell you**: one sentence, always. These counts show a trend for one person's use; they do not show the kit caused it.
   - **Proposals**: at most three changes, each tied to a number above (for example, a workflow with repeated runs, a command that never ran, a context file that is stale). Propose only; do not edit `settings.json`, `CLAUDE.md`, any command or workflow from here.
6. **Insights.** Tell me to run `/insights` myself in Claude Code if I want its usage report (I should not rely on it; its availability has not been verified for this setup). Do not run or describe its output.
7. **Unattended runs** (CLAUDE.md rule 22): there is nobody to answer. Finish steps 1–5, mark the manual items `[NEEDS INPUT]` in the file, append `BLOCKED: monthly review needs your manual notes` to `logs/run-log.csv` only if I had no notes at all, and stop.

## Never
- Compute or estimate any figure yourself, or compare against numbers from before the first snapshot.
- Say the workbench saved time. This review does not measure time.
- Delete or rewrite `state/health-history.csv` or `logs/review-notes.csv`. Append only; I edit notes myself.

Show the saved file in full (rule 20). Finish with one line naming the single change you would make first.
