# SCHEDULING.md — unattended and in-session runs, from the command line

This workbench runs from the Claude Code command line (terminal or Cursor), so scheduling uses two lanes that share the same guardrails. Pick the lane by whether a session is open.

| | Lane 1: your computer's scheduler | Lane 2: `/loop` in an open session |
|---|---|---|
| Runs when | The time arrives, even with no session open (computer awake and logged in) | Only while that Claude Code session is open and idle |
| Who can answer questions | Nobody. Rule 22 applies: finish what you can, label the gap, log `BLOCKED` | You, in the session |
| Lasts | Until you remove it | Recurring loops expire after 7 days; a self-paced `/loop` is not restored on resume |
| Best for | Daily brief, inbox watch, the to-do sweep, weekly and monthly drafts | A working day: leave a session open and let it watch the inbox |
| Setup | One scheduler entry per task (below) | `/loop` once; the prompt lives in `.claude/loop.md` |

Both lanes can be on together. They don't collide: Lane 1 calls `scripts/run_scheduled.py`, which skips a run if the previous one is still going, and the loop's work is the same safe set (`/capture process-inbox`, `/todo propose queue`, `/todo sweep`).

## Guardrails (both lanes)

- **Pause switch.** Create an empty file `state/PAUSE` and nothing runs: the wrapper skips, every router stops, the loop does nothing. Delete the file to resume.
- **Caps.** The wrapper allows 5 scheduled runs a day (`--max-runs-per-day`) and `/todo sweep` drafts at most 3 to-dos per run. Fast or Standard mode only; Deep workflows are not in the task list.
- **Same approval tiers.** Tier 3 actions (scope, owner, dates, anything sent, any customer contact) never happen unattended. A run may propose them.
- **Same checks.** The register hook, the output provenance hook and `check_run.py` apply unchanged.
- **A visible trail.** Every invocation, run or skipped, is a row in `logs/scheduled-runs.csv`. A failed run also appends `BLOCKED:` to `logs/run-log.csv`, which `/brief daily-brief` lists each morning. The brief also lists drafts written overnight and any queued to-do proposals.
- **No browser.** Unattended runs read exports and files already in the workbench. They do not drive your signed-in browser.

## Lane 1: your computer's scheduler

Every entry calls the same wrapper. It checks the pause file, the daily cap and the lock, then runs `claude -p` in this folder with no permission prompts (anything that would need an answer is denied, so a run can never hang waiting for you) and the permissions already in `.claude/settings.json` (writes scoped to `outputs/`, `registers/`, `state/` and `logs/`, plus `python3 scripts/*`), with only reads, subagents and the run marker added on top.

```
python3 scripts/run_scheduled.py daily-brief
python3 scripts/run_scheduled.py inbox-watch --if-new-inbox
python3 scripts/run_scheduled.py --list          # every task name
python3 scripts/run_scheduled.py daily-brief --dry-run   # show the exact claude command, run nothing
```

Suggested set:

| Task | Schedule | Wrapper command |
|---|---|---|
| daily-brief | Weekdays 7:30 | `daily-brief` |
| inbox-watch (D3) | Hourly, 8:00–18:00 weekdays | `inbox-watch --if-new-inbox` (runs only when `inbox/` has a new or changed file, then processes it and queues to-do proposals) |
| todo-sweep (D2) | Weekdays 7:45 | `todo-sweep` (drafts help for at most 3 to-dos that are overdue or due within 2 days) |
| discovery-delta | Weekly, Tue 7:15 | `discovery-delta` |
| jira-reconcile | Weekly, Wed 7:15 | `jira-reconcile` (needs an export in `inbox/`; otherwise it logs BLOCKED) |
| weekly-update-draft | Weekly, Thu 15:00 | `weekly-update-draft` (drafts for Friday review) |
| okr-refresh | Weekly, Fri 7:15 | `okr-refresh` (needs an export; otherwise BLOCKED) |
| monthly-review | 1st of the month, 8:50 | `monthly-review` |

Pick minutes that are not :00 or :30 if exact time matters; the API is busiest then.

### macOS (launchd or cron)

cron is the shortest. Run `crontab -e` and paste, fixing the path (use the full path to `python3`, from `which python3`; cron has almost no PATH, so also set `PATH` to include the folder holding `claude`, from `which claude`):

```
PATH=/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin
27 7 * * 1-5 cd "$HOME/pm-workbench" && python3 scripts/run_scheduled.py daily-brief
12 8-18 * * 1-5 cd "$HOME/pm-workbench" && python3 scripts/run_scheduled.py inbox-watch --if-new-inbox
43 7 * * 1-5 cd "$HOME/pm-workbench" && python3 scripts/run_scheduled.py todo-sweep
```

Prefer launchd if the laptop sleeps often: a launchd calendar job whose time passed during sleep runs once at wake, where cron simply skips it. cron may also need Full Disk Access if the folder is under Documents or Desktop (System Settings, Privacy & Security). Easiest of all: keep the folder under your home directory outside those.

### Windows (Task Scheduler)

Create a Basic Task per row. Action: Start a program. Program: `python`. Arguments: `scripts\run_scheduled.py daily-brief`. Start in: your workbench folder. Tick "Run whether user is logged on or not" only if `claude` is signed in for that account; otherwise leave it as "Run only when user is logged on". Under Settings, tick "Run task as soon as possible after a scheduled start is missed" to get catch-up.

### First run of each task

Run it by hand once: `python3 scripts/run_scheduled.py daily-brief`. Check `logs/scheduled-runs.csv`, the new file in `outputs/`, and `logs/run-log.csv`. If the log says a tool was denied, add exactly that tool to `ALLOWED_TOOLS` in the script or to the allow list in `.claude/settings.json`. Then add it to the scheduler. Unverified until you do this: that `claude -p` expands the slash commands and that the router can hand work to the `workflow-runner` subagent in this mode.

### What the schedule needs from you

1. The computer awake and logged in at run time. A run missed while asleep is skipped (cron) or caught up once on wake (launchd, Task Scheduler with the catch-up option). Prompts in `run_scheduled.py` are written so a late run is still correct.
2. `claude` signed in with your normal account. Don't use `--bare`: it skips CLAUDE.md, the hooks and the commands this workbench depends on.

## Lane 2: `/loop` in an open session

In a Claude Code session started in this folder, type:

```
/loop 20m
```

A bare `/loop` with an interval runs the prompt in `.claude/loop.md` every 20 minutes: look for new inbox files and process them, queue to-do proposals, and run the daily to-do sweep once. With no interval Claude picks its own pace between one minute and one hour. Press `Esc` to stop a self-paced loop. The loop file is plain text; edit it and the next round uses the change.

Because you are in the session, the loop can ask you a question. If you don't answer by the next round it treats the run as unattended. Loops don't survive closing the terminal. For a working day, start one in the morning and let it go.

One thing to check once: the loop can only run commands Claude is allowed to invoke itself. `/todo` and `/build` are set to name-only in `.claude/settings.json`. If the loop reports it cannot run one, it falls back to following `.claude/workflows/_protocol.md` for that workflow; add the workflow to the loop file by name if you prefer.

## What happens when a run needs you

None of these runs can ask a question. CLAUDE.md rule 22 governs: the run finishes what it can, labels the gap, logs `BLOCKED: …` to `logs/run-log.csv`, and stops. `/brief daily-brief` turns those lines into your morning decision list, and `/report workbench-health` counts them. Check the logs for the first week; a silent schedule is the one to distrust.

Schedules trigger decision points; you trigger work. Overnight, the system only reads, files to registers through the hooks, and writes drafts to `outputs/`. It never sends anything.

## Rollout rule

Manual for 2–3 cycles per task, then schedule only what is boringly reliable. Start with `daily-brief` and `inbox-watch`. Add `todo-sweep` once you have read a few drafts and found them useful. A scheduled task you have to babysit is worse than a manual one, because you stop checking it.

## Cloud routines (not used here)

Claude Code also has cloud routines (`/schedule`). They run on a fresh clone of your repository, so your inbox, registers and local outputs are not there, and the minimum interval is one hour. They are the wrong tool for this workbench. Desktop-app scheduled tasks exist too, but this setup does not use the Desktop app.
