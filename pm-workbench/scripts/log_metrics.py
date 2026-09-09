#!/usr/bin/env python3
"""
log_metrics.py — logs metric values that are ALREADY CALCULATED by their
source dashboards (QuickSight, FullStory, the experiment tool). This script
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

Usage (called by /okr-refresh, not run standalone):
  python3 scripts/log_metrics.py --metric onboarding_completion \
      --value 0.412 --as-of 2026-07-15 --source quicksight

FIRST-TIME SETUP: open in Cursor and ask Claude to implement the argument
parsing + CSV append + threshold checks per this docstring, reading each
metric's max_data_age_days and flag_if_change_exceeds from its YAML in
reference/metric-definitions/.
"""

import sys

if __name__ == "__main__":
    print("log_metrics.py is a stub — ask Claude (in Cursor or Claude Code) "
          "to implement it per the docstring above, once you have your "
          "first metric YAML defined in reference/metric-definitions/.")
    sys.exit(1)
