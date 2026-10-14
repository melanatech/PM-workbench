---
name: authority-lookup
description: >
  Use for freeform factual lookups: what did I commit, what's due, didn't I promise,
  open commitments for a person or topic, what did we decide, initiative status,
  risks, metric value, is the inbox empty, what does the PRD say, board or ticket
  state, what instrumentation exists, what did we already conclude, how did you
  check, or any named surface. Enforce CLAUDE.md rules 25–26: read the
  authoritative surface first, then secondary sources. Never answer from a single
  find hit, transcript, or draft.
---

# authority-lookup

Freeform lookup — **not** a slash workflow. Enforce CLAUDE.md rules 25–26. Promise and due questions use this skill (there is no separate commitment skill).

1. Classify the question type (commitment, todo, decision, initiative, risk, metric, PRD, inbox, Jira, priorities, prior analysis / instrumentation, verification, named surface).
2. Read the **authoritative surface first** (Rule 25 table below).
   - Prior analysis / "what do we already know" / events / instrumentation → run `python3 scripts/context_preflight.py --root <live> --topic "…"` (or read a fresh marker). Cite hits + `primary_sources`.
   - Verification / "how did you check?" / baseline "today" → SOURCE-POLICY claim-type ladder; chain to a capture or `repos/…@commit` / locale file. Never stop at "the brief says."
   - A named surface → `reference/context/workspace-aliases.md` first, then preflight. Ask if still ambiguous.
3. Operational matches (process-inbox, jira-reconcile, explore-brief, and the rest of `_plain-language.md`) still run the workflow — do not improvise a lighter peek.
4. Use digests, archive, or raw files only to fill gaps or quote wording.
5. Reply with the answer **plus** a one-line coverage note when the source set is non-obvious.

**Forbidden:** leading with `find` on `archive/`; one meeting file as the whole answer; citing only `drafts/` or `prototypes/` as evidence for product facts; blank-slate re-investigation when a dated hit exists; waiting for the PM to push back before checking the index.

## Rule 25 — authority-first lookups

Pick the authoritative surface for the question type, read it first, then secondary sources only to fill gaps or quote wording. One coverage line when the set is non-obvious. Do not lead with `find` on raw archive or a single convenient file.

| Question type | Authoritative surface first | Then (only if needed) |
|---|---|---|
| Promises / due / "didn't I commit" / meeting action items | `registers/commitments.csv` (open/overdue; filter owner/due/topic) | todos → digests → specific meeting files |
| My action list / TODO-nnn | `registers/todos.csv` via `scripts/todo_register.py` | digests / source links on the row |
| What did we decide | `registers/decisions.csv` | digests → transcript for exact wording |
| Initiative / feature status and links | `registers/initiatives.csv` | linked PRD/outputs; the tracker if delivery dates are disputed |
| Risks | `registers/risks.csv` | digests |
| Metric value / trend | `state/okr-history.csv` (+ metric YAML if present) | dashboard or deck only to refresh or resolve a conflict |
| PRD / current scope | initiative row → `outputs/prds/…` | prototype, tracker — report conflicts (rule 8) |
| "Inbox empty?" / what's waiting | `scripts/intake_status.py` / process-inbox Step 0 | never a bare `inbox/` peek |
| Board / ticket hygiene | `/sync jira-reconcile` (live board or export) | local notes are not tracker truth |
| Strategy / priorities this week | `reference/context/current-priorities.md` + latest strategy outputs | older decks only with dates |
| Prior analysis / instrumentation / events / code findings | `python3 scripts/context_preflight.py --topic "…"` (`state/analysis-index.csv` + outputs/learning) | `repos/` only when the recommendation is `investigate` / `reuse_and_refresh` or `--allow-repos` |
| Verification / "how did you check?" / baseline "today" | SOURCE-POLICY claim-type ladder → primary source (capture, repo@commit, locale file) | Never stop at a draft, brief, or prototype citation |
| Named surface / any PM-named artifact | `reference/context/workspace-aliases.md` first, then `context_preflight --topic "…"` | Glob/search; **ask** if still ambiguous. Do not guess the nearest-sounding file (for example glossary for a metric workbook). |
| Company or area acronyms | `reference/context/glossary.md` | — |

**Name resolution:** if a phrase names a surface and the path is unclear, read `workspace-aliases.md`, then Glob/Grep/`context_preflight`. Do not map an unfamiliar name onto the nearest file.

**Worked example (commitments):** do not start in `archive/meetings/`. Order: `commitments.csv` → `todos.csv` → `decisions.csv` if relevant → recent `outputs/daily/` digests → a specific meeting file only to fill a gap or verify wording.

**Worked example (instrumentation):** do not start in `repos/`. Order: `context_preflight --topic instrumentation events` → cite the digest and its primary commit → clone only if preflight says refresh or investigate.

**Coverage line (when non-obvious):** what you read and what you skipped — for example "From commitments.csv: COM-012 (due 10-13), COM-010; digests checked; did not re-read the full transcript."

## Rule 26 — cache-first analyses

1. Run `context_preflight` (or require a fresh `state/.context-preflight.json`) before investigating.
2. Cite hits with as_of **and** their `primary_sources` when present.
3. On `reuse_and_refresh` or a conflict, do a targeted refresh and report conflicts (rule 8).
4. A new durable analysis → `scripts/analysis_index.py append` in the same run (or fan-out).
5. Forbidden: blank-slate re-investigation when hits exist and there is no staleness or conflict signal; answering "the brief says" for a product-fact check.

Citations under `drafts/` or `prototypes/` are not evidence. Carry `primary_sources` from the index, or climb the SOURCE-POLICY claim-type ladder. Hooks block ungrounded consequential writes and `repos/**` reads without a fresh preflight marker.
