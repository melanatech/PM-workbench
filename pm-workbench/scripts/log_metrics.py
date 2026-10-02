#!/usr/bin/env python3
"""
log_metrics.py — logs metric values that are ALREADY CALCULATED by their
source dashboards (your OKR dashboard, behavior-analytics tool, experiment tool). This script
never computes, derives, or re-derives a metric from raw rows. Its only jobs:

  1. Append {metric, value, as_of_date, retrieved_date, source} to
     state/okr-history.csv
  2. Flag if as_of_date is older than the metric's max_data_age_days
     (the dashboard's own data is stale, not that anything needs recalculating)
  3. Flag if the new value differs from the last logged value for that
     metric by more than flag_if_change_exceeds (worth a second look before
     reporting, not evidence of an error)

If a metric ever genuinely needs calculation from raw row-level exports
(no dashboard aggregates it for you), that is a different, explicitly-named
workflow — mark it in its YAML as `retrieval_method: raw_calculation` and
write a dedicated script for that one metric. Don't fold it into this one.

Usage (called by /report okr-refresh, not run standalone):
  python3 scripts/log_metrics.py --metric onboarding_completion \
      --value 0.412 --as-of 2026-07-15 --source quicksight

STUB: this script exits with an error; it does not append rows or check thresholds.
Until it is implemented and tested, use an approved source and manually append a
CSV-quoted row to state/okr-history.csv with the columns above. Compare configured
freshness/change thresholds manually and note that automated checks did not run.
"""

import sys

if __name__ == "__main__":
    print("log_metrics.py is a stub — no metric was recorded and no thresholds were checked.")
    sys.exit(1)
