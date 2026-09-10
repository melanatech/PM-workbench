---
description: "Analyze experiment results against the pre-registered design"
argument-hint: "[results export path] [experiment name]"
---

Read the results at the given path against `outputs/experiments/[name]/` (card + analysis template).

If `scripts/` has an analysis script for this experiment, run it for the official stats; otherwise compute significance, effect size, and confidence interval — and label them as needing verification before executive use.

In parallel, dispatch the pre-registered design + raw results to the `results-integrity-reviewer` subagent — it never sees your narrative, only the original design and the numbers, so it can independently flag goalpost-moving or post-hoc segment-fishing without being anchored by whatever conclusion you've already drafted.

Decision memo, strictly separated: (1) observed results, (2) interpretation, (3) recommendation per the PRE-REGISTERED decision rules, (4) the integrity reviewer's verdict — if FLAGGED, lead with that, not bury it.

Ship / kill / iterate call with reasoning → `outputs/experiments/[name]/results-memo.md`. Once I confirm the ship/kill/iterate call, **write the decision to `registers/decisions.csv`** — a confirmed call is exactly the kind of decision the whole system exists to not lose track of, and it shouldn't sit as an unpersisted chat message. **Update `registers/initiatives.csv`**: stage=shipped or stage=killed, related_decisions linking the new decisions.csv row. If this initiative has a PRD, flag explicitly whether the PRD's original hypothesis held — that's a direct input to `/strategy-refresh`'s next run. Propose the matching Jira update as a draft.
