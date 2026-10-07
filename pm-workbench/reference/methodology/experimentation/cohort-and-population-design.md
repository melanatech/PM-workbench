# Cohort and Population Design

## The three constructs, and when each is valid

A shipped change implies one of three fundamentally different comparisons, depending on how it
actually gated:

| Gating mechanism | Valid construct | What makes it valid |
|---|---|---|
| A real the experiment platform experiment (randomized) | Randomized A/B | Random assignment is what makes "the two groups differ only by treatment" a defensible claim in the first place |
| A feature flag / config gate, unconditionally rolled out to whoever opts in or qualifies | Adopter-vs-non-adopter | Only valid as a *description* of who used what, never as a causal claim — adopters chose to adopt, which is exactly the self-selection a randomized test exists to remove |
| No gating at all — shipped to everyone at once | Population-wide pre/post | The only construct available when there's no control group at all; can show something moved, can never show *why* on its own |

Picking the wrong one from this table isn't a minor framing error — it's the difference between a
claim that survives scrutiny and one that doesn't. The Product Analyst agent's Mode 1 checklist
already names this as its first check: "Identify the real gating mechanism from code, not from a
guess." This file is the reasoning behind why that check exists, not a replacement for doing it.

## Why adopter-vs-non-adopter needs an extra check before it's usable at all

Even once you've correctly identified "this is an adopter-vs-non-adopter comparison, not a
randomized one," it can still be broken in a way that has nothing to do with self-selection: the
non-adopter side has to actually be one population. A "didn't adopt the new tool" bucket that
secretly contains both "actively uses the legacy version of this job" and "never does this job at
all" isn't a comparison group, it's two different populations wearing one label — see
`common-pitfalls.md`'s comparison-group-homogeneity entry for a real example and how to check it.

## Why the pre/post window matters as much as the population

A population-wide pre/post (or an adopter-vs-non-adopter comparison over time) is only as
trustworthy as its window choice. A longer "before" window than "after" window will mechanically
inflate any metric that's about *reach* (did this account ever do X) simply because it had more
calendar time to accumulate a "yes" — independent of whether the change did anything at all. See
`common-pitfalls.md`'s matched-window entry.

## What a randomized A/B still needs to get right

Randomization solves self-selection, but not everything: the randomization *unit* has to match
the thing that's actually supposed to behave consistently across the comparison. Randomizing a
session/visitor for an account-level product lets the same account bounce between arms across
visits, which breaks the experience and makes any depth-shaped metric (one needing a consistent
identity across the whole window) unusable — `designing-experiments`' own Workflow step 2 already
checks this before finalizing a design; this file just names why it matters.
