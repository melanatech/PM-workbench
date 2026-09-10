---
description: "How the workbench itself is doing: which workflows you use, which fail or never run, blocked scheduled runs, register growth, unfilled setup"
model: haiku
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

The system needs its own product management. Run `python3 scripts/workbench_health.py` and use ONLY its numbers — never estimate usage, counts, or dates yourself (the script counts; you interpret).

Then, in under 200 words, tell me:
1. **What I actually use** — the 3–5 workflows with the most runs, and whether the daily loop (`/quick-close`, `/meeting-closeout`, `/weekly-update`, `/jira-reconcile`) is being used at all.
2. **What's broken or stuck** — failed runs, `BLOCKED:` scheduled runs (each is a decision I owe), inbox files older than 3 days, stub scripts a used workflow depends on.
3. **What's dead weight** — commands never run. If a command has never run after 4+ weeks of logged use, propose setting it to `"name-only"` or `"off"` in `skillOverrides` (see `settings.core.json`) — propose, don't change.
4. **One tuning suggestion** grounded in the log, and the BACKLOG item it maps to (or a new BACKLOG line to add).

Save the script's raw output to `outputs/monthly/[date]-workbench-health.md` and show me the file. Do not edit `settings.json`, `CLAUDE.md`, or any command from here.
