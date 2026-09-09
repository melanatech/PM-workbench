# SCHEDULING.md — unattended runs on macOS, safely

Claude Code's headless mode (`claude -p "/command"`) + macOS's built-in scheduler = real recurring automation with no Claude Desktop and no admin help.

## Why this is safe now (a fix from the earlier version)
The previous kit used `--dangerously-skip-permissions` for headless runs. That's replaced: `.claude/settings.json` pre-approves only reads, navigation, snapshots, register/output writes, and the metrics script — and **explicitly denies browser click/type/upload**. A scheduled run physically cannot send, submit, or modify anything external, even if it wanted to. Interactive sessions still prompt you live for those actions.

## The schedule
Run `crontab -e` in Terminal (yes, cron works fine on macOS) and paste, fixing the path:

```
# Discovery scan — Tue 7:15am
15 7 * * 2 cd "$HOME/PM Workbench" && claude -p "/discovery" >> logs/discovery.log 2>&1

# Jira reconcile — Wed 7:15am (before your team's board review)
15 7 * * 3 cd "$HOME/PM Workbench" && claude -p "/jira-reconcile" >> logs/jira.log 2>&1

# OKR refresh — Fri 7:15am
15 7 * * 5 cd "$HOME/PM Workbench" && claude -p "/okr-refresh" >> logs/okr.log 2>&1

# Weekly update draft — Thu 3pm (afternoon BEFORE it's due, never the hour before)
0 15 * * 4 cd "$HOME/PM Workbench" && claude -p "/weekly-update" >> logs/update.log 2>&1

# Competitive scan — 1st of month, 8am
0 8 1 * * cd "$HOME/PM Workbench" && claude -p "/competitive-scan" >> logs/competitive.log 2>&1

# Inbox processing — nightly weekdays 6pm, so captures never pile up
0 18 * * 1-5 cd "$HOME/PM Workbench" && claude -p "/process-inbox" >> logs/inbox.log 2>&1

# Morning brief — weekdays 7:30am: a digest of what changed + suggested next steps.
# This one never does work — it reports and offers choices you act on when you sit down.
30 7 * * 1-5 cd "$HOME/PM Workbench" && claude -p "/daily-brief" >> logs/brief.log 2>&1
```

A note on philosophy: the brief is the schedule's front door. The other scheduled jobs above (discovery, jira, okr) do real read-and-summarize work unattended — that's fine because they only write to local registers/outputs. But anything requiring a decision surfaces in the brief for YOU to trigger, rather than more jobs quietly acting. Schedules trigger decision points; you trigger work.

Tue discovery → Wed Jira → Thu update draft → Fri metrics mirrors the dependency chain: each day's output feeds the next.

## The two preconditions (honest section)
1. **Laptop awake at trigger time.** Schedule inside your working hours (7:15am works if you're online by then), or System Settings → Battery/Energy → prevent sleep on power during those windows.
2. **The automation Chrome profile open + logged in** — needed by discovery/Jira/OKR runs. Make launching it part of your morning routine, same reflex as opening Slack. `/weekly-update`, `/process-inbox`, and `/competitive-scan` don't need the browser and succeed regardless.

A run that hits an SSO login page reports exactly that in its log (standing rule: fail loud, never fabricate). Re-auth, re-run manually, move on — expect it occasionally; it's the cost of the no-admin route.

## Rollout rule
Manual for 2-3 cycles per command → tune URLs, channels, tone → schedule only what's boringly reliable. A scheduled task you have to babysit is worse than a manual one, because you stop checking it.
