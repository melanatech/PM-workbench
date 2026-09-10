---
description: Refresh the product strategy from accumulated system state
model: opus
---

Execution mode: **deep** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

**Step 1 — dispatch to the `strategy-synthesizer` subagent** for the change report BEFORE rewriting anything: it reads `registers/evidence.csv`, `state/okr-history.csv`, the competitive log, and `learning/` all at once. **In parallel, dispatch `internal-docs-reader`** for any market research, analyst reports, or strategy documents sitting in the shared drive/Confluence/`reference/user-research/` that aren't yet reflected in those registers. Combine both into assumptions strengthened/weakened, new + contradictory evidence, opportunities to add/deprioritize, competitive/feasibility shifts.

**Step 2 — revenue ideas get explicit models, not vibes:** eligible customers, expected adoption, revenue mechanism, incremental revenue estimate, cost to serve, retention/expansion effect, evidence level (cite evidence_ids), key assumptions, sensitivity, validation plan.

**Step 2.5 — read `registers/initiatives.csv` for the full portfolio view:** what's at each stage, what's stalled (last_updated old relative to its stage), what's shipped-and-should-be-evaluated-for-impact-by-now. This is what keeps the strategy doc grounded in what's actually in flight, not just what evidence exists.

**Step 3 — package** → `outputs/strategy/[date]/`: updated strategy doc (same throughline as prior versions — deepen, don't reinvent); one-page leadership memo; prioritization table; revenue models; strategic risks; anticipated objections + responses; proposed roadmap changes; experiments needed before investment; discussion-deck outline.

**First run:** if no current strategy doc exists in `outputs/strategy/` or `reference/`, STOP and ask for it (a wiki/shared-drive link for `reference/links.csv`, or a file). A change report against no baseline is fiction. If the person confirms no strategy doc exists at all, say so and offer to draft an initial one instead — labeled as initial, not as an update.
