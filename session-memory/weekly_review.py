#!/usr/bin/env python3
"""Counts for the session-memory weekly review. No model; proposals are written for the user to approve.

  python3 weekly_review.py              # print the last 7 days' counts
  python3 weekly_review.py --write      # also save reviews/<date>.md under the data home (offered at next start)

Counts per project from log.jsonl: captures, entries added and superseded, audits and their changes,
consolidations, restores, stale-session notices and !force overrides, detector offers, reading-budget
notices (and how many were in partner sessions), model calls today, failed captures. The rework_correction
share comes from the workbench's session_usage.py, which this script does not read.
"""
import argparse
import collections
import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks"))
import common as c  # noqa: E402


def counts(days=7):
    since = datetime.datetime.now() - datetime.timedelta(days=days)
    out = {}
    for log in glob.glob(os.path.join(c.data_home(), "*", "log.jsonl")):
        tally = collections.Counter()
        for line in open(log, encoding="utf-8", errors="replace"):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            when = c.parse_ts(row.get("ts"))
            if not when or when.replace(tzinfo=None) < since:
                continue
            event = row.get("event")
            tally[event] += 1
            if event == "capture":
                tally["entries added"] += row.get("added", 0)
                tally["entries superseded"] += row.get("superseded", 0)
            if event == "audit":
                tally["audit changes"] += row.get("changed", 0)
            if event == "reading-over" and row.get("partner"):
                tally["reading-over in partner sessions"] += 1
            if event == "detector" and row.get("match"):
                tally["pickup offers"] += 1
        if tally:
            out[os.path.basename(os.path.dirname(log))] = dict(sorted(tally.items()))
    return out


def report(data):
    lines = [f"# Session memory weekly review ({datetime.date.today().isoformat()})", "",
             "Counts from the session-memory logs, last 7 days. Proposed changes to thresholds or "
             "haiku-instructions.md need the user's approval; nothing is applied automatically.", ""]
    if not data:
        lines.append("No session-memory activity logged in the last 7 days.")
    for project, tally in data.items():
        lines.append(f"## {project}")
        lines += [f"- {k}: {v}" for k, v in tally.items()]
        lines.append("")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    text = report(counts())
    print(text)
    if args.write:
        dest = os.path.join(c.data_home(), "reviews", f"{datetime.date.today().isoformat()}.md")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "w", encoding="utf-8").write(text)
        print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
