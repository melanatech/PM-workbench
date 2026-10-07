# Pre-Registration and the Peeking Problem

## Why checking early and often is the problem, not just being impatient

Every time an experiment's results get checked before it's finished, that check is itself a
chance for a real-no-difference test to look significant purely by chance — checking 5 times
during a run inflates the effective false-positive rate well above the pre-registered alpha, even
though each individual check used the "right" threshold. This isn't about discipline or
impatience; it's a structural property of repeated significance testing, and it's why "we peeked,
saw a strong effect, and stopped early" is a specific, nameable methodological error, not just bad
luck if the effect later fades.

## What pre-registering actually buys

Pre-registering a hypothesis, primary metric, guardrails, sample size, and duration — *before* any
data exists — closes off the two most common ways a result gets quietly reinterpreted after the
fact: choosing a different metric because the original one didn't move, and stopping early because
an interim check looked good. `framing-metrics`' own hard rule states this directly for the
`expected_direction` field: set it from reasoning about the change's intent, never by looking at
data first, and never revise it after seeing numbers. The same logic extends to every other
pre-registered field, not just direction.

## This plugin's own enforcement of it

`designing-experiments` builds a decision rule and sample-size/duration estimate before the
experiment exists, specifically so there's nothing left to decide once data starts coming in
except "did we hit the pre-registered number, in the pre-registered direction, yes or no." This
file is the reasoning behind why that skill's steps are ordered the way they are — it isn't a
restatement of those steps, and doesn't need to be re-read to run the skill itself.

## A pre/post readout is not a workaround for this

It can be tempting to treat "we didn't have a real experiment, so we're just reading the pre/post
numbers whenever we want" as a lower-rigor substitute that avoids the peeking problem by not being
an experiment at all. It doesn't — `measuring-impact`'s own hard rules are explicit that a pre/post
comparison is never causal (name the confounders, every time) precisely because it has none of a
real experiment's protections, peeking-related or otherwise. An INCONCLUSIVE pre/post readout is
the signal to reach for `designing-experiments`, not to keep re-checking the same pre/post numbers
hoping a later look resolves the ambiguity.
