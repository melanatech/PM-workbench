# Sample Size and Power

## What MDE actually means

The minimum detectable effect (MDE) is the smallest true change a test is built to notice, not
the smallest change that matters to the business — those are different numbers, and confusing
them is the single most common power-calculation mistake. Set `mde_relative` from "what change
would actually justify shipping or killing this," not from "what number makes the sample size
come out small." `designing-experiments`' own hard rule (step 4 of its Workflow) says the same
thing: a too-small MDE chosen just to look rigorous is how a design ends up asking for an
impractically large sample for no real reason.

## Alpha and power, in plain terms

- **Alpha (significance level, default 0.05)** — the chance of calling a real-no-difference test
  a winner anyway (a false positive / Type I error). Lower alpha = harder to falsely claim a win,
  but needs more sample to still detect a real effect.
- **Power (default 0.80)** — the chance of actually detecting a true effect of the size you set
  as your MDE, if it's really there (1 minus the false-negative / Type II error rate). Higher
  power = less risk of missing a real win, but needs more sample too.

These two knobs trade off against sample size in opposite directions from each other but the same
direction as MDE: smaller MDE, lower alpha, or higher power all mean *more* sample needed, not
less. There's no way to get "detect a smaller effect, with more confidence, faster" — pick which
one matters most for this decision and let the others sit at their defaults (0.05 / 0.80) unless
there's a specific reason to move them.

## Duration, roughly

Once a script gives you `n_per_arm`, duration is `(n_per_arm × variants) / daily_eligible` days,
adjusted for whatever fraction of daily traffic is actually allocated to the experiment (if only
50% of eligible traffic is randomized in, double the raw estimate). This is a sanity-check
intuition only — it exists so a proposed design's duration doesn't come as a surprise, not to
replace the real number.

## Always the script, never a hand estimate

`designing-experiments/scripts/power_calc.py` computes the real number from
`--baseline-rate`, `--mde-rel`, `--daily-eligible`, `--alpha`, `--power`, and `--variants`. That
skill's own hard rule is explicit: every `n_per_arm` and `est_duration_days` that ends up in a
real proposal must be the script's own printed output for the exact inputs stated alongside it —
never a number "roughly matching" what this file's intuition above would suggest. This file exists
so the *inputs* to that script (especially `mde_relative`) get chosen for the right reason, not so
its *output* gets second-guessed or reproduced by hand.

## GoDaddy-specific: alpha and achievement-badge credit factors

the experiment platform ties the `alpha_value` an experiment pre-registers to an achievement badge
(Bronze/Silver/Gold/Platinum), and that badge sets what fraction of a win's iGCR actually gets
credited when it's annualized — 0 = none, 1 would be all of it:

| Badge | Alpha requirement | iGCR credit factor (0 = none, higher = more) |
|---|---|---|
| Bronze | frequentist, alpha > 0.2 | 0 |
| Silver | frequentist, alpha ≤ 0.2 (+ documented hypothesis, ≤3 decision + ≤3 guardrail metrics) | 0.335 |
| Gold | Silver requirements + alpha ≤ 0.1 | 0.433 |
| Platinum | Gold requirements + configured/measured on the experiment platform | 0.53 |

This is a real business incentive around alpha that's distinct from pure statistical rigor — and
it runs the opposite direction from what you'd guess. The conventional 0.05 significance level
already clears every tier's alpha bar (0.05 ≤ 0.1), so there's no credit for going tighter than
0.1; the actual risk this table creates is registering too *loose* an alpha. A Bronze-badged win
(alpha > 0.2) gets zero iGCR credit no matter how real the effect is. Source: Confluence
"Experiment Governance & Validation Guidelines" (space REN, page 4140533098) — check that page
directly before citing exact numbers in a real proposal; GoDaddy governance pages change without
this file being told.
