---
description: Draft the weekly leadership update from maintained state, not memory; on PPP weeks also draft the PPP
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

**Step 0 — reconcile before generating** (per CLAUDE.md rules 2 and 3): refresh current Jira status via the bookmarked view; check whether local decisions/commitments are older than what Jira/Confluence now shows; list conflicts and material gaps. For a missing fact that could change an outcome, trend, priority, or leadership ask, ask a focused, batched question and wait before drafting (for example: "I have current Jira, decisions, and risks; I'm missing this week's OKR values and Tuesday's leadership notes. Please provide them, or explicitly confirm that you want a provisional update with those sections incomplete."). Do not generate the update in the same turn as that question. Only proceed with a partial draft if I explicitly choose it; mark the whole update **PROVISIONAL** and put `[NEEDS INPUT: ...]` at every affected claim or section. Keep assumptions separate from sourced facts and never infer missing metrics or outcomes.

Then read maintained state — this update is generated, not recalled:
- `registers/initiatives.csv` — what's in flight and at what stage, for the "what's moving" framing
- `reference/context/current-priorities.md` — frame the update against my stated priorities, and flag if the week's actual activity diverged from them (that divergence is itself worth a line to leadership)
- Latest `outputs/weekly/*-jira-reconcile.md` (what moved, what's stale)
- `registers/commitments.csv` — due, completed, or missed since last update
- `registers/decisions.csv` and `registers/risks.csv` — new or changed entries
- Latest `outputs/weekly/*-discovery.md`
- Latest OKR narrative from `/report okr-refresh` outputs
- Last week's update in `outputs/weekly/` (style + continuity reference)
- Status trackers on Confluence (`reference/links.csv` L-021 weekly tracking by milestone, L-022 Q4 roadmap, L-023 report builder and CH meetings tracker): read them via the Atlassian MCP for the latest notes, and say which version you read. They feed the update; they are not authoritative. Jira wins on dates and status, and any disagreement is reported as a conflict.

Structure — leading with change, never repeating background (shape: `reference/templates/leadership-update-template.md`):
1. **What changed since last update**
2. Outcomes achieved, with evidence (metric or link)
3. Decisions made
4. Upcoming commitments
5. Risks and mitigation
6. **Specific leadership asks**

Then two checks against last week's update: strip any repeated background, and **flag any commitment mentioned last week that this draft doesn't address** — silently dropped promises are exactly what this system exists to prevent.

Produce an email version and a wiki-format version. Save to `outputs/weekly/[date]-leadership-update.md`. If browser drafting is available and I approve interactively, pre-fill the email draft or wiki page — and stop before send/publish.

**PPP weeks — also draft the PPP, alongside the leadership update (not instead of it).** PPP Fridays are 2026-10-09 and every 14 days after (10-23, 11-06, …); publish Friday 5pm, leadership reviews Monday. Say at the top whether this is a PPP week. If it is, use `reference/templates/ppp-template.md` as the format, apply the same Step 0 reconciliation, and save to `outputs/weekly/[date]-ppp.md`. Build it from maintained state:
- **1 OKR status:** the L2 KRs owned are not recorded yet, so write the KR table as `[NEEDS INPUT: L2 KRs owned]` rather than guessing. Once KRs are recorded, take values only from `state/okr-history.csv` with the as-of date (CLAUDE.md rule 5); never recompute.
- **2 Plan and progress:** shipped and in-flight work from `registers/initiatives.csv` and the latest `outputs/weekly/*-jira-reconcile.md`; Jira wins on dates, status and % complete. Include Jira keys. Expected impact and experiment slide links only where a source gives them, otherwise `[NEEDS INPUT]`. Key learnings from recent discovery, experiments and `learning/`.
- **3 Problems:** open items from `registers/risks.csv`, blocked or overdue items from `registers/commitments.csv` and the Jira reconcile, and the same specific asks used in the leadership update. Do not invent owners or ETAs.
- **4 Supporting other KRs and 5 Team health:** no register holds these; leave `[NEEDS INPUT]` unless I supply them. Never infer team health.
- **Status colors (🟢🟡🔴):** mark them "proposed" with the evidence; I confirm them.
- PPPs are posted to Confluence or Slack (the exact page or channel is not recorded). In this workflow stop at the saved draft: do not publish, post, or pre-fill either.

**If living context is blank** (`current-priorities.md`): note it rather than silently generating unframed output — a one-line "no stated priorities this week" is honest; fabricated framing is not.
