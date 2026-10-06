---
description: Reconcile the Jira board against reality - snapshot diff plus proposed change set
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

1. **Get current state** of my active board/epics. Access-path ladder (name which one in the report — rule 21):
   1. **Atlassian MCP** (approved plugin) — preferred when configured and authenticated.
   2. Bookmarked Jira (or equivalent) view via logged-in browser.
   3. Pasted export or CSV I drop in `inbox/` / `archive/documents/`.
   Save a timestamped snapshot to `state/jira-snapshots/[date].json` (or `.md` if structure is loose). Include in the snapshot at least: key, summary, owner, status, **whatever field(s) this board uses for delivery stage** (see below), target date(s), updated, and progress counts when present. If a prior run already logged "my board" in `reference/links.csv`, reuse that link — do not re-ask.

   **MCP hygiene:** board-wide JQL can exceed context limits. Prefer compact/`responseFields` (or write full tool output straight into the snapshot file and work from that file). Do not paste megabyte issue dumps into chat. Re-count live child progress only for keys that moved or that this run's questions depend on; other counts may stay as-of the last export if labeled.

   **Which field is "status"?** Do not assume Jira `status` alone is delivery truth. On many boards (classic sprints, epics, idea/product-discovery views) the meaningful stage lives in another field or in child-issue progress. On first reconcile for a board: discover which field(s) the team actually uses, record their names on the `reference/links.csv` row for that board (or in `.claude/CLAUDE.local.md`), and reconcile against those. CSV exports often omit custom fields — a live MCP/browser read must pull them. When Status and the stage field disagree, say so. Never hard-code a product name or a company-specific field label into this workflow.

2. **Diff against the previous snapshot** in `state/jira-snapshots/` — what changed, what didn't move. If the only prior artifact is an export CSV, materialize a baseline snapshot from it first, then diff.

3. **Cross-reference** against `registers/decisions.csv`, `registers/commitments.csv`, recent `outputs/daily/*-meeting.md`, recent evidence in `registers/evidence.csv`, and — if a specific discrepancy needs checking against a decision doc that lives outside Jira/Confluence — dispatch `internal-docs-reader` for the shared drive or file-browser sources rather than reading them inline.

4. **Cross-check against `registers/initiatives.csv`** — where a ticket maps to a known initiative, use that link to catch PRD-vs-Jira scope drift systematically rather than ad hoc; where it doesn't, that's worth asking whether the ticket should be linked to one.

5. Flag, per ticket where applicable:
   - No update in 7+/14+ days
   - Status **or delivery-stage field** inconsistent with a recorded decision or meeting
   - Missing owner or target date
   - Missing acceptance criteria **only when that field exists on the issue type** (many idea/discovery types have none — skip and say so; do not invent an AC gap)
   - Blocked without an explicit escalation anywhere
   - Decisions made in meetings never recorded on the ticket
   - Scope described differently in PRD vs. Jira
   - Completed work still in active views (Done/Complete stage or all children closed, still on the board)

6. **Output a proposed change set.** Use the ticket block below for high-signal items (blockers, wrong stage, link/comment fixes, INIT drift). Bulk hygiene (many past-target or stale keys) may be a **table** in the report plus Tier 3 listed once — do not force 30+ identical prose blocks.
```
Ticket: ABC-123
Current state: [status] / [delivery stage if different]
Evidence: [what you found, with source + date]
Proposed: add blocked label; link ABC-98; comment summarizing blocker
Needs my approval: any date/priority/owner/status/stage change
Confidence: High/Medium/Low
```

7. For approved changes: draft the exact text for the Atlassian MCP / internal tool (or type it via browser with my live approval). **Mechanical fixes** (links, comments, missing metadata) can batch under one approval once I trust the accuracy — **priority, owner, dates, scope, status, and delivery-stage changes are always individually approved.** Default this workflow to **read-only against Jira** until I approve a PROPOSALS block.

Save the report to `outputs/weekly/[date]-jira-reconcile.md`. This turns board maintenance into reviewing a diff instead of reconstructing reality.

**First run:** if `reference/links.csv` has no board bookmark, ask which board/filter view is "my board" (link), save it as an L- row **and note which fields mean delivery stage**. Every reconcile output states how the board was read (Atlassian MCP / browser view / pasted export) per rule 21.

**Tier 1 local fan-out:** observations that correct local registers (e.g. a linked DEC- correction, INIT notes, risk mitigation text) may be written this run with provenance. Do not change initiative stage, owner, or dates without Tier 3 approval. Do not write to Jira without approval.
