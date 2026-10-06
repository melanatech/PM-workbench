---
description: Retrieve OKR metrics (already calculated), log them, draft the three destinations
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

This is a workflow prompt, not a connected dashboard integration. Use only an
approved, verified read path, a value/export I provide, or an **internal**
document that already shows the calculated metric with an as-of date (MBR deck,
PPP, wiki). If a source or metric definition is missing, ask for it; do not
claim retrieval or automated logging when those have not run. Store metric
definitions and source links only where company policy permits.

For a first run without metric YAMLs in `reference/metric-definitions/`, ask
which metrics, their approved sources, the displayed values and as-of dates,
and their targets. Draft definitions for review; do not silently persist
company-specific URLs or data into tracked files.

1. **Retrieve — do not calculate anything.** Prefer an approved dashboard path when configured. Also accept: the value I paste, a CSV export, or an internal deck/doc that names the metric and its as-of date. Read the exact displayed aggregate — never recompute from raw rows. Note as-of / last-updated, and any breakdowns in `also_capture`. If nothing usable is available, stop and report the gap.
2. **Log:** `scripts/log_metrics.py` is a stub. Manually append to `state/okr-history.csv` with `metric,value,as_of_date,retrieved_date,source` (header if new; valid CSV quoting). `source` must name the concrete path (dashboard URL/bookmark, or `archive/…` / inbox path). Compare freshness/thresholds from the metric definition manually; say automated checks did not run.
3. **Conflicts:** if two internal sources disagree on the **same** metric definition, prefer the newer `as_of_date`, log that row, and still report the conflict (rule 8) if an older series or alternate definition remains. If they are clearly **different metrics** (e.g. one official KR vs a cohort/product-line split of a similar name), log each under a distinct metric name and open the "which is official KR?" question — do not overwrite one with the other.
4. **Narrate** — for each metric: current vs. target vs. prior, whether the move looks meaningful, which segment drove it (from the breakdown you captured), and anything that smells like an instrumentation issue rather than a real change. Format:
```
Objective: [objective]
Current: X  |  Target: Y  |  Change: +/-Z
As of: [date from the source, not today's upload date]
Source: [dashboard | internal deck/doc path]
Primary contributor: ...
Risk/caveat: ...
Recommended action: ...
```
5. **Three destinations, drafted:**
   - Weekly-update paragraph → feeds `/report weekly-update`
   - Spreadsheet row(s) matching `state/okr-history.csv` columns, ready to paste
   - OKR-site text block matching prior entries' format; pre-fill the form if browser access allows and I approve, and **stop before submit**
6. **Cross-check against `registers/initiatives.csv`:** if a metric that moved is the related_okr for an active initiative, name that initiative directly in the narrative — "this is the target metric for [initiative], currently at [stage]" — instead of reporting the number in isolation from the work meant to move it.
7. Save the full report to `outputs/monthly/[date]-okr-report.md` (or weekly/ for weekly runs).

When surfaces disagree on **roadmap/status/scope**, resolve by the **Roadmap surface authority** table in `SOURCE-POLICY.md`. Metric authority follows the Official metrics row and the dated-internal-numbers exception there.
