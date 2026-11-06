---
name: explore-brief
description: >
  Use when the PM asks for a product brief, explore brief, check-in brief, options
  for INIT-/COM-, or alternatives before a PRD. The brief discovers what the thing
  is and what it does. Lead with the problem frame, user stories, and alternatives.
  Then what the requirements should focus on, how to discuss it with the team,
  and how to sell it cross-functionally. Precursor to a PRD.
  Runs /discover explore-brief. Never skip prd-context-gatherer or jump to a
  single UI pattern first.
---

# explore-brief

Plain-language entry for **`/discover explore-brief`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/explore-brief.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / gather / frame-before-options / gate requirement in that file — including `context_preflight.py` before the gatherer, and citing hit `primary_sources` (drafts are not evidence).
4. The written brief is the product, not the research log. A source is a short citation on the claim. Do not write what was looked at, read, or reviewed, or what each of those said.
5. Lead with the original job: problem frame, user stories, and alternatives. Then what this is and what it does, what the requirements should focus on, how to explain it so the team discussion is productive, and how the PM sells it cross-functionally. It is the precursor to a PRD.

Forbidden: generic brainstorm without the gatherer when INIT/COM is named; leading with one UI pattern; blank-slate `repos/` when preflight has hits; running `/build prd-package` unless the PM asked for a full PRD.
