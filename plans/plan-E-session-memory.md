# Plan E: session memory and register supersession

Status: not started. Written 2026-11-02. Build from this file in Claude Code;
work in the phases below, in order, and stop at the end of each phase for review.

## What this plan fixes

Three problems in long Claude Code sessions, plus one in the workbench itself.

1. **Forgetting inside a session.** Auto-compaction summarizes earlier turns,
   and things the user said were important get dropped. The user keeps asking
   for rework to restore them.
2. **Expensive revivals.** A prompt sent to an old, large conversation writes
   the whole context to a cold cache again.
3. **Losing the thread between sessions.** A fresh session means re-explaining,
   but old context must not be pushed into chats that have nothing to do with it.
4. **Stale workbench registers.** Registers keep citing context that was later
   corrected.

Nothing here should depend on the user remembering a command, a tag or a
prefix. The work is often not code: long sessions are frequently reviews of
documentation and code toward strategic decisions or new projects, so nothing
may assume a git repo or a codebase.

## What the repo looks like today (read before building)

Findings from reading the repo on 2026-11-02. Confirm each before relying on it.

- **The workbench is not a plugin.** It is a project-level kit: `.claude/` with
  hooks in `pm-workbench/.claude/settings.json` keyed on `$CLAUDE_PROJECT_DIR`,
  copied into a live workspace (`~/pm-live`) by
  `scripts/create_live_workspace.py`. Its hooks only run in that workspace.
  Session memory has to run in every project, so it must be installed at user
  level. That is why it is a separate module (Part 2), not part of the kit.
- **`registers/decisions.csv` has no supersession column.** Schema in
  CONNECTIONS.md: `id, date, decision, made_by, source_link, affects`, described
  as "immutable history: append; correct by a linked superseding row." The link
  can only live in the decision text. `scripts/workbench_metrics.py` finds
  reversals by text match and `reference/workbench-metrics.md` says this
  under-counts. Thirteen workflows, agents and scripts read `decisions.csv`
  (meeting-prep, weekly-update, ripple-check, return-brief, roadmap-update,
  context-reconcile, prd-context-gatherer and others), and none filters out
  superseded rows. This is the most likely cause of stale citations, but it is
  inferred from the code, not observed. Phase 0 confirms it.
- **`reference/context/assumptions-and-open-questions.md`** is living context
  with `open` / `resolved` status per bullet, maintained by meeting-closeout.
  Another possible staleness source if resolutions are missed.
- **Reusable pieces already exist:**
  - `scripts/transcripts.py` parses Claude Code JSONL transcripts, skips
    `isMeta` and `isSidechain` (subagent) records, and labels the surface
    (`cli`, `sdk-cli`, `claude-vscode`). Session memory should use the same
    parsing rules.
  - `scripts/session_usage.py` already classifies turns, including a
    `rework_correction` category, and `scripts/usage_story.py` and
    `scripts/recurring_corrections.py` report on it. **That is the success
    metric for this plan:** the share of turns that are rework corrections
    should fall.
  - `scripts/chat_harvest.py` harvests the user's own statements from
    transcripts for `/brief context-setup`. Overlaps in purpose with the
    register keeper below; keep them separate in v1 and note the overlap.
  - The workbench already calls `claude -p` with Haiku for bulk classification.
- **Known risk:** BACKLOG notes that the Cursor Agent shell proxy can block
  `claude -p` even when the Claude Code panel works. Every model call in Part 2
  runs `claude -p` from a hook, so this must be verified in the Cursor panel
  before anything else in Part 2 is built.
- **Existing hooks the new ones will run alongside** (in `~/pm-live`):
  PreToolUse on `Read|Grep|Glob` (`require_context_preflight_for_repos.py`),
  PreToolUse on `Write|Edit` (`validate_register_write.py`, which rejects
  header changes), PostToolUse checks, and Stop hooks (`check_reply_links.py`,
  `log_run.py`). User-level and project-level hooks both run.
- **Already confirmed by the user:** hooks are allowed on the work machine,
  installing code from this repo works, and third-party plugin marketplaces
  are allowed (the company runs one).

## Before Phase 0: fix the failing test on main

`test_generalization.GeneralizationTests.test_tracked_kit_does_not_name_a_company_ux_checker`
fails on `main` as of commit 74ffd8c, before any Plan E change. The test bans
the strings "the company UX checker", "company-ux-checker" and "the company UX checker" in tracked
kit files, and two lines name it:

- `pm-workbench/NEW-USER-SETUP.md` line 185 (the Impeccable row: "use UX
  Guardrails + `frontend-design` there")
- `pm-workbench/SETUP.md` line 55

Replace the name with a generic phrase (for example "your company's UX
checker, if you have one, named in `.claude/CLAUDE.local.md`"), keeping the
meaning. Do not weaken the test. The `mcp__ux_guardrails__*` allow entry in
the three settings files doesn't trip the test (underscores); leave it unless
the user wants it generalized too. Run the full suite and confirm only the
two tests that read the machine's own `~/.claude/settings.json` can still fail
on a machine whose user settings differ from the kit. Commit this on its own,
separate from Plan E work, so CI on `main` is green before Phase 1 starts.

## Phase 0: confirm before building

Report results, then stop for review.

1. **Find a real stale-register incident.** In the live workspace, look for
   decisions that a later decision reverses (rows whose text names an earlier
   `DEC-` id, or opposite decisions on the same `affects` value), and check
   whether recent outputs still cite the reversed one. Do the same for
   `assumptions-and-open-questions.md`: open bullets that a later meeting
   answered. Registers are gitignored, so this runs on the machine that has
   them. Report counts and one or two examples, without copying sensitive text
   into tracked files.
2. **Hook behavior in the Cursor panel and the terminal**, checked against the
   current hooks docs:
   - `UserPromptSubmit`: exit 2 blocks and erases the prompt and shows stderr
     to the user; stdout on exit 0 adds context.
   - `Stop` fires after each reply; a detached child process survives it.
   - `SessionStart` with source `compact` fires after manual and automatic
     compaction, and its stdout reaches context.
   - `PreToolUse` / `PostToolUse` payloads: is there a field that marks a
     subagent call, or does the transcript path differ for subagents? Phase 4
     depends on this.
3. **`claude -p --model haiku` from inside a hook**, launched from the Cursor
   panel, not only from a terminal. If the shell proxy blocks it, stop and
   report; Part 2's design changes.
4. **Plugin hooks in Cursor.** Install a throwaway plugin with one logging
   hook from a local marketplace and confirm it fires in the Cursor panel. If
   it does, Part 2 ships as a plugin; if not, as an install script.
5. **Transcript fields:** where timestamps, user text, assistant text, tool
   errors and `message.usage` live, using `transcripts.py` as the reference.
6. **Cost baseline with optimAIzr.** Run `npx optimaizr` and
   `npx optimaizr sessions` once on the work machine and save the summary
   numbers (not prompts) to the Phase 0 report: share of spend on re-reading
   context, cold-cache returns and their cost, and the costliest sessions.
   Read its SECURITY.md first; it states it runs locally and reads token
   counts and tool-call arguments, not prompts. This is the "before" picture
   the weekly review compares against. See "Relationship to optimAIzr" below.

## Part 1: register supersession in the workbench (Phase 1)

Goal: a corrected decision stops being cited, without breaking rule 7
(history registers append; nothing is deleted).

1. **Schema.** Add a `supersedes` column to `registers/decisions.csv`: empty,
   or one or more `DEC-` ids separated by `;`. Update CONNECTIONS.md (it owns
   the schemas). Rows stay append-only: the old row is never edited. A row is
   active unless a later row lists it in `supersedes`.
2. **One reader for current state.** Add `scripts/register_view.py` with
   `active decisions` (resolves supersession chains, prints active rows only,
   same columns) and `history decisions --id DEC-nnn` (the full chain, for
   "why did we decide X"). Every workflow, agent and script that reads
   `decisions.csv` for current state switches to the active view. History
   reads stay explicit. Use the list in the findings above as the checklist.
3. **Writers set the link.** meeting-closeout already compares new items with
   `decisions.csv` (step 3). When a new decision overrides an active one, it
   writes `supersedes` instead of describing the reversal in text. Same for
   experiment-analyze, return-brief, ripple-check and any other writer.
   Supersession is a Tier 1 local write when the override is explicit in the
   source, and a question in the output when it's ambiguous. Never guessed.
4. **Hook.** Extend `validate_register_write.py`: allow the one-time header
   migration, and reject a `supersedes` value that doesn't name an existing
   `DEC-` id or that points at itself.
5. **Migration.** A script proposes `supersedes` values for existing rows from
   the text patterns `workbench_metrics.py` already uses (supersede, reverse,
   replaces, overrule, overrides plus an earlier id). Output is a Tier 2
   batch for the user to approve; nothing is applied silently.
6. **Metrics.** `workbench_metrics.py` counts reversals from the column
   instead of text matching. Update `reference/workbench-metrics.md`.
7. **Open questions file.** If Phase 0 found stale open bullets, add a
   resolution check to context-reconcile. If it didn't, leave it.
8. **Out of scope unless Phase 0 shows a problem:** evidence.csv, risks,
   commitments (current-state registers already update in place with status).
8a. **Fresh start for existing registers.** A script,
   `scripts/register_reset.py --root ~/pm-live`, so the user can stop carrying
   old, possibly stale rows without breaking rule 7 (nothing is deleted).
    1. `--dry-run` by default. With `--apply`, first copy every file in
       `registers/` plus `reference/context/assumptions-and-open-questions.md`
       to `archive/registers-<YYYY-MM-DD>/`, unchanged. The archive is the
       full history; outputs and `source_link`s that cite old ids still
       resolve there.
    2. Propose a carry-forward list as one Tier 2 batch: decisions that are
       still active (after the migration in step 5, so reversed ones are
       already excluded), commitments and risks not closed, to-dos not done
       or dropped, initiatives not killed, open questions not resolved. For
       each, a one-line reason it might be stale (older than 60 days, no
       mention in recent outputs, an `affects` value with a later decision).
       The user ticks what to keep. Evidence and research-participants are
       history only and are not carried; they stay in the archive.
    3. Write new register files with the current headers (including
       `supersedes`) and only the kept rows. Ids keep their original values so
       existing references still work; new rows continue numbering from the
       highest old id, so ids never collide with the archive.
    4. Log the reset to `logs/run-log.csv` and add a dated line to
       `reference/context/current-priorities.md` saying registers were reset
       and where the archive is, so later workflows don't treat missing rows as
       never having existed (rule 16).
    5. Make the register-write hook and `/sync rotate-registers` agree with
       this: BACKLOG already notes rotation conflicts with the hook's "no lost
       rows" check. The reset runs as a script outside the hook, and the hook
       accepts a fresh file when an archive copy dated today exists. Resolve
       the rotate-registers item the same way.
    6. Tests: dry run writes nothing; apply archives byte-for-byte; kept ids
       unchanged; next id continues numbering; the hook accepts the reset and
       still rejects an ordinary write that drops rows.

   Run the reset after the Part 1 migration, not before, so the carry-forward
   list already knows which decisions were reversed. Session-memory registers
   (Part 2) start empty and need no reset.
9. **Tests** in `pm-workbench/tests/`: chain resolution (A superseded by B
   superseded by C → only C active), multi-id supersedes, hook rejection of a
   dangling id, the Lumenly fixture still scoring the same, and a check that
   no workflow reads raw `decisions.csv` for current state. CI runs
   `python3 -m unittest discover -s pm-workbench/tests`.
10. Changelog line in EVOLVING.md, BACKLOG item ticked.

## Part 2: session memory (Phases 2 to 5)

A separate module at the repo root, `session-memory/`, installed at user
level so it works in every project, in the Cursor extension and the terminal.
Packaging per Phase 0 check 4: a plugin (add `.claude-plugin/marketplace.json`
at the repo root) or an `install.py` that merges into `~/.claude/settings.json`
after backing it up, with `--uninstall`. Either way: no third-party packages,
Python standard library only, every script fails open (exits 0 on any error
or unrecognized payload), and every headless call sets
`SESSION_MEMORY_INTERNAL=1`, which makes every script exit 0 immediately.

### Relationship to optimAIzr

[optimAIzr](https://github.com/blendbunjaku/optimaizr) is an open-source local
CLI (MIT, first released September 2026) that overlaps with part of Phase 3.
Its `guard` uses Claude Code hooks to hold a message sent to a long
conversation whose cache has expired, once, with the cost; sending again goes
through. It also has a cache-countdown status line, a `/optimaizr handoff`
note, cost reports per session, and a `results` command that compares spend
before and after a change.

Use it for measurement, not as a dependency:

- **Baseline and results:** Phase 0 step 6, and the weekly review compares
  against it. Its numbers are cost per session and cold-cache rewrites; the
  `rework_correction` share from `session_usage.py` measures forgetting. Both
  are needed, because Plan E targets both.
- **Not its guard.** Its guard is deliberately soft (a resend goes through),
  and the user wants a block that needs `!force`. Running both guards means
  two hooks deciding on the same prompt. Pick ours; if the user prefers its
  guard after trying it, drop Phase 3's guard and keep the detector.
- **Not its handoff.** Session registers already hold the handoff state.
- **Optional:** its status line, which doesn't conflict with anything here.
- Its README figures (one-hour cache window, dollar amounts) are the author's.
  Calibrate thresholds from this machine's transcripts (see Testing), not
  from its README.

It is young and changing quickly. Check its current README and SECURITY.md
before running it, and pin the version used for the baseline.

### The register

One register per session, same model as Part 1: entries are appended, an
entry can be superseded by a later one, and only active entries are ever used.

- Storage: `~/.claude/session-memory/<project-slug>/<session-id>.jsonl`, one
  JSON object per entry: `id`, `section`, `text`, `date`, `turn`,
  `supersedes` (list of ids), and `dropped` (bool, set by an audit).
  Rendered to markdown only when injected. Project slug = cwd with `/`
  replaced by `-`.
- Sections: Goal and Where it stands (snapshots, rewritten, not appended);
  Decisions; Constraints; Corrections (instructions given after Claude got
  something wrong); Don't retry (approaches that failed or were rejected, with
  the reason); Open questions (removed when answered).
- `index.json` per project: session id, first and last activity, Goal line,
  and links between sessions that were picked up from one another.
- Keep the supersession resolution logic identical to `register_view.py` in
  Part 1. Share the code if packaging allows, or copy it with a test that
  asserts both behave the same on shared cases.

### Phase 2: capture and compaction restore

**Register keeper (`Stop` hook).** Returns immediately after starting a
detached worker. The worker:

1. Takes only the latest exchange: the user's last prompt (up to 4,000
   characters), Claude's reply text (up to 3,000), and tool errors in that turn
   (up to 500). It skips the model call for prompts under 20 characters unless
   they contain a correction word (no, don't, wrong, instead, stop, undo,
   actually, scratch that).
2. Sends Haiku the exchange plus all active entries, and asks for JSON
   operations: add an entry, supersede entries by id with a new one, or
   nothing. When the exchange contains a correction signal, Haiku must check
   every active entry for conflict even if it's worded differently. The newer
   statement wins.
3. Writes under a lock file and updates the index.

Haiku instructions, kept in one file so the weekly review can tune them:
record only what the user stated or explicitly accepted (Claude's
suggestions count only once accepted); keep the user's wording; supersede
rather than add a contradicting entry; recording nothing is the right answer
for most turns; the work may be strategy, research, writing or code.

**Audit every 10 captures.** One Haiku pass compares active entries with the
user's last 20 prompts and supersedes or drops entries the user has since
contradicted or moved away from. This catches changes that were implied,
never stated as corrections.

**Size cap.** If active entries pass about 1,500 words, one consolidation pass
merges overlaps with the same contradiction check.

**Compaction restore (`SessionStart`, source `compact`).** Waits up to 10
seconds for the keeper's lock, then prints a preface and the active entries:
"The conversation was just compacted. These decisions, constraints and
corrections from earlier in this session still apply and take precedence over
the summary. If one conflicts with something said more recently, the more
recent statement wins; point out the conflict in one line." Superseded and
dropped entries are never printed.

**User-level CLAUDE.md line:** session registers exist at
`~/.claude/session-memory/`; check them when asked what was decided; follow
Constraints, Corrections and Don't retry; flag a conflict between an entry
and what the user just said.

Phase 2 is done when, in both the Cursor panel and the terminal, on a
non-code session (reviewing a long document toward a decision) and a code
session: a decision, a constraint, a correction and a rejected approach each
land in the right section; small talk adds nothing; a decision reversed later
in different words, without the word "correction," ends up superseded by the
next capture or audit; and after `/compact`, Claude knows the constraint
without being told again.

### Phase 3: stale-session guard and related-work detector

One `UserPromptSubmit` script handles both, so two hooks never race.

**Guard.** The expensive case is a conversation idle past the cache window
and large. Age alone doesn't matter.

1. Exit 0 on parse errors, missing transcripts, `SESSION_MEMORY_INTERNAL`, or
   a prompt starting `!force` (log the override).
2. From the last assistant entry with usage: idle time from its transcript
   timestamp (not file mtime), and context size =
   `input_tokens + cache_read_input_tokens + cache_creation_input_tokens`.
3. If idle ≥ `SESSION_MEMORY_IDLE_MINUTES` (default 60) and context ≥
   `SESSION_MEMORY_MIN_TOKENS` (default 80000): ask Haiku for a Where it
   stands snapshot from the last 10 exchanges, write it to the register, and
   exit 2 with a short message: idle time and size, that the decisions and
   state are saved, that a new chat will offer to pick it up, the `!force`
   override, and the first 500 characters of the blocked prompt (exit 2
   erases it from the input box). Save the full prompt in the register.

**Detector.** On the first prompt of a session (no assistant entries yet,
prompt at least 30 characters):

1. Candidates: sessions in this project's index active in the last 14 days,
   with a Goal.
2. Haiku gets the prompt and, for up to 8 candidates, the Goal, top three
   active decisions and last active date, and returns a session id or `none`.
   Instruct it to prefer `none` when in doubt. 15-second timeout; exit 0 on
   timeout.
3. On a match, print context telling Claude to ask the user in one line
   whether to pick that work up, before doing anything else. If yes: read the
   register, recap Where it stands in three or four lines, list the inherited
   Constraints, Corrections and Don't retry entries so the user can drop stale
   ones, then copy the kept entries into the new session's register with their
   source id. If no: ignore the note completely. Record the offer so it isn't
   repeated in that session.

**`/pickup` command** as a manual fallback for a session the detector missed:
`/pickup <words>` matches the Goal and does the same as a "yes."

### Phase 4: reading-heavy work goes to subagents

Long documents, many sources and web research are read in subagents that
return conclusions, so the main conversation compacts less and every later
turn re-reads less. An instruction alone gets followed inconsistently, so this
is enforced.

1. **Reader subagent** (Sonnet; Read, Grep, Glob, WebFetch, WebSearch): answer
   the questions asked, cite file and line or section for each claim, flag
   anything contradicting the stated goal, reply under 800 words. Many sources
   are split across parallel readers, then synthesized. In `~/pm-live`, the
   workbench's own heavy-read agents (AGENTS.md) take precedence; the reader is
   for everything else.
2. **Reminder on every prompt** from the `UserPromptSubmit` script: one line
   of context, added fresh each turn so compaction can't remove it.
3. **Reading budget.** `PostToolUse` on Read, Grep, Glob, WebFetch, WebSearch
   tallies what lands in the main conversation since the last user prompt;
   `PreToolUse` blocks the next read past 25,000 tokens or 4 distinct sources
   in one turn, telling Claude (stderr, exit 2) to delegate the rest. Reset on
   each new prompt. Applies to the main conversation only: build this step
   only if Phase 0 found a reliable way to exempt subagent calls. Otherwise
   ship steps 1 and 2 and record the gap in BACKLOG.
4. Log per-turn main-conversation reading and whether delegation happened.

### Phase 5: compaction threshold and the weekly review

**Compact earlier, only after Phase 2 is proven.** Set
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70`. Known issues from public reports: it can
only lower the threshold
([#31806](https://github.com/anthropics/claude-code/issues/31806)); the `env`
block of settings.json may not apply it, while a shell export does
([#63186](https://github.com/anthropics/claude-code/issues/63186)); Cursor
launched from the Dock doesn't see shell exports, and the Claude Code
extension has its own environment-variables setting. Confirm with `/context`.

**Weekly review, automatic analysis, approved changes.** A scheduled headless
run (same pattern as `scripts/run_scheduled.py`) reads the session-memory
logs and writes a short report: captures per session, entries later
superseded or dropped by audits, pick-up offers accepted and declined, held
prompts and `!force` overrides, reading-budget blocks, and the
`rework_correction` share from `session_usage.py` before and after
installation. It proposes changes to thresholds and the Haiku instructions.
A `SessionStart` (startup) hook has Claude offer the report in one line the
next time a session starts. Changes apply only after the user approves them;
the system never rewrites its own rules about what to remember.

## Testing for Part 2

Unit tests with fixture transcripts for every script: fail-open on bad,
Cursor-agent-style and internal payloads; register supersession (same cases as
Part 1); guard thresholds; detector `none` bias; budget tally and reset. Then
live checks per phase in the Cursor panel and the terminal, as listed at the
end of each phase. Calibrate the idle threshold from real transcripts: find
assistant entries that followed a gap where `cache_creation_input_tokens` is
near the full context, and set the threshold just under the shortest such gap.

## Running cost

Each automatic call is Haiku on a few thousand tokens: one per substantive
turn for capture, one per 10 captures for the audit, one per new chat for
matching, one per held prompt. Re-injecting a register after compaction adds
at most a couple of thousand tokens. All of it counts against the plan's
usage, which is why trivial turns skip the call. Compare against one cold
revival of a large conversation or one round of rework.

## Rollback

Part 1: the `supersedes` column is additive; reverting the readers to raw
`decisions.csv` restores old behavior. A register reset is undone by copying
the dated folder in `archive/` back into `registers/`. Part 2: uninstall the plugin, or run
`install.py --uninstall`, which restores the settings backup. Registers can
stay; nothing reads them without the hooks.
