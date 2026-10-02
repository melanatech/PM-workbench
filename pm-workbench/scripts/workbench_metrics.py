#!/usr/bin/env python3
"""workbench_metrics.py — numbers for the monthly review (Plan C). Standard library only.

Counts from the registers and logs on disk; never estimates, never calls a model. Every
metric is a trend indicator for one person's own use, not a score and not proof that the
kit caused a change (see reference/workbench-metrics.md for each definition and what it
cannot tell you).

Lead measures, in this order: dropped balls, decision quality. Then rework, then to-dos.

Usage (from the workbench root)
  python3 scripts/workbench_metrics.py                  # print the table
  python3 scripts/workbench_metrics.py --snapshot       # also record today in state/health-history.csv
  python3 scripts/workbench_metrics.py --json           # machine-readable
  python3 scripts/workbench_metrics.py --today 2026-10-02   # repeatable runs and tests

--snapshot keeps one row per day (re-running the same day replaces it). The first
snapshot starts the baseline period (21 days); changes measured inside it are labelled
provisional. A metric whose source file or column does not exist is reported as "n/a",
never as zero.
"""
import argparse
import csv
import datetime
import glob
import hashlib
import json
import os
import statistics
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY = os.path.join("state", "health-history.csv")
BASELINE_DAYS = 21
STALE_INITIATIVE_DAYS = 30
REVERSAL_WINDOW_DAYS = 60
REDO_WINDOW_DAYS = 7
CLOSED_WORDS = ("done", "closed", "complete", "completed", "cancel", "dropped", "resolved", "met", "fulfilled")
FINAL_STAGES = ("launched", "killed", "iterating")
INACTIVE_STAGES = ("launched", "killed", "done", "archived")
CADENCE_WORKFLOWS = {"brief:daily-brief", "capture:process-inbox", "quick-close", "todo"}
# (key, group, label, direction) — direction says which way is better, for the change column.
METRICS = [
    ("commitments_overdue", "Dropped balls", "Commitments past due and not closed", "down"),
    ("todos_overdue", "Dropped balls", "To-dos past due and not closed", "down"),
    ("todos_blocked", "Dropped balls", "To-dos blocked", "down"),
    ("initiatives_stale", "Dropped balls", f"Active initiatives not updated in {STALE_INITIATIVE_DAYS}+ days", "down"),
    ("inbox_old", "Dropped balls", "Inbox files older than 3 days", "down"),
    ("blocked_runs", "Dropped balls", "Runs that logged BLOCKED (logged in the last 30 days)", "down"),
    ("decisions_30d", "Decision quality", "Decisions logged in the last 30 days", "info"),
    ("decisions_no_source_30d", "Decision quality", "Of those, with no source_link", "down"),
    ("decisions_no_owner_30d", "Decision quality", "Of those, with no made_by", "down"),
    ("decisions_reversed", "Decision quality", f"Decisions a later row supersedes within {REVERSAL_WINDOW_DAYS} days (text match)", "down"),
    ("stage_without_decision", "Decision quality", "Initiatives at launched/killed/iterating with no linked decision", "down"),
    ("runs_30d", "Rework", "Workflow runs logged in the last 30 days", "info"),
    ("repeat_runs_30d", "Rework", f"Same workflow run again within {REDO_WINDOW_DAYS} days (cadence workflows excluded)", "down"),
    ("outputs_tracked", "Rework", "Outputs whose hash was recorded when written", "info"),
    ("outputs_edited", "Rework", "Of those, changed on disk since (edited outside Claude)", "info"),
    ("context_files_updated_30d", "Rework", "CLAUDE.md and reference/context files updated in the last 30 days", "info"),
    ("todos_open", "To-dos", "Open, in progress or blocked", "info"),
    ("todos_median_age", "To-dos", "Median age of open to-dos (days)", "down"),
    ("todos_done_30d", "To-dos", "Marked done in the last 30 days", "up"),
    ("todos_dropped_30d", "To-dos", "Dropped in the last 30 days", "info"),
    ("proposals_offered", "To-dos", "Proposed to-dos offered (logged by /todo propose)", "info"),
    ("proposals_accepted", "To-dos", "Of those, accepted", "up"),
    ("scheduled_runs_30d", "Unattended", "Scheduled runs that executed in the last 30 days", "info"),
    ("scheduled_failed_30d", "Unattended", "Of those, failed (exit code not 0)", "down"),
    ("scheduled_skipped_30d", "Unattended", "Scheduled invocations skipped (paused, capped, already running)", "info"),
    ("todo_drafts_30d", "Unattended", "To-do drafts written in the last 30 days", "info"),
]
NA = None


def p(*parts):
    return os.path.join(ROOT, *parts)


def parse_day(text):
    try:
        return datetime.date.fromisoformat((text or "").strip()[:10])
    except ValueError:
        return None


def read_csv(path):
    """Rows as dicts, or None if the file is missing or empty."""
    if not os.path.isfile(path):
        return None
    try:
        with open(path, newline="", encoding="utf-8", errors="replace") as handle:
            rows = list(csv.DictReader(handle))
    except OSError:
        return None
    return rows


def open_status(status):
    status = (status or "").strip().lower()
    return not any(word in status for word in CLOSED_WORDS)


def within(day, today, days):
    return day is not None and 0 <= (today - day).days <= days


def compute(today):
    m = {key: NA for key, *_ in METRICS}

    commitments = read_csv(p("registers", "commitments.csv"))
    if commitments is not None:
        m["commitments_overdue"] = sum(
            1 for r in commitments
            if open_status(r.get("status")) and (parse_day(r.get("due_date")) or today) < today)

    todos = read_csv(p("registers", "todos.csv"))
    if todos is not None:
        is_open = [r for r in todos if (r.get("status") or "") in ("open", "in_progress", "blocked")]
        m["todos_open"] = len(is_open)
        m["todos_overdue"] = sum(1 for r in is_open if (parse_day(r.get("due_date")) or today) < today)
        m["todos_blocked"] = sum(1 for r in todos if r.get("status") == "blocked")
        ages = [(today - d).days for d in (parse_day(r.get("created")) for r in is_open) if d]
        m["todos_median_age"] = int(statistics.median(ages)) if ages else 0
        m["todos_done_30d"] = sum(1 for r in todos if r.get("status") == "done"
                                  and within(parse_day(r.get("last_updated")), today, 30))
        m["todos_dropped_30d"] = sum(1 for r in todos if r.get("status") == "dropped"
                                     and within(parse_day(r.get("last_updated")), today, 30))

    proposals = read_csv(p("logs", "todo-proposals.csv"))
    if proposals is not None:
        def total(column):
            return sum(int(r[column]) for r in proposals
                       if (r.get(column) or "").isdigit() and within(parse_day(r.get("date")), today, 30))
        m["proposals_offered"], m["proposals_accepted"] = total("offered"), total("accepted")

    initiatives = read_csv(p("registers", "initiatives.csv"))
    if initiatives is not None and initiatives and "last_updated" in initiatives[0] and "stage" in initiatives[0]:
        m["initiatives_stale"] = sum(
            1 for r in initiatives
            if (r.get("stage") or "").strip().lower() not in INACTIVE_STAGES
            and parse_day(r.get("last_updated")) is not None
            and (today - parse_day(r.get("last_updated"))).days >= STALE_INITIATIVE_DAYS)
        if "related_decisions" in initiatives[0]:
            m["stage_without_decision"] = sum(
                1 for r in initiatives
                if (r.get("stage") or "").strip().lower() in FINAL_STAGES and not (r.get("related_decisions") or "").strip())

    decisions = read_csv(p("registers", "decisions.csv"))
    if decisions is not None:
        recent = [r for r in decisions if within(parse_day(r.get("date")), today, 30)]
        m["decisions_30d"] = len(recent)
        m["decisions_no_source_30d"] = sum(1 for r in recent if not (r.get("source_link") or "").strip())
        m["decisions_no_owner_30d"] = sum(1 for r in recent if not (r.get("made_by") or "").strip())
        reversed_ids = set()
        for r in decisions:
            text = (r.get("decision") or "").lower()
            if any(word in text for word in ("supersede", "reverse", "replaces", "overrule", "overrides")):
                for earlier in decisions:
                    eid = (earlier.get("id") or "").strip()
                    d_new, d_old = parse_day(r.get("date")), parse_day(earlier.get("date"))
                    if eid and eid != (r.get("id") or "").strip() and eid.lower() in text and d_new and d_old \
                            and 0 <= (d_new - d_old).days <= REVERSAL_WINDOW_DAYS:
                        reversed_ids.add(eid)
        m["decisions_reversed"] = len(reversed_ids)

    log = read_csv(p("logs", "run-log.csv"))
    if log is not None:
        stamped = [(parse_day(r.get("timestamp")), (r.get("workflow") or "").strip().lstrip("/"), r) for r in log]
        recent = [x for x in stamped if x[0] and within(x[0], today, 30)]
        m["runs_30d"] = len(recent)
        m["blocked_runs"] = sum(1 for day, _, r in recent
                                if (r.get("success") or "").lower() == "blocked" or "BLOCKED" in (r.get("note") or ""))
        last_seen, repeats = {}, 0
        for day, name, _ in sorted((x for x in stamped if x[0]), key=lambda x: x[0]):
            if name in CADENCE_WORKFLOWS or name.endswith(":unspecified"):
                continue
            if name in last_seen and 0 <= (day - last_seen[name]).days <= REDO_WINDOW_DAYS and within(day, today, 30):
                repeats += 1
            last_seen[name] = day
        m["repeat_runs_30d"] = repeats

    scheduled = read_csv(p("logs", "scheduled-runs.csv"))
    if scheduled is not None:
        recent_sched = [r for r in scheduled if within(parse_day(r.get("date")), today, 30)]
        m["scheduled_runs_30d"] = sum(1 for r in recent_sched if r.get("status") in ("ok", "failed"))
        m["scheduled_failed_30d"] = sum(1 for r in recent_sched if r.get("status") == "failed")
        m["scheduled_skipped_30d"] = sum(1 for r in recent_sched if (r.get("status") or "").startswith("skipped")
                                         and r.get("status") != "skipped-nothing-new")
    if os.path.isdir(p("outputs", "todo-drafts")):
        m["todo_drafts_30d"] = sum(
            1 for f in glob.glob(p("outputs", "todo-drafts", "TODO-*.md"))
            if within(datetime.date.fromtimestamp(os.path.getmtime(f)), today, 30))

    inbox = [f for f in glob.glob(p("inbox", "**", "*"), recursive=True) if os.path.isfile(f)]
    if os.path.isdir(p("inbox")):
        m["inbox_old"] = sum(1 for f in inbox if (today - datetime.date.fromtimestamp(os.path.getmtime(f))).days > 3)

    hashes = read_csv(p("state", "output-hashes.csv"))
    if hashes is not None:
        tracked = edited = 0
        for r in hashes:
            target = p(r.get("path", ""))
            if not r.get("path") or not os.path.isfile(target):
                continue
            tracked += 1
            with open(target, "rb") as handle:
                if hashlib.sha256(handle.read()).hexdigest() != r.get("sha256"):
                    edited += 1
        m["outputs_tracked"], m["outputs_edited"] = tracked, edited

    context = [p("CLAUDE.md")] + glob.glob(p("reference", "context", "*"))
    m["context_files_updated_30d"] = sum(
        1 for f in context if os.path.isfile(f)
        and within(datetime.date.fromtimestamp(os.path.getmtime(f)), today, 30))
    return m


def read_history():
    return read_csv(p(HISTORY)) or []


def write_history(rows):
    path = p(HISTORY)
    directory = os.path.dirname(path)
    if os.path.islink(directory) or os.path.islink(path):
        raise SystemExit("state/ or its history file is a symlink; refusing to write")
    os.makedirs(directory, exist_ok=True)
    fields = ["date"] + [key for key, *_ in METRICS]
    handle = tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=directory, delete=False, suffix=".tmp")
    with handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})
    os.replace(handle.name, path)


def snapshot(today, metrics):
    rows = [r for r in read_history() if r.get("date") != today.isoformat()]
    rows.append({"date": today.isoformat(), **{k: ("" if v is NA else v) for k, v in metrics.items()}})
    rows.sort(key=lambda r: r["date"])
    write_history(rows)


def previous_snapshot(today):
    earlier = [r for r in read_history() if parse_day(r.get("date")) and parse_day(r["date"]) < today]
    return earlier[-1] if earlier else None


def baseline_state(today):
    history = [parse_day(r.get("date")) for r in read_history() if parse_day(r.get("date"))]
    if not history:
        return None, False
    start = min(history)
    return start, (today - start).days < BASELINE_DAYS


def change_text(key, direction, now, before):
    if before is None or now is NA:
        return "—"
    try:
        old = float(before.get(key, ""))
    except (TypeError, ValueError):
        return "—"
    delta = now - old
    if delta == 0:
        return "no change"
    arrow = f"{'+' if delta > 0 else ''}{int(delta) if float(delta).is_integer() else round(delta, 1)}"
    if direction == "info":
        return arrow
    good = (delta < 0) == (direction == "down")
    return f"{arrow} ({'better' if good else 'worse'})"


def report(today, metrics):
    start, provisional = baseline_state(today)
    before = previous_snapshot(today)
    lines = [f"# Workbench metrics, as of {today.isoformat()}", ""]
    if start is None:
        lines += ["No snapshot recorded yet. Run with --snapshot to start the baseline "
                  f"({BASELINE_DAYS} days). Nothing below can be compared to an earlier month yet.", ""]
    elif provisional:
        lines += [f"Baseline period: started {start.isoformat()}, ends "
                  f"{(start + datetime.timedelta(days=BASELINE_DAYS)).isoformat()}. "
                  "Changes shown are provisional; do not treat them as a trend.", ""]
    else:
        lines += [f"Baseline captured {start.isoformat()}. Change is against the previous snapshot"
                  + (f" ({before['date']})." if before else "."), ""]
    group = None
    for key, grp, label, direction in METRICS:
        if grp != group:
            if group is not None:
                lines.append("")
            lines += [f"## {grp}", "", "| Metric | Now | Change |", "|---|---|---|"]
            group = grp
        now = metrics[key]
        lines.append(f"| {label} | {'n/a' if now is NA else now} | {change_text(key, direction, now, before)} |")
    lines += ["", "n/a means the source file or column does not exist yet, not zero. Counts are heuristics for "
              "one person's own use; they show a trend, not a cause and not a score."]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--today")
    args = parser.parse_args(argv)
    today = parse_day(args.today) if args.today else datetime.date.today()
    if today is None:
        print("--today must look like 2026-10-02", file=sys.stderr)
        return 1
    metrics = compute(today)
    text_out = report(today, metrics)
    if args.snapshot:
        snapshot(today, metrics)
    if args.json:
        print(json.dumps({"as_of": today.isoformat(), "metrics": metrics}, indent=2))
    else:
        print(text_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
