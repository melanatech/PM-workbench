#!/usr/bin/env python3
"""run_scheduled.py — the one entry point for unattended runs (cron, launchd, Task Scheduler). Standard library only.

An OS scheduler calls this instead of calling `claude` directly, so every unattended run gets the same
guardrails (Plan D):
  * state/PAUSE exists            -> nothing runs; logged as skipped-paused
  * more than --max-runs-per-day  -> nothing runs; logged as skipped-cap
  * the previous run still holds state/.scheduled.lock -> skipped-running (stale after 2 hours)
  * --if-new-inbox and nothing new in inbox/ since the last successful run -> skipped-nothing-new
  * otherwise it runs `claude -p` in this folder with no permission prompts (anything that would need an
    answer is denied), an append-system-prompt that says nobody can answer (CLAUDE.md rule 22), and a
    narrow allow-list. A non-zero exit appends a BLOCKED row to logs/run-log.csv so tomorrow's brief shows it.
Every invocation, run or skipped, is one row in logs/scheduled-runs.csv.

  python3 scripts/run_scheduled.py daily-brief
  python3 scripts/run_scheduled.py inbox-watch --if-new-inbox
  python3 scripts/run_scheduled.py daily-brief --dry-run        # print the command, run nothing, log nothing
  python3 scripts/run_scheduled.py --list

Deep-mode workflows (prd-package, strategy-refresh, experiment-package) are deliberately not in TASKS:
unattended runs use Fast or Standard mode only.
"""
import argparse
import csv
import datetime
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_STALE_SECONDS = 2 * 60 * 60
SCHEDULED_LOG = os.path.join("logs", "scheduled-runs.csv")
RUN_LOG = os.path.join("logs", "run-log.csv")
SEEN = os.path.join("state", "inbox-seen.json")
PAUSE = os.path.join("state", "PAUSE")
LOCK = os.path.join("state", ".scheduled.lock")

# task name -> list of prompts, run in order inside this one invocation
TASKS = {
    "daily-brief": ["/brief daily-brief"],
    "process-inbox": ["/capture process-inbox"],
    "inbox-watch": ["/capture process-inbox", "/todo propose queue"],
    "todo-sweep": ["/todo sweep"],
    "weekly-update-draft": ["/report weekly-update"],
    "okr-refresh": ["/report okr-refresh"],
    "jira-reconcile": ["/sync jira-reconcile"],
    "discovery-delta": ["/discover discovery what's new since the last run"],
    "monthly-review": ["/report monthly-review"],
}
# Deliberately short. Writes, edits and `python3 scripts/*` are already allowed (and scoped to outputs/, registers/,
# state/ and logs/) by .claude/settings.json, which also applies to `claude -p`; listing a bare Write or Edit here
# would widen that scope. This list only adds what settings.json does not already allow.
ALLOWED_TOOLS = ["Read", "Glob", "Grep", "Agent", "Bash(printf *)"]
UNATTENDED_NOTE = (
    "This is an unattended scheduled run. Nobody can answer questions. Follow CLAUDE.md rule 22: finish what "
    "you can, label every gap in the output, append a BLOCKED line to logs/run-log.csv for anything you needed, "
    "and stop. Use Fast or Standard execution mode only, never Deep. Never send, post or submit anything. "
    "Read only exports and files already in the workbench; do not use the browser.")


def p(*parts):
    return os.path.join(ROOT, *parts)


def now():
    return datetime.datetime.now()


def log_row(task, status, code="", seconds="", note=""):
    path = p(SCHEDULED_LOG)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.islink(path) or os.path.islink(os.path.dirname(path)):
        return
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    stamp = now()
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if new:
            writer.writerow(["date", "time", "task", "status", "exit_code", "seconds", "note"])
        writer.writerow([stamp.date().isoformat(), stamp.strftime("%H:%M:%S"), task, status, code, seconds, note])


def log_blocked(task, note):
    """Make a failed run visible in tomorrow's brief (it reads BLOCKED lines in run-log.csv)."""
    path = p(RUN_LOG)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.islink(path):
        return
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if new:
            writer.writerow(["timestamp", "workflow", "approx_duration_min", "success", "note"])
        writer.writerow([now().isoformat(timespec="seconds"), f"scheduled:{task}", "", "blocked", f"BLOCKED: {note}"])


def runs_today(task_filter=None):
    path = p(SCHEDULED_LOG)
    if not os.path.isfile(path):
        return 0
    today = now().date().isoformat()
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        return sum(1 for r in csv.DictReader(handle)
                   if r.get("date") == today and r.get("status") in ("ok", "failed"))


def inbox_snapshot():
    found = {}
    base = p("inbox")
    for directory, names, files in os.walk(base):
        names[:] = [n for n in names if not n.startswith(".")]
        for name in files:
            if name.startswith("."):
                continue
            full = os.path.join(directory, name)
            found[os.path.relpath(full, ROOT)] = int(os.path.getmtime(full))
    return found


def inbox_has_new():
    try:
        with open(p(SEEN), encoding="utf-8") as handle:
            seen = json.load(handle)
    except (OSError, ValueError):
        seen = {}
    current = inbox_snapshot()
    return any(seen.get(path) != mtime for path, mtime in current.items())


def remember_inbox():
    path = p(SEEN)
    if os.path.islink(os.path.dirname(path)) or os.path.islink(path):
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(inbox_snapshot(), handle)


def take_lock():
    path = p(LOCK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        if time.time() - os.path.getmtime(path) < LOCK_STALE_SECONDS:
            return False
        os.remove(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    return True


def drop_lock():
    try:
        os.remove(p(LOCK))
    except OSError:
        pass


def build_command(claude, prompt):
    return [claude, "-p", prompt, "--permission-mode", "acceptEdits", "--permission-prompts", "none",
            "--allowedTools", ",".join(ALLOWED_TOOLS), "--append-system-prompt", UNATTENDED_NOTE]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", nargs="?")
    parser.add_argument("--if-new-inbox", action="store_true", help="run only if inbox/ has a new or changed file")
    parser.add_argument("--max-runs-per-day", type=int, default=5)
    parser.add_argument("--claude", default=os.environ.get("CLAUDE_BIN") or "claude")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    if args.list or not args.task:
        for name, prompts in TASKS.items():
            print(f"{name:22} {' ; '.join(prompts)}")
        return 0 if args.list else 2
    if args.task not in TASKS:
        print(f"Unknown task '{args.task}'. Known: {', '.join(TASKS)}", file=sys.stderr)
        return 2
    prompts = TASKS[args.task]
    if args.dry_run:
        for prompt in prompts:
            print(" ".join(repr(x) if " " in x else x for x in build_command(args.claude, prompt)))
        return 0
    os.chdir(ROOT)
    if os.path.exists(p(PAUSE)):
        log_row(args.task, "skipped-paused", note="state/PAUSE exists")
        return 0
    if runs_today() >= args.max_runs_per_day:
        log_row(args.task, "skipped-cap", note=f"{args.max_runs_per_day} runs already today")
        return 0
    if args.if_new_inbox and not inbox_has_new():
        log_row(args.task, "skipped-nothing-new")
        return 0
    if shutil.which(args.claude) is None and not os.path.isfile(args.claude):
        log_row(args.task, "failed", 127, 0, "claude not found on PATH")
        log_blocked(args.task, "claude command not found when the scheduler ran")
        return 1
    if not take_lock():
        log_row(args.task, "skipped-running", note="previous run still holds the lock")
        return 0
    started, worst = time.time(), 0
    try:
        for prompt in prompts:
            result = subprocess.run(build_command(args.claude, prompt), cwd=ROOT, text=True,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            worst = worst or result.returncode
            if result.returncode:
                tail = " ".join((result.stdout or "").strip().splitlines()[-2:])[:200]
                log_blocked(args.task, f"{prompt} exited {result.returncode}. {tail}")
                break
        if not worst and args.if_new_inbox:
            remember_inbox()
    finally:
        drop_lock()
    log_row(args.task, "ok" if not worst else "failed", worst, int(time.time() - started))
    return 1 if worst else 0


if __name__ == "__main__":
    sys.exit(main())
