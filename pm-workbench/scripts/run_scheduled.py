#!/usr/bin/env python3
"""run_scheduled.py — the one entry point for unattended runs (cron, launchd, Task Scheduler). Standard library only.

An OS scheduler calls this instead of calling `claude` directly, so every unattended run gets the same
guardrails (Plan D):
  * state/PAUSE exists            -> nothing runs; logged as skipped-paused
  * more than --max-runs-per-day  -> nothing runs; logged as skipped-cap
  * the previous run still holds state/.scheduled.lock -> skipped-running (stale after 2 hours)
  * --if-new-inbox and nothing new in inbox/ since the last successful run -> skipped-nothing-new
  * --once-per-day and this task already logged `ok` today -> skipped-done-today (lets the installer add
    catch-up slots without running the job twice)
  * the model gateway in ANTHROPIC_BASE_URL (environment, else ~/.claude/settings.json "env") refuses a TCP
    connection after three tries -> skipped-offline (a laptop waking for maintenance often has no network yet;
    the next slot retries)
  * otherwise it runs `claude -p` in this folder with `--permission-mode dontAsk` (anything that would need
    an answer is denied; Claude Code 2.1+ has no `--permission-prompts` flag), an append-system-prompt that
    says nobody can answer (CLAUDE.md rule 22), and a narrow allow-list. A non-zero exit appends a BLOCKED
    row to logs/run-log.csv so tomorrow's brief shows it. Each prompt gets --timeout-minutes (default 45) of
    awake time; a run past that is killed, logged failed with exit 124, and BLOCKED, so a hung run cannot hold
    the lock and make the next job skip.
Script tasks (SCRIPT_TASKS) run a kit script directly: no `claude`, no model, no permission questions. They obey
state/PAUSE, take their own lock (state/.scheduled-script.lock, so a long model run never makes a weekly
measurement skip its slot), do not count toward --max-runs-per-day, and save their output to
state/scheduled/<task>.txt. A failure is logged and BLOCKED the same way.
Every invocation, run or skipped, is one row in logs/scheduled-runs.csv.

  python3 scripts/run_scheduled.py daily-brief
  python3 scripts/run_scheduled.py inbox-watch --if-new-inbox
  python3 scripts/run_scheduled.py metrics-snapshot
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
import socket
import subprocess
import sys
import time
import urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_STALE_SECONDS = 2 * 60 * 60
SCHEDULED_LOG = os.path.join("logs", "scheduled-runs.csv")
RUN_LOG = os.path.join("logs", "run-log.csv")
SEEN = os.path.join("state", "inbox-seen.json")
PAUSE = os.path.join("state", "PAUSE")
LOCK = os.path.join("state", ".scheduled.lock")
SCRIPT_LOCK = os.path.join("state", ".scheduled-script.lock")
SCRIPT_OUTPUT = os.path.join("state", "scheduled")

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
# task name -> kit script and its arguments, run with this python, no model (Plan E schedules)
SCRIPT_TASKS = {
    "metrics-snapshot": ["scripts/workbench_metrics.py", "--snapshot"],
    "workbench-health": ["scripts/workbench_health.py"],
    "decisions-integrity": ["scripts/register_view.py", "integrity", "decisions"],
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


def notify_failure(task, note):
    """Show a macOS notification. A failed schedule should reach the PM the same day. Never raises."""
    text = " ".join(f"{task} failed: {note}".split())
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    script = f'display notification "{text}" with title "PM workbench"'
    try:
        subprocess.run(
            ["/usr/bin/osascript", "-e", script],
            check=False,
            timeout=10,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def log_blocked(task, note):
    """Make a failed run visible in tomorrow's brief (it reads BLOCKED lines in run-log.csv)."""
    notify_failure(task, note)
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


def todays_rows():
    path = p(SCHEDULED_LOG)
    if not os.path.isfile(path):
        return []
    today = now().date().isoformat()
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        return [r for r in csv.DictReader(handle) if r.get("date") == today]


def runs_today(task_filter=None):
    return sum(1 for r in todays_rows()
               if r.get("status") in ("ok", "failed") and r.get("task") not in SCRIPT_TASKS)


def done_today(task):
    return any(r.get("task") == task and r.get("status") == "ok" for r in todays_rows())


def gateway_address():
    """(host, port) of ANTHROPIC_BASE_URL from the environment or ~/.claude/settings.json, else None."""
    url = os.environ.get("ANTHROPIC_BASE_URL")
    if not url:
        try:
            with open(os.path.join(os.path.expanduser("~"), ".claude", "settings.json"), encoding="utf-8") as handle:
                url = (json.load(handle).get("env") or {}).get("ANTHROPIC_BASE_URL")
        except (OSError, ValueError, AttributeError):
            url = None
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if not parsed.hostname:
        return None
    return parsed.hostname, parsed.port or (80 if parsed.scheme == "http" else 443)


def gateway_reachable(address, tries=3, wait=None):
    wait = float(os.environ.get("PM_SCHED_PROBE_WAIT", "20")) if wait is None else wait
    for attempt in range(tries):
        try:
            socket.create_connection(address, timeout=5).close()
            return True
        except OSError:
            if attempt < tries - 1:
                time.sleep(wait)
    return False


def failure_note(prompt, code, output):
    tail = " ".join((output or "").strip().splitlines()[-2:])[:200]
    if "ExceededBudget" in (output or ""):
        return (f"{prompt} exited {code}: the model gateway says the account is over its spend budget. "
                f"Ask the gateway admin to reset or raise it. {tail}")
    return f"{prompt} exited {code}. {tail}"


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


def take_lock(lock=LOCK):
    path = p(lock)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        if time.time() - os.path.getmtime(path) < LOCK_STALE_SECONDS:
            return False
        os.remove(path)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))
    return True


def drop_lock(lock=LOCK):
    try:
        os.remove(p(lock))
    except OSError:
        pass


def build_command(claude, prompt):
    # dontAsk: unattended runs must not hang on permission prompts. Claude Code 2.1+
    # rejects the older --permission-prompts flag (unknown option).
    return [claude, "-p", prompt, "--permission-mode", "dontAsk",
            "--allowedTools", ",".join(ALLOWED_TOOLS), "--append-system-prompt", UNATTENDED_NOTE]


def run_script_task(task, dry_run=False):
    command = [sys.executable, *SCRIPT_TASKS[task]]
    if dry_run:
        print(" ".join(command))
        return 0
    os.chdir(ROOT)
    if os.path.exists(p(PAUSE)):
        log_row(task, "skipped-paused", note="state/PAUSE exists")
        return 0
    if not take_lock(SCRIPT_LOCK):
        log_row(task, "skipped-running", note="previous script run still holds the lock")
        return 0
    started = time.time()
    try:
        result = subprocess.run(command, cwd=ROOT, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, check=False)
        out_dir = p(SCRIPT_OUTPUT)
        if not os.path.islink(os.path.dirname(out_dir)):
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, f"{task}.txt"), "w", encoding="utf-8") as handle:
                handle.write(result.stdout or "")
        if result.returncode:
            tail = " ".join((result.stdout or "").strip().splitlines()[-2:])[:200]
            log_blocked(task, f"{' '.join(SCRIPT_TASKS[task])} exited {result.returncode}. {tail}")
    finally:
        drop_lock(SCRIPT_LOCK)
    log_row(task, "ok" if not result.returncode else "failed", result.returncode, int(time.time() - started))
    return 1 if result.returncode else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", nargs="?")
    parser.add_argument("--if-new-inbox", action="store_true", help="run only if inbox/ has a new or changed file")
    parser.add_argument("--max-runs-per-day", type=int, default=5)
    parser.add_argument("--once-per-day", action="store_true", help="skip if this task already ran ok today")
    parser.add_argument("--timeout-minutes", type=float, default=45, help="per prompt; 0 means no limit")
    parser.add_argument("--no-probe", action="store_true", help="do not check the model gateway first")
    parser.add_argument("--claude", default=os.environ.get("CLAUDE_BIN") or "claude")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    if args.list or not args.task:
        for name, prompts in TASKS.items():
            print(f"{name:22} {' ; '.join(prompts)}")
        for name, command in SCRIPT_TASKS.items():
            print(f"{name:22} script: {' '.join(command)}")
        return 0 if args.list else 2
    if args.task in SCRIPT_TASKS:
        return run_script_task(args.task, args.dry_run)
    if args.task not in TASKS:
        print(f"Unknown task '{args.task}'. Known: {', '.join([*TASKS, *SCRIPT_TASKS])}", file=sys.stderr)
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
    if args.once_per_day and done_today(args.task):
        log_row(args.task, "skipped-done-today")
        return 0
    if args.if_new_inbox and not inbox_has_new():
        log_row(args.task, "skipped-nothing-new")
        return 0
    if shutil.which(args.claude) is None and not os.path.isfile(args.claude):
        log_row(args.task, "failed", 127, 0, "claude not found on PATH")
        log_blocked(args.task, "claude command not found when the scheduler ran")
        return 1
    address = None if args.no_probe else gateway_address()
    if address and not gateway_reachable(address):
        log_row(args.task, "skipped-offline", note=f"model gateway {address[0]}:{address[1]} not reachable")
        return 0
    if not take_lock():
        log_row(args.task, "skipped-running", note="previous run still holds the lock")
        return 0
    started, worst = time.time(), 0
    timeout = args.timeout_minutes * 60 if args.timeout_minutes > 0 else None
    try:
        for prompt in prompts:
            try:
                result = subprocess.run(build_command(args.claude, prompt), cwd=ROOT, text=True, timeout=timeout,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
            except subprocess.TimeoutExpired:
                worst = 124
                log_blocked(args.task, f"{prompt} ran past {args.timeout_minutes:g} minutes and was stopped")
                break
            worst = worst or result.returncode
            if result.returncode:
                log_blocked(args.task, failure_note(prompt, result.returncode, result.stdout))
                break
        if not worst and args.if_new_inbox:
            remember_inbox()
    finally:
        drop_lock()
    log_row(args.task, "ok" if not worst else "failed", worst, int(time.time() - started))
    return 1 if worst else 0


if __name__ == "__main__":
    sys.exit(main())
