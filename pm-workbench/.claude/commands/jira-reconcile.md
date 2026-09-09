---
description: Reconcile the Jira board against reality - snapshot diff plus proposed change set
execution_mode: fast   # fast=0 reviewers, standard=1-2, deep=full panel (see CLAUDE.md)
---

1. **Get current state:** pull my active board/epics — via the internal tool (I'll paste the output if you can't reach it) or by reading my bookmarked Jira view through the browser. Save a timestamped snapshot to `state/jira-snapshots/[date].json` (or .md if structure is loose).
2. **Diff against the previous snapshot** in `state/jira-snapshots/` — what changed, what didn't move.
3. **Cross-reference** against `registers/decisions.csv`, `registers/commitments.csv`, recent `outputs/daily/*-meeting.md`, recent evidence in `registers/evidence.csv`, and — if a specific discrepancy needs checking against a decision doc that lives outside Jira/Confluence — dispatch `internal-docs-reader` for SharePoint or file-browser sources rather than reading them inline.
4. **Cross-check against `registers/initiatives.csv`** — where a ticket maps to a known initiative, use that link to catch PRD-vs-Jira scope drift systematically rather than ad hoc; where it doesn't, that's worth asking whether the ticket should be linked to one.
5. Flag, per ticket where applicable:
   - No update in 7+/14+ days
   - Status inconsistent with a recorded decision or meeting
   - Missing owner, target date, or acceptance criteria
   - Blocked without an explicit escalation anywhere
   - Decisions made in meetings never recorded on the ticket
   - Scope described differently in PRD vs. Jira
   - Completed work still in active views

5. **Output a proposed change set**, one block per ticket:
```
Ticket: ABC-123
Current state: In Progress
Evidence: [what you found, with source + date]
Proposed: add blocked label; link ABC-98; comment summarizing blocker
Needs my approval: any date/priority/owner/status change
Confidence: High/Medium/Low
```

6. For approved changes: draft the exact text for the internal tool (or type it via browser with my live approval). **Mechanical fixes** (links, comments, missing metadata) can batch under one approval once I trust the accuracy — **priority, owner, dates, scope, and status changes are always individually approved.**

Save the report to `outputs/weekly/[date]-jira-reconcile.md`. This turns board maintenance into reviewing a diff instead of reconstructing reality.

**First run:** ask which board/filter view is "my board" (link), save it. Every reconcile output states how the board was read (browser view / pasted export / internal-tool pull) per rule 21.
