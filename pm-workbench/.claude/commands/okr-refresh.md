---
description: Retrieve OKR metrics (already calculated by their dashboards), log them, draft the three destinations
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

This is a workflow prompt, not a connected dashboard integration. Use only an
approved, verified read path or a value/export I provide. If a source or metric
definition is missing, ask for it; do not claim retrieval, freshness validation,
or automated logging when those have not run. Store metric definitions and
source links only where company policy permits.

For a first run without metric YAMLs in `reference/metric-definitions/`, ask
which metrics, their approved sources, the displayed values and as-of dates,
and their targets. Draft definitions for review; do not silently persist
company-specific URLs or data into tracked files.

1. **Retrieve — do not calculate anything.** Use an approved verified source path, or the value/export I provide. The browser bridge may be unavailable. Read the exact value described in `what_to_read` — this should be the dashboard's already-calculated number. Note its "as of" / last-updated date, and capture any breakdowns listed in `also_capture`. If the source cannot be read, stop and report the gap.
2. **Log:** `scripts/log_metrics.py` is a stub and exits unsuccessfully. Until it is implemented and tested, manually append the verified value to `state/okr-history.csv` using the columns `metric,value,as_of_date,retrieved_date,source` and valid CSV quoting. If the file is new, add that header first. Compare freshness and change thresholds from the metric definition manually, and state that no automated threshold check ran.
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
