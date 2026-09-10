---
description: Launch package - drift detection first, then all audience docs from reconciled truth
argument-hint: [feature name]
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Launch package for: $ARGUMENTS

**Step 0 — reconcile:** refresh current Jira scope and the approved Confluence PRD before anything else; the drift check is worthless against stale inputs.

**Step 1 — dispatch to the `launch-drift-detector` subagent** (in `.claude/agents/`) with the approved PRD, current Jira scope + acceptance criteria, prototype notes (if in `prototypes/`), instrumentation plan, and any existing docs/marketing/support drafts. It reads all of it in its own isolated context and returns only the discrepancy report — keeping this session from filling up with every source document.

**Step 2 — resolve.** Show me the discrepancy list; I resolve each (or take them to the team). Docs generated from unreconciled sources are how launch-day surprises happen — the drift report IS the deliverable that saves you.

**Step 3 — generate from IMPLEMENTED scope** (never the original PRD), to `outputs/launches/[feature]/`: release notes; customer-facing doc draft; internal FAQ; support troubleshooting guide; AM/CS briefing + talking points; marketing fact sheet; known-limitations doc; launch checklist; post-launch monitoring plan (which metrics, which behavior-analytics segments to watch — pull the actual metric names from `registers/initiatives.csv`'s related_okr if set, so monitoring targets the OKR this was meant to move). Wiki-bound pieces formatted for your wiki; the announcement email as a draft. **For deliverables that need real formatting** (branded one-pagers, exec-ready Word docs): if a tagged template exists in `reference/templates/formatted/`, generate the context JSON and render through `scripts/render_template.py`; if not, produce clean markdown and log the missing template in BACKLOG.md — templates accelerate, never gate.

**Step 4 — close the loop.** Update `registers/initiatives.csv`: stage=launched, launch_path, last_updated. This is usually the last stage-update an initiative gets — `/strategy-refresh` and `/weekly-update` both read stage to know what's actually live versus still in flight.
