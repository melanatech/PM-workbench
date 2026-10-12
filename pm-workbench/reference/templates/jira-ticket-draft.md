# Jira ticket draft (paste-ready)

Use this shape for every drafted Jira issue (from `/capture meeting-closeout`, `/capture process-inbox`, `/build prd-package`, etc.). Drafts only — never create until approved.

The **paste block** is what goes into Jira. Anyone reading it in Jira has no access to the PM workbench, so it must stand alone.

Before drafting, run the **quality checklist** below. Org-specific project maps, priority names, and epic naming conventions live in `.claude/CLAUDE.local.md` (or a private live checklist) — not in this kit file.

## Paste block (one ticket)

```
Summary: <one line that states the change AND the product reason — not a vague label>
Type: Story | Bug | Task | Spike
Project: <Jira project key — from CLAUDE.local / discovered conventions>
Initiative / Epic: <initiative name or epic key; [NEEDS INPUT] if unknown>
Priority: <use the target project's real priority values; cite meeting/decision if set; else provisional + why>
Target date: <YYYY-MM-DD or none>
Assignee: <name or Unassigned>

Description:
Problem:
<what is wrong or missing today — concrete, not vibes>

Expected behavior:
<what “done” looks like in the product>

Scope:
<in>

Out of scope:
<out>

Acceptance criteria:
- [ ] …
- [ ] …

Related tickets: <Jira keys only, e.g. ABC-123, or sibling drafts as "Draft #2 — …". Write "none" if none.>
```

Prefer **Problem → Expected behavior → Scope → Out of scope → Acceptance criteria** unless the issue type demands another shape (spike, TDD, etc.). Match strong completed tickets in the **same** project when they already use a house format.

## Field rules

| Field | Do | Don't |
|---|---|---|
| **Summary** | Say *what* to change and *why it matters* (surface + outcome). Aim ~80–120 chars if needed. | One-word labels; eng jargon with no product context |
| **Project** | The Jira project that owns this work (from CLAUDE.local) | Guess; omit when multi-project ownership is unclear |
| **Initiative / Epic** | Verified epic key or `registers/initiatives.csv` name | Cite a planning-doc epic name without checking Jira |
| **Priority / Target date** | Always set using **that project's** field values; mark `provisional` when inferred | Omit; invent a hard date the meeting never said; assume another project's labels |
| **Related tickets** | Other **Jira** keys, or other drafts in this same file by number | `COM-` / `DEC-` / `RISK-` / `TODO-` ids; `archive/…` paths; meeting filenames; Stream URLs |
| **Description** | Self-contained for eng/design who were not in the room | “See COM-006”; workbench-only pointers |

## Quality checklist (before you write / when you structure / when you link)

### Before you write

1. **Confirm the project.** Which Jira project owns this work? Ownership rules belong in CLAUDE.local. If the work spans projects, create the ticket in the primary project and flag the sibling need with **specifics about what the other project's ticket would cover**.

2. **Find the right epic.** Search Jira — do not reference an epic name from a planning doc without verifying it exists. Check active and upcoming epics, not only backlog.

3. **Check what already exists.** Search done and in-progress tickets for similar work before writing. A ticket that ignores shipped or in-flight work confuses the engineer who picks it up; acknowledge overlaps in the draft.

4. **Check for established conventions.** Search for prior art that set a pattern in that project. If your ticket contradicts an established pattern, either align with it or explicitly say why you are departing.

### Structure the ticket

5. **Use the structure completed tickets in that project use.** Default: Problem → Expected behavior → Scope → Out of scope → Acceptance criteria. Do not invent a different structure unless the issue type demands it.

6. **Describe the before and after concretely.** Vague user pain is not enough. State the observable mismatch (what surface A shows vs surface B, or what happens today vs what should happen). Use tables when there are multiple states to compare.

7. **Name the specific surfaces, components, and code paths.** Prefer concrete names (screens, components, endpoints, queries, tables) over a vague product-area label. If an API, schema, or data path is involved, name it.

8. **Make NEEDS INPUT flags actionable.** Not “may need a sibling ticket.” State the open question and how someone answers it without a round trip to the PM (what to check, what would decide yes/no).

9. **Make acceptance criteria verifiable.** Every AC should be something QA can write a test case against — measurable outcomes, not “users understand” or “feels right.”

### Reference and link

10. **Link related tickets formally, not just in prose.** Dependencies should be formal Jira link types (Blocks, Relates to, Implements, etc.) when creating/updating — not only keys buried in description text. In drafts, list keys under Related and note the intended link type.

11. **Link to design artifacts.** If an AC says “matches Figma” (or equivalent), the artifact URL must be in the ticket — or the ticket must say `[NEEDS INPUT: design link must be added before work starts]`.

12. **Verify Jira field values before creating.** Priority names, issue types, and custom fields vary by project. Check an existing ticket in the **target** project (or CLAUDE.local notes from a prior create). Some projects have no Spike type — use the local convention (e.g. Task with `Spike:` in the summary) only after confirming.

## Outside the paste block (PM-only, optional)

At the bottom of the drafts file, a short **Workbench notes (do not paste into Jira)** section may cite DEC-/COM-/RISK- ids and archive paths for your follow-up. That section is never part of the ticket body.
