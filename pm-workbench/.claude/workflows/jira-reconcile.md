---
description: Reconcile the Jira board against reality - snapshot diff plus proposed change set
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Context dependencies: soft: systems-map | hard: none

## Gather plan

Batch the independent reads in one turn, then diff. The live board read does not depend on the local registers, and the registers do not depend on the live board. The diff depends on both, so it waits until the batch is back. If this session already read a file, pass the distilled brief onward instead of re-reading the raw file. Re-reading the same file for a different task is fine; prompt caching makes that cheap. No session cache.

Independent (batch together):

- `reference/links.csv` (the board bookmark and which fields mean delivery stage)
- the previous file in `state/jira-snapshots/`
- `registers/decisions.csv`, `registers/commitments.csv`, `registers/initiatives.csv`, `registers/evidence.csv` (recent rows only)
- recent `outputs/daily/*-meeting.md`
- `reference/context/systems-map.md` (key prefixes, repo mapping, link conventions). If that file is still the template, say so and skip key parsing — do not invent a prefix.
- the latest file in `state/repo-activity/` when one exists (the code-vs-board step refreshes it)
- `state/entity-links.csv` (header only until this workflow writes a row)
- the live board via Atlassian MCP, the bookmarked browser view, or a pasted export (name which path — rule 21). Prefer compact fields; write the full payload into the snapshot file instead of pasting it into chat.

Then write `state/jira-snapshots/[date].json` and the diff in `outputs/weekly/[date]-jira-reconcile.md`. Dispatch `internal-docs-reader` only when a discrepancy needs a decision doc outside Jira/Confluence, and pass it the distilled mismatch, not the whole board dump.

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

7. For approved changes: draft the exact text for the Atlassian MCP / internal tool (or type it via browser with my live approval). **Mechanical fixes** (links, comments, missing metadata) can batch under one approval once I trust the accuracy — **priority, owner, dates, scope, status, and delivery-stage changes are always individually approved.** Default this workflow to **read-only against Jira** until I approve a PROPOSALS block. Link and comment writes in the tracker are Tier 2. After I approve a batch, apply it, then re-read each touched ticket and verify the record matches what was approved. Do not mark the batch done from the write call alone.

8. **Code vs board.** From the live workspace, run:

```bash
python3 scripts/repo_activity.py --root "$(pwd)"
```

Pass `--since YYYY-MM-DD` when the cursor in `state/repo-activity-cursor.json` is missing or the window should be explicit. The script reads prefixes from `reference/context/systems-map.md` (or the example, which has no real prefix). It writes `state/repo-activity/[date].json`. This is git metadata only (`git log`, `git fetch`, branch names). It is exempt from the repos preflight gate (SOURCE-POLICY, Git metadata exemption) — do not open source files under `repos/` for this step. If fetch fails or the clone has no remote, the script uses the local log and says so; report that note, and do not treat it as an empty history.

Compare that snapshot to the board snapshot. One Tier 2 batch, local proposals only (`tracker_write` stays false until I approve). Four checks:

- **merged_but_open** — ticket is To Do or In Progress, and a default-branch commit names it. Cite `repo@commit`. Delivery status stays the board's; report the conflict (rule 8, SOURCE-POLICY "Merged in code").
- **stale_in_progress** — In Progress with no commit naming it in N days (default 7; say the window).
- **key_not_on_board** — a key in a commit or branch name is absent from the board snapshot.
- **done_without_commits** — Done with no commits (low priority; it may be non-code work).

9. **Entity links (this workflow only — not fan-out).** Columns in `state/entity-links.csv`: `from,to,type,source,confidence,status,first_seen`. Status is `proposed` or `confirmed`. Types: `ticket-epic`, `paired-tickets`, `ticket-initiative`, `initiative-doc`, `ticket-decision`, `ticket-thread`, `initiative-thread`, `commit-ticket`. Pair rules come from the systems-map link convention, not from a guessed prefix.

```bash
python3 scripts/entity_links.py propose --root "$(pwd)" --activity state/repo-activity/[date].json --tickets <board-snapshot> --comments <comments-export> --apply-confirmed
```

- **Explicit** (a key or id named in a commit, comment, parent field, or initiative row) is Tier 1: write the local row as `confirmed`.
- **Inferred** (a missing pair, a missing parent, a name overlap with no key) is Tier 2: write `proposed` and show the batch. Do not confirm those rows until I approve. `confirm` without approval is a no-op.
- Confirmed links that name an INIT- update that row in place (same id, same order). There is no `links` column: put a doc or PRD path in `prd`, a `DEC-` id in `related_decisions`, and any other ref as a `links:` clause in `notes`. Do not change stage, scope, priority, owner, or dates (Tier 3). Do not add or delete rows.
- Tracker link payloads stay empty until I approve. Nothing in this step calls the tracker.

10. **Comments.** Read recent comments on tracked tickets through the configured tracker path (Atlassian MCP, bookmarked browser, or a pasted export — name which, rule 21). If that path is not configured, say so and skip; do not invent comments. Save the text, then:

```bash
python3 scripts/entity_links.py candidates --root "$(pwd)" --comments <comments-export>
```

Propose decision, risk, or blocker candidates in the reconcile report. Nothing is auto-written to a register or to the tracker. A `DEC-` id named in a comment is an explicit `ticket-decision` link (Tier 1 local). A bare "blocked" with no key is a candidate only.

Save the report to `outputs/weekly/[date]-jira-reconcile.md`. This turns board maintenance into reviewing a diff instead of reconstructing reality.

**First run:** if `reference/links.csv` has no board bookmark, ask which board/filter view is "my board" (link), save it as an L- row **and note which fields mean delivery stage**. Every reconcile output states how the board was read (Atlassian MCP / browser view / pasted export) per rule 21.

**Tier 1 local fan-out:** observations that correct local registers (e.g. a linked DEC- correction, INIT notes, risk mitigation text) may be written this run with provenance. Do not change initiative stage, owner, or dates without Tier 3 approval. Do not write to Jira without approval.

**Cite only IDs that exist.** Never invent COM-/DEC-/RISK-/EV-/INIT-/TODO- numbers in mitigation text, notes, or the reconcile report. Write the register row first in the same run, then cite it. If a follow-up is only proposed, write `proposed: COM row needed — <description>` with no ID. The provenance hook rejects register writes that cite missing IDs.
