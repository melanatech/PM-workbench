---
description: Close out a meeting - decisions, commitments, and risks flow into the registers
argument-hint: [paste notes/transcript, or filename in inbox/meetings/]
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Meeting input: $ARGUMENTS

(This can be typed notes, a downloaded meeting transcript/AI summary (Teams, Zoom, Meet) if you organized the meeting, whatever your meeting tool's AI summary produces if you didn't, or a dictated voice memo transcript — treat all of them the same way below.)

1. Extract: decisions, commitments (owner + due date), risks, assumptions stated, unresolved questions, and anything that changed a prior decision.

2. **PM-scope filter (this is a PM workbench — not an eng ticket tracker).** Before writing any register row, keep only items the PM needs to own, chase, or remember for product work. Apply especially hard to **commitments**:

   **Log a commitment when** at least one is true:
   - The PM is the owner, audience, or the person who must follow up
   - It is a promise about product scope, UX, requirements, research, launch, metrics, stakeholders, or design deliverables the PM depends on
   - Missing it would cause the PM to drop a ball (e.g. "Sabrine sends Figma links", "groom cash-discount tickets before the 14 Oct release" when that release is in the PM's area)

   **Do not log as a commitment** (mention at most as one "eng-only, not tracked" line in the output, with no COM- id):
   - Pure engineering / ops / infra work with no PM dependency (SSL/cert/secret rotation, DB vacuum/index cleanup, cluster cutovers, on-call chores, "ping Charlie about DP test")
   - Sprint housekeeping already owned end-to-end by eng with no product decision or PM follow-up
   - Someone else's task the PM only overheard and will not chase

   Same spirit for **decisions** and **risks**: keep product / process / launch / stakeholder items; skip infra chores unless they block a product date or metric the PM owns (then log the *product risk*, not the eng chore). When unsure, prefer a short QUESTIONS item over inventing a COM- row.

3. **Reconcile against current state:** compare extracted items with `registers/decisions.csv`, `registers/commitments.csv`, and (if provided or fetchable) relevant Jira tickets. Flag conflicts explicitly — e.g., "meeting moved readiness to Aug 19 but ticket still says Aug 5."

4. **Seed and cross-check `registers/initiatives.csv` (do not leave the hub empty when product work was named).** For each distinct **PM-scoped product initiative** clearly named or treated as in-flight work in the meeting:

   - **Create a row** if none matches (same name / obvious alias). IDs: `INIT-nnn` next unused. Stages (descriptive, not a pipeline): `discovery` | `building` | `prd` | `prototype` | `experiment` | `launched` | `killed` | `iterating`. Prefer `discovery` / `building` / `iterating` when no PRD/prototype path exists yet. Link `related_decisions` / `related_risks` to IDs from this closeout when they apply. Put source meeting path and open enhancement bullets in `notes`. Set `last_updated` to today.
   - **Update in place** (same id, same row order) when the meeting advances stage, adds a decision/risk link, or adds concrete enhancement items — append to `notes`, do not invent a second row for the same feature.
   - **One row per initiative**, not per ticket. Smaller enhancements (date selector, lock column, table total row, status labels, etc.) go in that initiative's `notes` (and evidence rows when discovery material), not as separate INIT- rows — unless the meeting treats them as their own epic/release slice (e.g. cash discount for 14 Oct).
   - **Never create INIT- rows for eng-only infra** (SSL/certs, DB vacuum/index cleanup, cluster cutovers, on-call). Same PM-scope filter as commitments.
   - If a decision/commitment touches an initiative, name it explicitly — "this affects [INIT-nnn name], currently at [stage]" — and note whether it implies re-running `/build prd-package`, `/build prototype-build`, or `/build experiment-package`.

5. Write clear, unambiguous register updates directly (per CLAUDE.md, internal writes don't need live approval) — tell me what got logged, including any new/updated INIT- rows. For anything genuinely ambiguous (unclear owner, conflicting dates, a decision that reads differently depending on tone, whether two names are one initiative), show it as a proposed diff and ask, rather than guessing or blocking on approval for everything. If an existing COM-/DEC-/RISK- row fails the PM-scope filter, mark it `dropped` (or `done` with note) in place — do not delete the row (rule 7). Changing an initiative's scope/priority/owner/dates still needs Tier 3 confirmation before you rewrite those fields — seeding a missing row from an explicit meeting name is Tier 1.

6. Save the summary to `outputs/daily/[date]-[topic]-meeting.md`: summary, then only the sections that have content (decisions, action items, risks, open questions, changes from prior decisions, conflicts). Omit empty headings. Eng-only items skipped by the filter go in at most one short "Not tracked (eng-only)" line if they appeared in the meeting — never as register rows. If everything was already in the registers, the file can be a short reconciliation (existing IDs, what you did not duplicate) plus any open call.

6b. **Assumptions and open questions → living file (do not leave them only in chat/output).** Append any new **assumptions stated** and **unresolved questions** (and unresolved conflicts that are questions, e.g. fees scope) to `reference/context/assumptions-and-open-questions.md`. Create the file from the kit template if missing. Each bullet: date, one line, source path, related INIT-/DEC-/RISK- if known, status `open`. Deduplicate against existing open bullets. When a later meeting resolves one, mark that bullet `resolved YYYY-MM-DD` in place (do not delete). This file is living context like `current-priorities.md`, not an immutable register.

6c. **Product knowledge → `learning/`.** If the meeting taught something durable about how the product works (a Figma walkthrough, report behavior, status labels, export limits), update or create `learning/[area].md` (e.g. `learning/commerce-intelligence.md`) with dated bullets and source paths. Skip one-off scheduling trivia.

7. Draft (do not send) follow-up messages or Jira text only when the meeting implies one. Do not write a "no drafts / only attendee / no Jira" section. Do not draft Jira for eng-only chores the filter skipped unless I ask.

   **When drafting Jira tickets**, match `reference/templates/jira-ticket-draft.md` exactly:
   - **Summary** must be descriptive enough that someone who was not in the meeting understands the change and the product reason (not a short label).
   - Always include **Initiative/Epic**, **Priority**, and **Target date** (use `[NEEDS INPUT]` or `provisional` + why — never omit).
   - **Related tickets** = other Jira keys (or sibling drafts by number) only. Never put workbench paths, COM-/DEC-/RISK-/TODO- ids, meeting titles, or Stream URLs in Related / Source fields that would be pasted into Jira — nobody else can open those. Keep workbench citations in an optional "Workbench notes (do not paste into Jira)" footer of the drafts file only.
   - Write drafts under `drafts/jira-[date]-[topic].md` (or the path I name). Show the paste blocks once.

If the meeting produced follow-ups that are mine to do but are not commitments to anyone: write them as a numbered candidate table to `outputs/todo-proposals/[date]-proposals.md` (create folder if needed; start with `QUEUED — nothing added` if new file; if today's file exists, add a section). Do **not** add rows to `registers/todos.csv` from here — I pick via `/todo propose`. One line in the reply: path + count. If there are none, skip.

**Fan-out (required).** After registers/initiatives/assumptions/learning/todo-proposals above, read and apply `.claude/workflows/_fan-out.md`. Update every surface that applies in this same run (including `current-priorities.md` when week pressure/dates moved; competitive log/`state/competitive/` when a competitor was named with a durable claim; every INIT- touched, not only the primary). End with the Surfaces updated / N/A / Cross-initiative block from that file.


The measure of this command is not the summary — it's that the registers stay true *for PM work*. A meeting isn't closed out until its product-relevant decisions and commitments are reconciled with the system of record.
