---
description: Retrieve OKR metrics (already calculated by their dashboards), log them, draft the three destinations
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

**No preconditions — first run configures itself.** If no metric YAMLs exist yet in `reference/metric-definitions/`, ask me: which metrics, where each lives (I'll paste the dashboard URL or the current value directly), and the target — then do this run with those answers AND write the YAML(s) so next time is automatic. If `log_metrics.py` is still a stub, append the history row yourself with proper CSV quoting; the script is a later optimization, not a dependency.

1. **Retrieve — do not calculate anything.** Open each metric's `source_url` via the browser bridge. Read the exact value described in `what_to_read` — this is already the dashboard's final, computed number. Also note its "as of" / last-updated date, and capture any breakdowns listed in `also_capture`.
2. **Log:** run `python3 scripts/log_metrics.py --metric [name] --value [x] --as-of [date] --source [source]` for each. It appends to `state/okr-history.csv`, flags if the data is older than `max_data_age_days`, and flags if the value moved more than `flag_if_change_exceeds` versus last time. **A flag means "look before reporting," not "something's wrong."**
3. **Narrate** — for each metric: current vs. target vs. prior, whether the move looks meaningful, which segment drove it (from the breakdown you captured), and anything that smells like an instrumentation issue rather than a real change. Format:
```
Objective: [objective]
Current: X  |  Target: Y  |  Change: +/-Z
As of: [date from the dashboard, not today's date]
Primary contributor: ...
Risk/caveat: ...
Recommended action: ...
```
4. **Three destinations, drafted:**
   - Weekly-update paragraph → feeds `/weekly-update`
   - Spreadsheet row(s) matching `state/okr-history.csv` columns, ready to paste
   - OKR-site text block matching prior entries' format; pre-fill the form if browser access allows and I approve, and **stop before submit**
5. **Cross-check against `registers/initiatives.csv`:** if a metric that moved is the related_okr for an active initiative, name that initiative directly in the narrative — "this is the target metric for [initiative], currently at [stage]" — instead of reporting the number in isolation from the work meant to move it.
6. Save the full report to `outputs/monthly/[date]-okr-report.md` (or weekly/ for weekly runs).


When surfaces disagree, resolve by the **Roadmap surface authority** table in `SOURCE-POLICY.md` — Slack and slides never outrank Jira status or approved scope.
