---
name: explore-brief
description: >
  Use when the PM asks for a product brief, explore brief, check-in brief, options
  for INIT-/COM-, or alternatives before a PRD. Runs /discover explore-brief.
  Never skip prd-context-gatherer or jump to a single UI pattern first.
---

# explore-brief

Plain-language entry for **`/discover explore-brief`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/explore-brief.md` in full (same gates as the slash command). Prefer dispatching via the `/discover` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / gather / frame-before-options / gate requirement in that file — including `context_preflight.py` before the gatherer, and citing hit `primary_sources` (drafts are not evidence).

Forbidden: generic brainstorm without the gatherer when INIT/COM is named; leading with one UI pattern; blank-slate `repos/` when preflight has hits; running `/build prd-package` unless the PM asked for a full PRD.
