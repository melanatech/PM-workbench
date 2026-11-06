---
description: "How the workbench itself is doing: which workflows you use, which fail or never run, blocked scheduled runs, register growth, unfilled setup"
model: haiku
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

The system needs its own product management. Run `python3 scripts/workbench_health.py` and use ONLY its numbers — never estimate usage, counts, or dates yourself (the script counts; you interpret).

Also run `python3 scripts/context_health.py --root <live>` and paste its table. That is the context-health report (missing, template-empty, stale, ok). Do not summarize a file you did not get a row for.

Also run `python3 scripts/session_usage.py --root <live> --summary` and report its **by-surface** and **by-model** lines next to those numbers. Do not add the tokens up yourself.

Surfaces, from the transcript `entrypoint` (see `scripts/transcripts.py`):

- `terminal` — interactive CLI (`entrypoint` `cli`)
- `headless` — `claude -p` and the CLI SDK (`entrypoint` `sdk-cli`)
- `panel` — VS Code / Cursor extension (`entrypoint` `claude-vscode`)

An entrypoint that is not one of those three is left as the raw value. If the summary has no `surface` column yet, say so and point at `python3 scripts/session_usage.py --root <live> --backfill-surface` instead of guessing.

Then, in under 200 words, tell me:
1. **What I actually use** — the 3–5 workflows with the most runs, and whether the daily loop (`/quick-close`, `/capture meeting-closeout`, `/report weekly-update`, `/sync jira-reconcile`) is being used at all. The run log misses runs started in plain language, so also use the named-workflow lines from `python3 scripts/usage_story.py data --root <live>` and say which source each count came from.
2. **What's broken or stuck** — failed runs, `BLOCKED:` scheduled runs (each is a decision I owe), inbox files older than 3 days, stub scripts a used workflow depends on.
3. **What's dead weight** — commands never run. If a command has never run after 4+ weeks of logged use, propose setting it to `"name-only"` or `"off"` in `skillOverrides` (see `settings.core.json`) — propose, don't change.
4. **One tuning suggestion** grounded in the log, and the BACKLOG item it maps to (or a new BACKLOG line to add).

Save the script's raw output to `outputs/monthly/[date]-workbench-health.md` and show me the file. Do not edit `settings.json`, `CLAUDE.md`, or any command from here.

## Monthly usage story

Once a month, or when I ask "what's my usage story", write `outputs/usage/[date]-story.md`. It answers: **what changed in how I work, what it produced, and what to do next.** It is not a cost report.

1. Refresh the usage rows: `python3 scripts/session_usage.py --root <live> --backfill`.
2. Run `python3 scripts/usage_story.py data --root <live>`. Use only its numbers for work mix, workflows, corrections, and outcomes.
3. Read the correction turns it lists and group them into 4–6 themes, such as missed source, template drift, or misread metric. Quote short fragments internally only.
4. Line the changes up against dated kit changes in [state/kit-changes.csv](state/kit-changes.csv). Say which changes have no after period yet.
5. **Cost, two copies.** The story in the live workspace may use the AI cost dashboard row in [reference/links.csv](reference/links.csv): displayed spend and tokens, and the date range on the page. Those figures and that URL stay in the live workspace. They are not committed to this kit. A usage story, example, or test committed to this repo uses the labeled price-table estimate and says it is an estimate. Do not commit dashboard spend, the dashboard URL, or a person-scoped link. If the live workspace has no dashboard row, ask me, and write `[NEEDS INPUT: dashboard export]` in that live story only.
6. Write the story in this order, using these headings: `Executive summary` (5–6 plain sentences), `So what` (3–4 actions), `What changed in how I use AI`, `Where the effort went: corrections`, `What it produced`, `What the kit changed in response`, `Cost`, `What we cannot claim yet`, `Next run should check`, `Sources`.
7. Run `python3 scripts/usage_story.py check --root <live> outputs/usage/[date]-story.md`. Fix every problem it reports before publishing.
8. Publish with `scripts/publish.py --formats html,docx` only if I ask.

Rules for the story:

- Lead with the change and what it means, not the method.
- Never divide total spend by files, decisions, rows, or any other output count. Most spend is not tied to one output.
- Compare weeks only with their active-day counts stated. A partial week is labeled as partial.
- Subagent results returning to the session are not my corrections. The script already separates them.
- Association, not causation, for anything lined up against a kit change.
- Do not add a separate workflow for this.

## Postmortem

In the same pass, when the health read or the usage story shows a failed job (a run I said went badly, a job I abandoned or redid, or a correction theme that kept one job from landing), write `outputs/monthly/[date]-[slug]-postmortem.md` for that job. One file per failed job. I do not draft it. It answers: **what the job was, why it failed, and what to change next.** A fictional example of the output is [fixtures/postmortem/sample-postmortem.md](fixtures/postmortem/sample-postmortem.md).

1. Use the numbers and correction turns from `usage_story.py data` that belong to the failed job. Read that job's transcripts and the artifacts it wrote. Count nothing yourself.
2. State the job and its pass bar from my asks before judging the run.
3. Write it in this order, using these headings: `Executive verdict`, `Intended job and success criteria`, `Lean progression`, `Artifact lineage and quality retention`, `What went well`, `What went wrong`, `Root causes`, `Lessons`, `Prioritized improvements (propose only)`, `Proposed next test`, `Sources and limitations`, `Review gate (calibration)`. When an earlier postmortem covers the same job, add `How the last postmortem's improvements fared` before the improvements.
4. Each root cause cites its evidence: a transcript turn, a correction theme, or an artifact path. Mark which causes I raised and which came only from the audit.
5. Run `python3 scripts/usage_story.py check-postmortem --root <live> outputs/monthly/[date]-[slug]-postmortem.md`. Fix every problem it reports.

Rules for the postmortem:

- Association, not causation, for anything lined up against a kit change, unless a transcript turn or an artifact shows the cause.
- Improvements are proposals. Change nothing in the kit, and append nothing to `logs/review-notes.csv`, until I approve.
- A postmortem that carries numbers and is shared needs a number ledger.
- Quiet month: if no job failed, say "no postmortem this month" in the reply (and in the story's `Next run should check` when there is a story). Do not invent one.
- A postmortem about real work stays in the live workspace. Only a fictional example goes in this kit.
