---
description: Close out a meeting - decisions, commitments, and risks flow into the registers
argument-hint: [paste notes/transcript, or filename in inbox/meetings/]
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Context dependencies: soft: people, current-priorities | hard: none

Meeting input: $ARGUMENTS

(This can be typed notes, a downloaded meeting transcript/AI summary (Teams, Zoom, Meet) if you organized the meeting, whatever your meeting tool's AI summary produces if you didn't, or a dictated voice memo transcript — treat all of them the same way below.)

**0. Incomplete / unlabeled transcript and fidelity gate.** If the source file has frontmatter `incomplete: true`, or a multi-speaker transcript has no speaker labels on lines, **stop before writing COM owners**. Ask once to recapture with the current clipper (slow full DOM pass) or drop a `.vtt`/`.docx` if download is enabled. If the PM says proceed anyway: write the summary with a **provisional** banner, and set any unclear COM `owner` to `[NEEDS INPUT]` — never invent owners from unlabeled speech.

Classify the input `fidelity: full | summary | excerpt` before writing registers. Frontmatter `fidelity:` wins (clipboard capture writes it). Otherwise run `python3 scripts/source_fidelity.py <file>` (or pass the pasted text on stdin) and follow `action`. Markers: an AI-summary header → `summary`; "N replies" or "View thread" without the replies → `excerpt`; truncation "…" or "Show more" → `excerpt`; a recap with no speaker or timestamp structure → `summary`. An AI recap is not a full transcript.

When `action` is `ask` (a summary or excerpt that would create a decision, commitment, owner, date, or risk): ask once — proceed labeled, paste the full thread, or skip — and do not write those rows until answered. When it is `proceed-labeled`, write with `source_fidelity=summary` or `source_fidelity=excerpt`. A full thread (`action: proceed`) does not ask. Unattended runs (rule 22) never wait: label `source_fidelity`, keep the provisional banner, and use `[NEEDS INPUT]` where the summary does not name an owner or date.

1. Extract: decisions, commitments (owner + due date), risks, assumptions stated, unresolved questions, and anything that changed a prior decision.

2. **PM-scope filter (this is a PM workbench — not an eng ticket tracker).** Before writing any register row, keep only items the PM needs to own, chase, or remember for product work. Apply especially hard to **commitments**:

   **Log a commitment when** at least one is true:
   - The PM is the owner, audience, or the person who must follow up
   - It is a promise about product scope, UX, requirements, research, launch, metrics, stakeholders, or design deliverables the PM depends on
   - Missing it would cause the PM to drop a ball (e.g. "designer sends Figma links", "groom tickets before the next release" when that release is in the PM's area)

   **Do not log as a commitment** (mention at most as one "Not tracked (engineering keep-list)" line in the output, with no COM- id):
   - Pure engineering / ops / infra work that does **not** change a keep-list item from `_source-triage.md` (SSL/cert/secret rotation, DB vacuum/index cleanup, cluster cutovers, on-call chores, "ping Charlie about DP test")
   - Sprint housekeeping already owned end-to-end by eng with no product decision or PM follow-up
   - Someone else's task the PM only overheard and will not chase

   Same spirit for **decisions** and **risks**: keep product / process / launch / stakeholder items; skip routine infra unless it hits the keep-list (merchant-visible behavior, API/schema/metric meaning, launch readiness, reliability/data quality, instrumentation, architecture that limits scope, cost/capacity) — then log the *product* impact, not the chore. When unsure, prefer a short QUESTIONS item over inventing a COM- row (except exploratory-thinking: never ask owners/decisions).

2b. **Source triage (required).** Apply `.claude/workflows/_source-triage.md` to the meeting source before register writes. Ideas / "things to think about" with no owner or decision → role `exploratory-thinking`, outcome `hold` (dated Ideas entry in learning + source-index row; **no EV/DEC/COM**; **no questions about owners or decisions**). Multiple transcripts of the same meeting → fullest is primary; others `duplicate` with `same_as`. Stakeholder preferences → `stakeholder-stance` into `reference/context/people.md`. Append the triage row via `scripts/source_index.py append`.

3. **Reconcile against current state:** compare extracted items with `registers/decisions.csv`, `registers/commitments.csv`, and (if provided or fetchable) relevant Jira tickets. Flag conflicts explicitly — e.g., "meeting moved readiness to Aug 19 but ticket still says Aug 5." Status claims ("done", "pulled into sprint") → tag `needs-authority`; when Jira is available, check in this run (Jira wins).

4. **Seed and cross-check `registers/initiatives.csv` (do not leave the hub empty when product work was named).** For each distinct **PM-scoped product initiative** clearly named or treated as in-flight work in the meeting:

   - **Create a row** if none matches (same name / obvious alias). IDs: `INIT-nnn` next unused. Stages (descriptive, not a pipeline): `discovery` | `building` | `prd` | `prototype` | `experiment` | `launched` | `killed` | `iterating`. Prefer `discovery` / `building` / `iterating` when no PRD/prototype path exists yet. Link `related_decisions` / `related_risks` to IDs from this closeout when they apply. Put source meeting path and open enhancement bullets in `notes`. Set `last_updated` to today.
   - **Update in place** (same id, same row order) when the meeting advances stage, adds a decision/risk link, or adds concrete enhancement items — append to `notes`, do not invent a second row for the same feature.
   - **One row per initiative**, not per ticket. Smaller enhancements (date selector, lock column, table total row, status labels, etc.) go in that initiative's `notes` (and evidence rows when discovery material), not as separate INIT- rows — unless the meeting treats them as their own epic/release slice (e.g. cash discount for 14 Oct).
   - **Engineering keep-list** (from `_source-triage.md`): keep engineering detail only when it changes merchant-visible behavior, API/event/schema/metric meaning, launch readiness, reliability/data quality, instrumentation, architecture that limits scope, or cost/capacity. Routine infra (SSL/certs, DB vacuum/index cleanup, cluster cutovers, on-call) → ignore with that reason; never create INIT-/COM- rows for it.
   - **Initiative candidate gate:** when ≥3 criteria in `_source-triage.md` §6 hold for a topic that was folded into a parent, raise `INITIATIVE CANDIDATE` (Tier 3 proposal) — do not create the row silently.
   - If a decision/commitment touches an initiative, name it explicitly — "this affects [INIT-nnn name], currently at [stage]" — and note whether it implies re-running `/build prd-package`, `/build prototype-build`, or `/build experiment-package`.

5. Write clear, unambiguous register updates directly (per CLAUDE.md, internal writes don't need live approval) — tell me what got logged, including any new/updated INIT- rows. **Ask budget:** at most one question batch; only for gaps that block a write the source clearly calls for. Never ask owners/decisions on exploratory-thinking. Honor `parked YYYY-MM-DD` markers. If an existing COM-/DEC-/RISK- row fails the keep-list, mark it `dropped` (or `done` with note) in place — do not delete the row (rule 7). Changing an initiative's scope/priority/owner/dates still needs Tier 3 confirmation before you rewrite those fields — seeding a missing row from an explicit meeting name is Tier 1.

6. Save the summary to `outputs/daily/[date]-[topic]-meeting.md`: summary, then only the sections that have content (decisions, action items, risks, open questions, changes from prior decisions, conflicts). Omit empty headings. Ignored engineering items go in at most one short "Not tracked (engineering keep-list)" line if they appeared — never as register rows. If everything was already in the registers, the file can be a short reconciliation (existing IDs, what you did not duplicate) plus any open call.

6b. **Assumptions and open questions → living file (do not leave them only in chat/output).** Append any new **assumptions stated** and **unresolved questions** (and unresolved conflicts that are questions, e.g. fees scope) to `reference/context/assumptions-and-open-questions.md`. Create the file from the kit template if missing. Each bullet: date, one line, source path, related INIT-/DEC-/RISK- if known, status `open`. Deduplicate against existing open bullets. When a later meeting resolves one, mark that bullet `resolved YYYY-MM-DD` in place (do not delete). This file is living context like `current-priorities.md`, not an immutable register.

6c. **Product knowledge → `learning/`.** If the meeting taught something durable about how the product works (a Figma walkthrough, report behavior, status labels, export limits), update or create `learning/[area].md` (e.g. `learning/billing.md`) with dated bullets and source paths. Skip one-off scheduling trivia.

7. Draft (do not send) follow-up messages or Jira text only when the meeting implies one. Do not write a "no drafts / only attendee / no Jira" section. Do not draft Jira for keep-list-skipped chores unless I ask.

   **When drafting Jira tickets**, match `reference/templates/jira-ticket-draft.md` exactly — paste block **and** its quality checklist (confirm project, verify epic in Jira, search duplicates/conventions, concrete before/after, named surfaces, actionable `[NEEDS INPUT]`, verifiable ACs, formal related links, design links, target-project field values):
   - **Summary** must be descriptive enough that someone who was not in the meeting understands the change and the product reason (not a short label).
   - Always include **Project**, **Initiative/Epic**, **Priority**, and **Target date** (use `[NEEDS INPUT]` or `provisional` + why — never omit). Priority/type values must match the **target** project (see CLAUDE.local).
   - **Related tickets** = other Jira keys (or sibling drafts by number) only. Never put workbench paths, COM-/DEC-/RISK-/TODO- ids, meeting titles, or Stream URLs in Related / Source fields that would be pasted into Jira — nobody else can open those. Keep workbench citations in an optional "Workbench notes (do not paste into Jira)" footer of the drafts file only.
   - Write drafts under `drafts/jira-[date]-[topic].md` (or the path I name). Show the paste blocks once.

If the meeting produced follow-ups that are mine to do but are not commitments to anyone: write them as a numbered candidate table to `outputs/todo-proposals/[date]-proposals.md` (create folder if needed; start with `QUEUED — nothing added` if new file; if today's file exists, add a section). Do **not** add rows to `registers/todos.csv` from here — I pick via `/todo propose`. One line in the reply: path + count. If there are none, skip.

**Fan-out (required).** After triage + registers/initiatives/assumptions/learning/todo-proposals above, tag each **promote** item and apply `.claude/workflows/_fan-out.md` (only the surfaces `scripts/fanout_route.py` names for those types). Then run the cross-source pass and implications check from `_source-triage.md`. Update every matching surface in this same run (competitive log when a competitor was named; every INIT- touched). `current-priorities.md` only when week pressure clearly moved **and** confirmed (Tier 3) — strategy-frame never writes it silently. End with the Surfaces updated / Cross-initiative block. No N/A list.


The measure of this command is not the summary — it's that the registers stay true *for PM work*. A meeting isn't closed out until its product-relevant decisions and commitments are reconciled with the system of record.
