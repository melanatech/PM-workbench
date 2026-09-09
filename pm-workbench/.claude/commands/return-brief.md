---
description: One-time return-to-work delta brief - what changed while I was on leave
argument-hint: [leave start date] [return date]
---

I was on leave from $ARGUMENTS. Build me a "what changed" brief — organized by significance, NOT chronologically.

**Gather** (browser for Slack/dashboards; paste-in or internal-tool pulls for Jira/Confluence; I'll drop anything else into `inbox/`) — my bookmarked Slack searches scoped to the leave window, Jira epics/tickets in my area, Confluence docs modified during the window, any leadership announcements I've dropped into `inbox/`.

**Dispatch all of it, plus any leadership decks/org docs on SharePoint or the file browser, to the `return-window-scanner` subagent.** This is the heaviest read in the whole kit — weeks of Slack/Jira/Confluence/SharePoint history has no reason to sit in this session once extracted.

**Produce `outputs/return-brief.md`:**
1. Decisions that changed (with source + date each)
2. Features shipped / delayed / cancelled / rescoped
3. OKR changes — targets, definitions, or ownership
4. New technical constraints or dependencies
5. Customer escalations touching my area
6. People changes — new roles, departures, shifted influence
7. **Assumptions I held before leave that are no longer true** (compare against anything in `reference/product-knowledge/`)
8. Unresolved decisions still hanging
9. The ten questions I should ask before acting on anything

Also produce `outputs/return-brief-manager-onepager.md` — a one-page version titled "What changed, what I'm validating, my immediate priorities" to share with my manager in week one. It should read as rapid reorientation, not as pretending I already know everything.

Seed the registers: any decisions found → `registers/decisions.csv`; live risks → `registers/risks.csv`; standing commitments → `registers/commitments.csv`. The system starts populated, not empty.
