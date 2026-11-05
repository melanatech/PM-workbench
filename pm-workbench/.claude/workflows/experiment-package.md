---
description: Experiment design with adversarial review gate
model: opus
argument-hint: [what we want to test / opportunity id]
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

**Step 0 — preflight:** `python3 scripts/context_preflight.py --root <live> --topic "$ARGUMENTS"` before triage/design. Reuse prior experiment designs or related discovery hits; do not blank-slate when the index already covers the opportunity.

## Uncertainty triage — run this BEFORE designing anything

Most things called "experiments" don't need an experiment, and none of the cheap
cases need the five-reviewer panel. Classify first:

1. **Usability / "will they understand it" question** → this is *research*, not an
   experiment. Route to `/discover research-plan`. Stop.
2. **Instrumentation or operational validation** ("does the event fire", "does the
   job retry") → this is a *QA / monitoring plan*, not an experiment. Produce a
   short verification checklist. Stop.
3. **Low-risk directional test** (small, reversible, no major commitment rides on
   it) → *lightweight* review: one reviewer sanity-checks the design. No panel.
4. **High-stakes causal decision** (a real, hard-to-reverse bet depends on the
   result) → *full adversarial panel* (the five reviewers).

Only case 4 earns the panel. State which case this is and why before proceeding.
The design-stage sample-size math is still appropriate in cases 3–4; official
outcomes still come only from the experiment platform / approved analysis.


Experiment package for: $ARGUMENTS

**Refuse to produce a polished proposal if foundations are missing.** Required first: the decision this experiment informs (with the decision for EACH possible result — including null), supporting evidence (evidence_ids), and a baseline (from `state/okr-history.csv`; if none, stop and say what baseline pull is needed).

**Design:** hypothesis; eligibility; treatment/control; assignment unit; primary metric (per its `reference/metric-definitions/` contract); guardrails; minimum meaningful effect; sample-size scenarios (show the math — compute honestly, this is design-stage arithmetic, not official reporting); duration; instrumentation requirements; stopping rules; segment cuts; novelty/seasonality/contamination risks. Platform constraints (from `reference/templates/experiment-plan-template.md` and `reference/context/workflow-notes.md` § experiment-package, when the workspace has them): pick a test type the platform supports; respect its limits on decision and guardrail metrics; a metric with params may need a saved custom metric first; for lagging metrics the platform does not track, name where they are measured and the significance method; state one-sided or two-sided per decision metric (when two org guides disagree, report the conflict, do not pick silently). Name who was consulted (platform intake, review board, office hours) or mark it `[NEEDS INPUT]`. Before locking metrics/power, skim `reference/methodology/experimentation/` (sample size, cohorts, guardrails, peeking, pitfalls). Post-ship measurement of a release uses `/report ship-signal` (verdicts `MOVED`/`FLAT`/`INCONCLUSIVE`/`DATA GAP`) — do not reinvent that loop here.

**Adversarial review — dispatch to five subagents in parallel** (`causal-reviewer`, `instrumentation-reviewer`, `ux-harm-reviewer`, `business-value-reviewer`, `ops-feasibility-reviewer` in `.claude/agents/`), each given only the design, not each other's opinions or who wrote it — that isolation is what keeps the review honest. Collect all five verdicts.

Label the panel verdicts "AI pre-review — not validated by stakeholders." If any FAIL: the experiment isn't ready. Show me the design plus which reviewer(s) failed it and why, and stop there — don't revise-and-resubmit automatically, since seeing what a real reviewer would push back on is the point.

If all PASS (with or without conditions): proceed to the final experiment card (shape: `reference/templates/experiment-plan-template.md`, all fifteen sections; section 15 is the portal configuration sheet) + pre-launch checklist + analysis template (written BEFORE results exist, so success criteria can't drift) → `outputs/experiments/[name]/`. Update `registers/initiatives.csv`: stage=experiment, experiment_path, last_updated — linking to the same row as the PRD/prototype if one exists for this feature. Facts only I or engineering can supply (app label, SDK bucketing type, traffic type and bucketing id, owner usernames, experiment ticket key, scorecard template) stay `[NEEDS INPUT: …]`; never guess them. Creating or saving anything in the experimentation platform's portal is a Tier 3 write: if browser access works, pre-fill from section 15 in the Test environment with my approval and stop before Save, leave traffic allocation at 0%, and never start Prod. After an approved write, re-read the portal and verify against section 15. Use the same sheet if there is no browser access: hand it over for manual entry.

**Monitoring.** The design names health metrics, guardrails, exposure balance (sample ratio), novelty decay, support volume, a qualitative replay sample, and the decision rule. Sources stay placeholders until a live monitoring-sources file maps them. Official outcomes still come only from the experiment platform.

**Required input.** A hypothesis needs a described treatment (what actually changes for whom), not just an outcome wish. If the treatment isn't stated, ask before designing anything.
