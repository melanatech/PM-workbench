# SCHEDULING.md — unattended runs, without a terminal, on macOS or Windows

Claude Code Desktop has a built-in scheduler: **Routines → New routine → Local**. A local routine runs on your machine, in this folder, with your files and your logged-in browser, on a schedule you pick in a form. No cron, no crontab, no admin approval, and it works the same on macOS and Windows. (Cloud routines also exist; they run on Anthropic's servers without your files, so they are the wrong tool for this workbench.)

## Why this and not cron
- One form instead of a crontab paste; a **Run now** button; a history of every run and every skipped run with the reason.
- Missed runs catch up: if your laptop was asleep at 7:15, the task runs once when it wakes (most recent missed slot only).
- Per-task permission mode, and the rules in `.claude/settings.json` still apply — so the browser deny list holds in scheduled runs exactly as in interactive ones.
- Prompts you can read: each task is stored as `~/.claude/scheduled-tasks/<name>/SKILL.md`.

## Set up the schedule (one form per task, ~2 minutes each)
In the Desktop app: **Routines → New routine → Local**, folder = this workbench. Suggested set — each instruction is one line:

| Name | Schedule | Instructions |
|---|---|---|
| daily-brief | Weekdays 7:30 | `/daily-brief` |
| process-inbox | Weekdays 18:00 | `/process-inbox` |
| discovery-delta | Weekly, Tue 7:15 | `/discovery what's new since the last run` |
| jira-reconcile | Weekly, Wed 7:15 | `/jira-reconcile` |
| weekly-update-draft | Weekly, Thu 15:00 | `/weekly-update` (drafts for Friday review — never the hour before) |
| okr-refresh | Weekly, Fri 7:15 | `/okr-refresh` |
| competitive-scan | monthly — ask Claude: "schedule /competitive-scan on the 1st at 8am" | `/competitive-scan` |

You can also just say it in any session: *"set up a local routine that runs /daily-brief every weekday at 7:30 in this folder."*

**First run of each task:** click **Run now**, watch the permission prompts, choose *always allow* for the reads and local writes it needs. Future runs then go unattended. Review or revoke those approvals on the task's detail page.

## What happens when a scheduled run needs you
None of these commands can ask a question in an unattended run. CLAUDE.md rule 22 governs: the run finishes what it can, labels the gap, logs `BLOCKED: …` to `logs/run-log.csv`, and stops. `/daily-brief` turns those lines into your morning decision list, and `/workbench-health` counts them. Check the run log the first week — a silent schedule is the one to distrust.

A note on philosophy: the brief is the schedule's front door. The other tasks do read-and-summarize work unattended — fine, because they only write to local registers and outputs. Anything requiring a decision surfaces in the brief for YOU to trigger. Schedules trigger decision points; you trigger work.

## The two preconditions (honest section)
1. **The Desktop app open and the laptop awake at trigger time.** Schedule inside working hours, and turn on **Keep computer awake** in the app's settings (Desktop app → General). A closed lid still sleeps.
2. **Your browser signed in**, for the tasks that read pages (discovery, Jira, OKR). Make it part of the morning reflex. `/weekly-update`, `/process-inbox`, and `/competitive-scan` don't need the browser and succeed regardless.

A run that hits a login page reports exactly that in its log (standing rule: fail loud, never fabricate). Re-auth, click Run now, move on.

## Rollout rule
Manual for 2–3 cycles per command → tune URLs, channels, tone → schedule only what's boringly reliable. A scheduled task you have to babysit is worse than a manual one, because you stop checking it.

## If you'd rather use cron anyway (macOS/Linux only)
`claude -p "/command"` from a crontab works and the same `settings.json` rules apply. Paste, fixing the path:
```
30 7 * * 1-5 cd "$HOME/pm-workbench" && claude -p "/daily-brief" >> logs/brief.log 2>&1
```
You lose the run history, the catch-up behavior, and Windows. Not recommended unless the Desktop app isn't an option.
