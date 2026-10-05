# Jira ticket draft (paste-ready)

Use this shape for every drafted Jira issue (from `/capture meeting-closeout`, `/capture process-inbox`, `/build prd-package`, etc.). Drafts only — never create until approved.

The **paste block** is what goes into Jira. Anyone reading it in Jira has no access to the PM workbench, so it must stand alone.

## Paste block (one ticket)

```
Summary: <one line that states the change AND the product reason — not a vague label>
Type: Story | Bug | Task | Spike
Initiative / Epic: <initiative name or epic key; [NEEDS INPUT] if unknown>
Priority: Highest | High | Medium | Low | Lowest   (cite meeting/decision if set; else provisional + why)
Target date: <YYYY-MM-DD or none>
Assignee: <name or Unassigned>

Description:
<2–5 short paragraphs. Cover: what is wrong or missing today, who is affected,
what “done” looks like in the product, and any constraint from the meeting.
Do not assume the reader saw the meeting or the workbench.>

Acceptance criteria:
- [ ] …
- [ ] …

Related tickets: <Jira keys only, e.g. ABC-123, or sibling drafts as "Draft #2 — …". Write "none" if none.>
```

## Field rules

| Field | Do | Don't |
|---|---|---|
| **Summary** | Say *what* to change and *why it matters* (surface + outcome). Aim ~80–120 chars if needed. | One-word labels (`Fees`, `Backfill`, `SLA`); eng jargon with no product context |
| **Initiative / Epic** | `registers/initiatives.csv` name, or known epic key | Leave blank silently — use `[NEEDS INPUT]` |
| **Priority / Target date** | Always set; mark `provisional` when inferred | Omit; invent a hard date the meeting never said |
| **Related tickets** | Other **Jira** keys, or other drafts in this same file by number | `COM-` / `DEC-` / `RISK-` / `TODO-` ids; `archive/…` paths; meeting filenames; Stream URLs; “Source: sprint planning” |
| **Description** | Self-contained for eng/design who were not in the room | “See COM-006”; workbench-only pointers |

## Outside the paste block (PM-only, optional)

At the bottom of the drafts file, a short **Workbench notes (do not paste into Jira)** section may cite DEC-/COM-/RISK- ids and archive paths for your follow-up. That section is never part of the ticket body.
