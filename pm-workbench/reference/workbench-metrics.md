# Workbench metrics — what is counted, and what it cannot tell you

Produced by `scripts/workbench_metrics.py`. Code counts files on disk; no model estimates anything. The first `--snapshot` starts a 21-day baseline in `state/health-history.csv`. There are no numbers from before the workbench, so nothing here can say the workbench improved on your old way of working. It can show whether things are moving the right way from the day you started measuring.

Lead measures: **dropped balls**, then **decision quality**. Time saved is secondary and is not measured.

| Metric | Counted as | Cannot tell you |
|---|---|---|
| Commitments past due, not closed | commitments with a due date before today whose status is not a closed word | whether the commitment is still wanted; a stale row nobody closed counts as dropped |
| To-dos past due / blocked | open, in progress or blocked to-dos with a past due date; status blocked | whether the due date was realistic |
| Active initiatives not updated in 30+ days | initiatives not launched/killed/done/archived with `last_updated` 30+ days ago | whether an unchanged initiative is genuinely on track |
| Inbox files older than 3 days | files in `inbox/` last modified over 3 days ago | whether they matter |
| Runs that logged BLOCKED | run-log rows in the last 30 days with BLOCKED | what was owed; read the note |
| Decisions in 30 days, no source, no owner | `decisions.csv` rows by date; empty `source_link` / `made_by` | whether the decision was good, only whether it is traceable |
| Decisions superseded within 60 days | a later row's text says supersede/reverse/replaces/overrule/overrides and names an earlier ID | reversals phrased any other way; this is a text match and under-counts |
| Final-stage initiatives with no linked decision | stage launched/killed/iterating with empty `related_decisions` | whether a decision was made but never linked |
| Workflow runs / repeat runs | run-log rows; same workflow within 7 days, cadence workflows excluded | whether a repeat was rework or a legitimate second pass |
| Outputs tracked / edited | hash recorded when Claude wrote a file under `outputs/` or `drafts/`; edited if the file differs now | whether you edited because it was wrong or just changed your mind; edits made inside Claude's own later write are replaced, not counted |
| Context files updated in 30 days | CLAUDE.md and `reference/context/*` by modified date | whether the update was a good one |
| To-dos open, median age, done, dropped | from `registers/todos.csv` | priority or effort |
| Proposals offered / accepted | logged by `/todo propose` in `logs/todo-proposals.csv` | whether an accepted proposal was useful |

| Scheduled runs, failed, skipped | rows in `logs/scheduled-runs.csv` (ok/failed; paused, capped and already-running skips; a run that found nothing new is not counted) | whether a run's output was useful; a run can exit 0 and still have BLOCKED a step, which shows under Dropped balls |
| To-do drafts written | `TODO-*.md` files in `outputs/todo-drafts/` by modified date | whether you used a draft; read it by hand |

Not captured by code, so recorded by hand in `logs/review-notes.csv` (`date,metric,value,note`): flags raised that you acted on, corrections you made to an update before sending, your own read on decision quality.

Regression check on the fixture is separate: `python3 scripts/score_fixture.py --root <isolated workspace>` scores a Lumenly run against `fixtures/lumenly/gold.json` (found, missed, invented). It guards against breaking the kit; it does not show the kit helps in real work.
