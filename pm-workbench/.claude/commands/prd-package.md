---
description: PRD package - grounded context, readiness gate, stakeholder pre-review, and prototype reconciliation
model: opus
argument-hint: [feature or problem]
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Build the PRD package for: $ARGUMENTS

**Step 0 — dispatch to `prd-context-gatherer`, and in parallel to `internal-docs-reader`.** The first reads evidence, code findings, OKR baseline, competitive log, and prior decisions/risks for this feature; the second checks the shared drive, wiki research pages, and `reference/user-research/` for anything relevant that isn't already reflected in those registers. Everything below works from both briefs instead of re-reading files from scratch.

**Step 1 — readiness report**, using that brief: evidence strength (with citations), problem clarity, target-user clarity, baseline metric availability, unresolved technical questions, dependencies, revenue/retention hypothesis, measurement readiness, and the gaps the gatherer flagged. **If evidence is thin or there's no baseline, say "not ready" and list what's needed — a polished PRD on a weak foundation is a trap, and this gate is what keeps your docs credible.**

**Step 1.5 — register the initiative.** Check `registers/initiatives.csv` for an existing row for this feature; create one if absent (stage=prd) or update it (prd_path, related_evidence_ids from the gatherer's brief, related_okr, last_updated). This is the row every other command checks against — it's what lets a Jira update or a piece of discovery evidence find its way back to this PRD later.

**Step 2 — draft the package**, to `outputs/prds/[feature]/`:
1. Full PRD (structure from `reference/templates/` examples)
2. One-page executive pre-read: problem in two sentences, the bet, cost/risk, the specific ask
3. Engineering + design question list
4. Assumptions requiring validation
5. Scope options: minimum / recommended / expanded, with tradeoff table
6. Proposed Jira epic + child structure, drafted for the internal tool

**Step 3 — stakeholder pre-review, bounded by execution mode.** In **Standard** (the default): pick the **1–2 reviewers whose angle this PRD most needs** — say which and why (default: `eng-feasibility-reviewer` + `business-revenue-reviewer`; swap in `design-ux-reviewer`, `data-instrumentation-reviewer`, or `customer-facing-reviewer` when the feature is UI-, instrumentation-, or support-heavy). The full five-reviewer panel runs only in **Deep** mode or when I ask for it. Run the review ONCE, when the draft is close to shareable — not on every revision loop. Whichever reviewers run: the same agents `/prototype-build` uses. Each sees only the PRD, not each other. This isn't a hard gate the way the experiment panel is — a PRD is allowed to go to real stakeholders imperfect — but every FAIL or CONDITION becomes an entry in the PRD's **Anticipated objections and responses** section. **Label the panel's output "AI pre-review — not validated by any stakeholder"** — these are model calls sharing one context and one set of blind spots, useful for completeness, never a substitute for your real engineering lead's feasibility read or actual leadership alignment.

**Step 3.5 — stakeholder buy-in plan.** Alongside the package, produce: who must validate (eng/design/analytics/CS/leadership), a pre-wire sequence (validate technical assumptions privately with eng BEFORE the group review; leadership gets the one-pager before the meeting), the likely objection from each stakeholder given what the pre-review surfaced, and the specific decisions the review meeting must produce. The AI prepares the influence work; the relationships and the room are yours.

**Step 4 — maintain the Feature Contract.** Draft/update `outputs/prds/[feature]/contract.md` (scope, rules, permissions, states, edge cases, instrumentation, open decisions) as part of the package — it's the shared interface the prototype builds against. If `prototypes/[feature]/` exists, dispatch `prd-prototype-reconciler` to reconcile both artifacts against the contract. Surface any discrepancies before I finalize — better to catch "the PRD says X but the prototype does Y" here than after both have shipped to different stakeholders.

**Step 5 — after real feedback comes in:** rerun with the comments pasted in; group them (clarification / new requirement / scope expansion / technical constraint / disagreement / decision needed / already addressed) and propose one reconciled revision — not comment-by-comment patchwork. Re-run Step 4 if the prototype exists, since the PRD just changed.

**Required input — do not conjure a PRD from a name.** If $ARGUMENTS is only a feature name, ask before drafting: the problem in one or two sentences, the goal/metric it should move, and the intended audience. A readiness gate can run on accumulated context; a PRD cannot be written from it alone.
