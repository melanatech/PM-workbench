# Guardrail and Decision Metrics

## The two roles, and why conflating them is a mistake

A **decision metric** is what determines win/loss/inconclusive — the thing the experiment exists
to move. A **guardrail metric** is something that must not regress, whether or not the experiment
succeeds — it's there to catch a real but unintended cost of the change, not to help the change
win. the experiment platform's own schema encodes this as a role, not a metric-type taxonomy: the same physical
metric could be a decision metric in one experiment and a guardrail in another, depending on what
the experiment is actually testing.

Treating a guardrail as a secondary decision metric (hoping it moves too) or a decision metric as
"basically a guardrail" (not holding it to the same rigor) both produce a worse experiment than
picking the role correctly up front.

## Avoiding metric sprawl

the experiment platform experiments can register up to 6 decision metrics, but the median is 1-3 — more isn't
more rigorous, it's more chances for one of them to hit significance by chance alone, and more
work to reconcile disagreeing results into one ship/kill call. `framing-metrics`' own hard rule
sets the practical default at 2 proposals per change, allowing a third only when the change's own
rationale names a mechanism the first two genuinely can't isolate from each other — stated
explicitly, not reached for as a default way to "cover more ground."

## A guardrail has to name a real failure mode

"Make sure nothing broke" is not a guardrail — it's the absence of one. A real guardrail names the
*specific* thing the treatment's mechanism could plausibly break: "this prompt could add friction
to the completion flow, suppressing completion rate" is checkable and falsifiable; "monitor for
regressions" is not. If a design's primary metric measures *depth* (does more, once already
converting), it needs a *reach* guardrail (converts at all) — a depth win bought by quietly losing
reach is exactly the kind of failure a vague guardrail would miss and a specific one catches.

## iGCR eligibility, conceptually

Not every significant win becomes an annualized revenue number. iGCR (incremental GCR) requires
the *decision* metric itself to be a GCR-shaped conversion/funnel metric, statistically
significant, with the experiment's achievement badge (driven by its pre-registered alpha) setting
what fraction of the annualized number actually gets credited — see `sample-size-and-power.md`'s
badge/credit-factor table for the literal thresholds. This section only exists to explain why
the eligibility gate exists at all: it's a filter against claiming full annualized revenue for
wins that don't actually meet the rigor bar for it, not an arbitrary bureaucratic hurdle.
