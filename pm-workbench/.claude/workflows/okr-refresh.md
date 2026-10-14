---
description: Retrieve OKR metrics (already calculated), log them, draft the three destinations
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Context dependencies: soft: none | hard: kr-metric-map

**Step 0 — preflight:** `python3 scripts/context_preflight.py --root <live> --topic "okr $ARGUMENTS"`. Reuse prior OKR digests for framing; still pull live dashboard numbers per rule 5 (never invent).

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

1. **Retrieve — do not calculate anything.** Prefer an approved dashboard path when configured. Also accept: the value I paste, a CSV export, or an internal deck/doc that names the metric and its as-of date. Read the exact displayed aggregate — never recompute from raw rows. Capture: as-of / last-updated, **timeframe** (period covered), **filters** on the view, **unit**, the source's own **definition** (numerator, denominator/base, feature list, scale), any **displayed delta** callout, and breakdowns in `also_capture`. Before logging, match the number to the KR it will be cited for by definition (see `reference/metric-definitions/kr-metric-map.md`): a 1+ feature adoption rate is not a single-feature usage rate, and a parent L1 metric is not the L2 KR. If the definition is not on the source, write "Not defined in source" — never guess it. Multi-metric charts → one value per named series (same timeframe/filters/`chart` label). If nothing usable is available, stop and report the gap.
2. **Log:** `scripts/log_metrics.py` is a stub. Manually append to `state/okr-history.csv` with `metric,value,unit,as_of_date,retrieved_date,timeframe,filters,delta,chart,definition,definition_source,notes,source` (header if new; valid CSV quoting). `source` must name the concrete path (dashboard URL/bookmark, or `archive/…` / inbox path). `definition` is the source's own wording for what the number counts and its base, written in the house voice ("The percentage of … who …"); `definition_source` says where that wording came from (dashboard definition text, tooltip, deck page) or "Not defined in source". A definition inferred from labels or arithmetic must say `[inferred]`. Put caveats in `notes` (do not recompute). Rolling windows ("past 30 days") and month-to-date values are logged with that timeframe and a PARTIAL/rolling note. Leave `delta`/`filters`/`chart`/`notes` empty when the source does not show them — do not invent deltas from prior rows. Compare freshness/thresholds from the metric definition manually; say automated checks did not run.
3. **Conflicts:** if two internal sources disagree on the **same** metric definition, prefer the newer `as_of_date`, log that row, and still report the conflict (rule 8) if an older series or alternate definition remains. If they are clearly **different metrics** (e.g. one official KR vs a cohort/product-line split of a similar name), log each under a distinct metric name and open the "which is official KR?" question — do not overwrite one with the other.
4. **Narrate** — for each metric: current vs. target vs. prior, whether the move looks meaningful, which segment drove it (from the breakdown you captured), and anything that smells like an instrumentation issue rather than a real change. Prefer the logged `delta` when the source displayed one; if narrating vs last history row instead, say that explicitly. Format:
```
Objective: [objective]
Current: X  |  Target: Y  |  Change: +/-Z (source-displayed | vs last logged — say which)
Timeframe: [period the number covers]  |  Filters: [or none]
As of: [date from the source, not today's upload date]
Chart: [shared label if multi-series, else omit]
Notes: [definition/calculation as labeled, or omit]
Source: [dashboard | internal deck/doc path]
Primary contributor: ...
Risk/caveat: ...
Recommended action: ...
```
5. **Three destinations, drafted:**
   - Weekly-update paragraph → feeds `/report weekly-update`
   - Spreadsheet row(s) matching `state/okr-history.csv` columns, ready to paste
   - OKR-site text block matching prior entries' format; pre-fill the form if browser access allows and I approve, and **stop before submit**
6. **Cross-check against `registers/initiatives.csv`:** if a metric that moved is the related_okr for an active initiative, name that initiative directly in the narrative — "this is the target metric for [initiative], currently at [stage]" — instead of reporting the number in isolation from the work meant to move it. If a recent `/report ship-signal` readout exists under `outputs/releases/` for the same metric window, cite its verdict vocabulary (`MOVED`/`FLAT`/`INCONCLUSIVE`/`DATA GAP`) — do not re-adjudicate the release loop here.
7. Save the full report to `outputs/monthly/[date]-okr-report.md` (or weekly/ for weekly runs).

When surfaces disagree on **roadmap/status/scope**, resolve by the **Roadmap surface authority** table in `SOURCE-POLICY.md`. Metric authority follows the Official metrics row and the dated-internal-numbers exception there.

## Rule 5 — log the displayed number, never recompute

OKR and metric values are already calculated somewhere. Log the displayed number; never recompute it from raw rows. The usual source is an OKR dashboard. Also valid: an internal leadership or metric deck, a wiki metric page, or an export that shows a named metric with an as-of / report date (and ideally the same definition as the key result).

Append a verified row to `state/okr-history.csv` with `metric,value,as_of_date,retrieved_date,timeframe,filters,delta,chart,notes,source` (valid CSV quoting; header if new). `as_of_date` is the source's report stamp. `retrieved_date` is when you captured it. `timeframe` is the period the number covers (for example past 30 days, or a closed month) — not the same as either date. `filters` is the cohort, product, or device applied on that view (empty if none). `delta` is the displayed change callout if the source shows one — never invent one by subtracting prior history rows. `chart` is the shared label when several series come from one multi-metric chart (one row per series). `notes` is how the figure is defined, as the source states it, plus short caveats. `source` is a concrete path or URL.

Prefer a live dashboard read when both a dashboard and a doc exist and disagree on the same metric and definition. Otherwise prefer the newer `as_of_date` from an internal doc and still report the conflict (rule 8) if definitions or cohorts differ. `scripts/log_metrics.py` is a stub — until tested, append manually and say that automated freshness checks did not run. Web search and external public pages are not metric sources. If a metric has no pre-calculated aggregate anywhere and needs calculation, create a separate, explicitly named workflow. See `reference/metric-definitions/example.yml`. The steps above are how this workflow applies the rule.
