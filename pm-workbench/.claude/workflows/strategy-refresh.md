---
description: Refresh the product strategy from accumulated system state, or draft the first memo from scratch
model: opus
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so. Deep is one word away (`run this in deep mode`). This workflow stays on opus in `routes.json` in every mode.

The Standard reviewer is one blind pass of `strategy-red-team-reviewer`. Deep still runs that one pass. Optional persona lenses are Deep and opt-in only. They are not dispatched unless the PM asks.

Context dependencies: soft: current-priorities, product-areas, kr-metric-map, audiences, people | hard: none

**Step 0 — preflight:** `python3 scripts/context_preflight.py --root <live> --topic "strategy $ARGUMENTS"`. Pass hits into the synthesizer (refresh) or the discovery phase (from scratch). Index the memo when written (`kind=strategy`).

**From-scratch mode.** Use this when no strategy memo exists under `outputs/strategy/` or `reference/`, or when the PM says "from scratch" or "strategy from scratch". A change report against no baseline is fiction. Do not stop to demand a wiki link before drafting. If the PM says a strategy already lives somewhere else, ask for that link in the same batch as Cold start and do not draft over it.

1. Follow the **Discovery phase** and **Cold start** in `.claude/workflows/roadmap-build.md` (preflight reuse, `discovery-source-reader`, `competitive-capture-agent` only when no fresh `state/competitive/` capture exists, `scripts/web_search.py` → `state/web-search/`, max 12 sources). Do not create a second gatherer. Reuse a fresh competitive capture; do not re-scan.
2. Cold start asks once, in one batch, before Product Objectives or Key Initiatives are written as if the PM stated them. Label derived lines **derived, not stated priorities**. Wait for a yes. Unattended: write the derived list, mark those sections `[NEEDS INPUT: confirm derived priorities]`, append `BLOCKED: confirm derived priorities`, and do not present them as decided.
3. Draft the memo in the shape of `reference/templates/product-strategy-memo-template.md` (that filename, not a new outline). Keep its heading order: Vision statement, Learnings & Discovery, the year-stamped Strategy heading, Product Objectives, Key Initiatives, Key dependencies/risks. Label the file the **initial version**, not an update. Save it under `outputs/strategy/[date]/`.
4. Every claim cites a source from this run. **No invented dates** — same rule as roadmap-build: a date only when a tracker issue or a commitment states it and the line cites that source; otherwise `[NEEDS INPUT]`. Do not invent market size, eligible-customer counts, adoption, metric values, or revenue estimates.
5. Then the red-team pass below.

A refresh (a memo already exists, and the PM did not say from scratch) uses Steps 1–3 below: synthesizer change report first; deepen, don't reinvent.

**Step 1 — dispatch to the `strategy-synthesizer` subagent** for the change report BEFORE rewriting anything: it reads `registers/evidence.csv`, `state/okr-history.csv`, the competitive log, and `learning/` all at once. **In parallel, dispatch `internal-docs-reader`** for any market research, analyst reports, or strategy documents sitting in the shared drive/Confluence/`reference/user-research/` that aren't yet reflected in those registers. Combine both into assumptions strengthened/weakened, new + contradictory evidence, opportunities to add/deprioritize, competitive/feasibility shifts.

**Evidence sufficiency gate:** before writing the refresh, identify missing, stale, or inaccessible sources and facts that could materially change strategic priorities, revenue/retention estimates, or recommendations. Ask a focused, batched question and wait for the missing evidence or clarification; do not present an updated strategy as complete while the gap remains. If I explicitly ask for a provisional refresh, label it **PROVISIONAL**, mark every affected claim/model/table cell `[NEEDS INPUT: ...]`, and separate sourced facts from assumptions. Do not invent market size, eligible-customer counts, adoption, metric values, or revenue estimates to fill the model.

**Step 2 — revenue ideas get explicit models, not vibes:** eligible customers, expected adoption, revenue mechanism, incremental revenue estimate, cost to serve, retention/expansion effect, evidence level (cite evidence_ids), key assumptions, sensitivity, validation plan.

**Step 2.5 — read `registers/initiatives.csv` for the full portfolio view:** what's at each stage, what's stalled (last_updated old relative to its stage), what's shipped-and-should-be-evaluated-for-impact-by-now. This is what keeps the strategy doc grounded in what's actually in flight, not just what evidence exists.

**Step 3 — package** → `outputs/strategy/[date]/`: updated strategy doc (same throughline as prior versions — deepen, don't reinvent); one-page leadership memo; prioritization table; revenue models; strategic risks; anticipated objections + responses; proposed roadmap changes; experiments needed before investment; discussion-deck outline.

**Red team (Standard and Deep).** Dispatch `strategy-red-team-reviewer` once on the draft plus the sources it cites. Blind: not the chat, not your reasoning. One pass. Put findings in an **Anticipated objections** section. Do not silently rewrite the draft. Fast skips this dispatch. The saved memo still has the section; if the pass did not run, the section says why.

## Deep only — optional persona lenses

Not in the default flow. Not in Fast or Standard. Only when the PM opts in and the mode is Deep, after the usage estimate and the yes.

These are role lenses, not impersonation. Build each lens from recurring concerns in `reference/context/people.md` that have a dated source. Drop a concern with no date. One blind pass per lens: the draft and its cited sources only. Keep the concerns, never transcripts. Findings join **Anticipated objections**. Do not add reviewer agents for this.

**Step 4 — Publish.** Defaults: `audience: internal`, `formats: [md]`. The strategy folder stays the internal source. Produce an external version only when the PM asks, then follow Audience and formats and Publish in `.claude/workflows/_protocol.md`. This workflow is not Fast: when an external version is written, dispatch `external-readiness-reviewer` once on the rendered file and the audience line. Publishing or sending is Tier 3 and waits for an explicit yes. Do not call a wiki create API or a chat send API from this step.
