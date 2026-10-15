---
description: Backfill fan-out across living surfaces from already-processed archive/outputs — fix gaps left when capture only wrote registers
argument-hint: [optional focus: todos|questions|competitive|initiatives| or a date window / topic]
---

Execution mode: **standard** (bounded sources; not Deep). Override inline if I say so.

Context dependencies: soft: current-priorities, people | hard: none

Backfill: $ARGUMENTS

**Purpose.** `/capture process-inbox` and meeting-closeout process a file once. Older runs often wrote registers (or a daily digest) and skipped living surfaces. This workflow **re-reads already-processed material** and applies `.claude/workflows/_fan-out.md` so context is propagated everywhere it should have landed — without re-inventing evidence or auto-adding to-dos.

This is **not** `/sync jira-reconcile` (board) and **not** `/sync ripple-check` (one new change). Use this when: todos feel wrong, open questions are scattered, competitive/research insights never hit INIT notes, or fan-out was added after a big archive week.

## Step 0 — preflight + scope

0. `python3 scripts/context_preflight.py --root <live> --topic "context-reconcile $ARGUMENTS"` — prefer indexed analyses when backfilling product facts; append index rows for any new durable analyses this run produces. When a backfilled fact shares an initiative id or a primary source with an indexed deliverable, `python3 scripts/analysis_index.py mark-stale` (surface 13). Do not rewrite the deliverable.
0b. **Chat harvest (rule 24 backfill).** `python3 scripts/chat_harvest.py --root <live> --workspace <live> --workspace <kit>`. Classify fact-like PM turns that never reached a capture. Present promotions in one Tier 2 batch. Do not copy assistant text into durable files.
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

From the window, pick up to 12 highest-signal files (prefer customer calls, roadmap/board exports, research summaries, competitive log, strategy baselines). Prefer `reference/user-research/` and `learning/` summaries over re-reading raw binaries when a summary exists. Prefer an existing `<stem>.vision.md` over re-visioning every PNG when the vision file is fresh.

Also load `state/source-index.csv` for the window: re-check rows with `outcome=hold` or `status=open` via `python3 scripts/source_index.py match --root <live> --entities "<topics from focus>"`. Promote when a primary source now confirms; conflict → assumptions.

**If any selected source is a long strategy/deck/research pack** (multi-page PDF, large `.vision.md`, strategy memo, initiative-list sheet): **dispatch `internal-docs-reader`** with those paths + the reconcile focus before writing INIT notes. Work from its brief. Do **not** skim "for context constraints" or replace a full fan-out with a thinner vision-only summary (CLAUDE.md: no context shortchanging).

For each source (or for the reader brief): apply `_source-triage.md` if it has no source-index row yet, then ask what durable claims are **missing** from the surfaces in `_fan-out.md`.

## Step 3 — reconcile (Tier 1 writes in this run)

Apply `_source-triage.md` then `_fan-out.md`. Specifically:

1. **Open questions** — every unresolved question found in sources or digests that is not already under `## Open` in `assumptions-and-open-questions.md` → append (dedupe). Skip questions marked `parked YYYY-MM-DD` unless a new source touches them. Fix hygiene: bullets under `## Resolved` that still say `open` → either move to Open or mark `resolved YYYY-MM-DD` with evidence.
2. **Initiatives** — append cross-cutting notes / EV links to **every** INIT- a theme touches (not only the primary). Seed only when PM-scoped product work is clearly named and missing (same rules as meeting-closeout). Raise `INITIATIVE CANDIDATE` when ≥3 criteria hold; do not create silently.
3. **Learning / user-research** — durable product or research facts missing from `learning/` or lacking a research summary → write/update with dated source paths. Strategy-frame and business-process baselines go here.
4. **Competitive** — vendor claims in archive/research that are not in `competitive-log.md` / `state/competitive/` → append a dated section or capture stub labeled with access path (e.g. "from archive research, not live WebFetch").
5. **Priorities** — only if sources clearly change this week's top 3 / leadership pressure / dated milestones; **proposal only** (Tier 3); do not invent or write silently from strategy-frame.
6. **To-do proposals (never silent `/todo` add)** — rebuild or append `outputs/todo-proposals/[today]-context-reconcile.md`:
   - Candidates from: open assumptions/questions that imply *my* action, open COM- I own or chase, INIT notes that imply follow-ups, competitive/strategy gaps that need a verify step
   - Mark each: `new` / `already TODO-nnn` / `already in proposals` / `skip (not mine)`
   - Header: `QUEUED — nothing added to registers/todos.csv`
7. **Todos hygiene report** (read-only on `todos.csv` unless I approved changes): list open TODO-nnn that look stale, duplicate of a proposal, or contradicted by a resolved question. Propose `/todo drop` / `/todo update` / accept-from-proposals as a **PROPOSALS** block — do not edit `todos.csv` status/priority/dates without Tier 3 approval. Adding brand-new todos still goes through `/todo propose` accept.
8. **Held → promoted** — for each source-index `hold` that now has a confirming primary source, promote via fan-out and `source_index.py promote`.

Do **not** re-append duplicate evidence rows. Link existing `EV-nnn` instead.

## Step 4 — write the reconcile report

Create [`outputs/daily/[today]-context-reconcile.md`](outputs/daily/) with:
- Scope (window, focus, files included / excluded)
- Gaps found → surfaces updated (paths + row ids)
- Open questions added/resolved (count)
- Todo proposal path + counts (`new` / `already tracked` / `skip`)
- Todo hygiene proposals awaiting approval
- Surfaces updated / Cross-initiative block from `_fan-out.md` (no N/A list)

Show the report path (rule 20). One line on context used/excluded if you chose among many sources (rule 18).

## Step 5 — stop conditions

- If archive is empty / nothing in window: say so and stop.
- If usage is tight: finish with proposals + open-questions + todo-proposals only; label other surfaces incomplete.
- Unattended: same Tier 1 writes allowed; Tier 3 todo edits → PROPOSALS only; never send/contact.
