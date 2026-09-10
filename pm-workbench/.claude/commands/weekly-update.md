---
description: Draft the weekly leadership update from maintained state, not memory
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

**Step 0 — reconcile before generating** (per CLAUDE.md rule 2): refresh current Jira status via the bookmarked view; check whether local decisions/commitments are older than what Jira/Confluence now shows; list any conflicts or gaps and ask ONLY for genuinely missing inputs ("I have Jira, decisions, risks; I'm missing this week's OKR values and Tuesday's leadership notes — add now, or proceed with those sections marked incomplete?"). Never generate a polished update from unverified state.

Then read maintained state — this update is generated, not recalled:
- `registers/initiatives.csv` — what's in flight and at what stage, for the "what's moving" framing
- `reference/context/current-priorities.md` — frame the update against my stated priorities, and flag if the week's actual activity diverged from them (that divergence is itself worth a line to leadership)
- Latest `outputs/weekly/*-jira-reconcile.md` (what moved, what's stale)
- `registers/commitments.csv` — due, completed, or missed since last update
- `registers/decisions.csv` and `registers/risks.csv` — new or changed entries
- Latest `outputs/weekly/*-discovery.md`
- Latest OKR narrative from `/okr-refresh` outputs
- Last week's update in `outputs/weekly/` (style + continuity reference)

Structure — leading with change, never repeating background:
1. **What changed since last update**
2. Outcomes achieved, with evidence (metric or link)
3. Decisions made
4. Upcoming commitments
5. Risks and mitigation
6. **Specific leadership asks**

Then two checks against last week's update: strip any repeated background, and **flag any commitment mentioned last week that this draft doesn't address** — silently dropped promises are exactly what this system exists to prevent.

Produce an email version and a wiki-format version. Save to `outputs/weekly/[date]-leadership-update.md`. If browser drafting is available and I approve interactively, pre-fill the email draft or wiki page — and stop before send/publish.

**If living context is blank** (`current-priorities.md`): note it rather than silently generating unframed output — a one-line "no stated priorities this week" is honest; fabricated framing is not.
