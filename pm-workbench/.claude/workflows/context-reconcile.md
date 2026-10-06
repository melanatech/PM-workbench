---
description: Backfill fan-out across living surfaces from already-processed archive/outputs — fix gaps left when capture only wrote registers
argument-hint: [optional focus: todos|questions|competitive|initiatives| or a date window / topic]
---

Execution mode: **standard** (bounded sources; not Deep). Override inline if I say so.

Backfill: $ARGUMENTS

**Purpose.** `/capture process-inbox` and meeting-closeout process a file once. Older runs often wrote registers (or a daily digest) and skipped living surfaces. This workflow **re-reads already-processed material** and applies `.claude/workflows/_fan-out.md` so context is propagated everywhere it should have landed — without re-inventing evidence or auto-adding to-dos.

This is **not** `/sync jira-reconcile` (board) and **not** `/sync ripple-check` (one new change). Use this when: todos feel wrong, open questions are scattered, competitive/research insights never hit INIT notes, or fan-out was added after a big archive week.

## Step 0 — scope

1. Default window: last **30 days** of `archive/` + related `outputs/daily/`, `outputs/monthly/`, `reference/user-research/`, `learning/`, plus always-read living files and registers below.
2. If `$ARGUMENTS` names a focus (`todos`, `questions`, `competitive`, `initiatives`, a topic, or `since YYYY-MM-DD`), narrow to that. If it says `full`, widen but still cap (step 1).
3. Print one line: window + focus + approx file count you will open (max **12** source files in Standard; if more are relevant, list excluded and offer to widen — never silently fan out across the whole archive).

## Step 1 — load the system of record (always)

Read (relevant rows / recent sections only):
- `registers/todos.csv`, `registers/initiatives.csv`, `registers/commitments.csv`, `registers/risks.csv`, `registers/decisions.csv`
- Recent `registers/evidence.csv` (last 60–90 days or topic filter)
- `reference/context/assumptions-and-open-questions.md` (full Open section)
- `reference/context/current-priorities.md`
- `outputs/todo-proposals/` (latest files)
- `outputs/monthly/competitive-log.md` if present; list `state/competitive/` if present

## Step 2 — sample sources for gaps

From the window, pick up to 12 highest-signal files (prefer customer calls, roadmap/board exports, research summaries, competitive log, strategy baselines). Prefer `reference/user-research/` and `learning/` summaries over re-reading raw binaries when a summary exists.

For each source, ask: what durable claims exist here that are **missing** from the surfaces in `_fan-out.md`?

## Step 3 — reconcile (Tier 1 writes in this run)

Apply `_fan-out.md`. Specifically:

1. **Open questions** — every unresolved question found in sources or digests that is not already under `## Open` in `assumptions-and-open-questions.md` → append (dedupe). Fix hygiene: bullets under `## Resolved` that still say `open` → either move to Open or mark `resolved YYYY-MM-DD` with evidence.
2. **Initiatives** — append cross-cutting notes / EV links to **every** INIT- a theme touches (not only the primary). Seed only when PM-scoped product work is clearly named and missing (same rules as meeting-closeout).
3. **Learning / user-research** — durable product or research facts missing from `learning/` or lacking a research summary → write/update with dated source paths.
4. **Competitive** — vendor claims in archive/research that are not in `competitive-log.md` / `state/competitive/` → append a dated section or capture stub labeled with access path (e.g. "from archive research, not live WebFetch").
5. **Priorities** — only if sources clearly change this week's top 3 / leadership pressure / dated milestones; do not invent.
6. **To-do proposals (never silent `/todo` add)** — rebuild or append `outputs/todo-proposals/[today]-context-reconcile.md`:
   - Candidates from: open assumptions/questions that imply *my* action, open COM- I own or chase, INIT notes that imply follow-ups, competitive/strategy gaps that need a verify step
   - Mark each: `new` / `already TODO-nnn` / `already in proposals` / `skip (not mine)`
   - Header: `QUEUED — nothing added to registers/todos.csv`
7. **Todos hygiene report** (read-only on `todos.csv` unless I approved changes): list open TODO-nnn that look stale, duplicate of a proposal, or contradicted by a resolved question. Propose `/todo drop` / `/todo update` / accept-from-proposals as a **PROPOSALS** block — do not edit `todos.csv` status/priority/dates without Tier 3 approval. Adding brand-new todos still goes through `/todo propose` accept.

Do **not** re-append duplicate evidence rows. Link existing `EV-nnn` instead.

## Step 4 — write the reconcile report

Create [`outputs/daily/[today]-context-reconcile.md`](outputs/daily/) with:
- Scope (window, focus, files included / excluded)
- Gaps found → surfaces updated (paths + row ids)
- Open questions added/resolved (count)
- Todo proposal path + counts (`new` / `already tracked` / `skip`)
- Todo hygiene proposals awaiting approval
- Surfaces updated / N/A / Cross-initiative block from `_fan-out.md`

Show the report path (rule 20). One line on context used/excluded if you chose among many sources (rule 18).

## Step 5 — stop conditions

- If archive is empty / nothing in window: say so and stop.
- If usage is tight: finish with proposals + open-questions + todo-proposals only; label other surfaces incomplete.
- Unattended: same Tier 1 writes allowed; Tier 3 todo edits → PROPOSALS only; never send/contact.
