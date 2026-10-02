Workbench check, for a session I left open. This runs the same safe work the scheduled routines do, while I can still answer questions.

1. If `state/PAUSE` exists, say "Paused" in one line and do nothing else this round.
2. Run `python3 scripts/run_scheduled.py --list` only if I ask what is available. Otherwise look at `inbox/`: if any file is new or changed since `state/inbox-seen.json` was written, run `/capture process-inbox`, then `/todo propose queue`. If a skill cannot be run from here, read `.claude/workflows/_protocol.md` and follow it for the same workflow.
3. Run `/todo sweep` once a day, in the morning (check `outputs/todo-drafts/` for today's sweep file first).
4. If a step needs an answer from me (CLAUDE.md rule 12), ask it now, in one batch, because I am here. If I have not answered by the next round, treat the run as unattended: finish what you can, label the gap, append `BLOCKED:` to `logs/run-log.csv`.
5. End each round with one line: what ran, what it produced, what is waiting for me. If nothing changed, say "Nothing new." and stop.

Never send, post or submit anything. Never use Deep mode. Never change a to-do's status or an owner or date from here.
