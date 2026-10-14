---
name: scenario-guide
description: >
  Optional evaluator/demo Scenario Guide panel for prototypes (look/do/try scripts
  keyed by concept or persona). Use when building or updating a multi-concept
  prototype, when the PM asks for a walkthrough guide, demo script, or "like
  ScenarioGuide", or when prototype-build offers the optional guide. Not merchant
  onboarding. Not required for every prototype.
---

# scenario-guide

Optional add-on for **`/build prototype-build`**.

1. Read `.claude/workflows/_scenario-guide.md` (do not invent a different panel pattern).
2. Prefer `ScenarioGuide` from `@pm-live/prototype-kit` when `prototypes/_shared/` exists; keep scripts local. Else adapt `prototypes/explanations-transactions` wrapper/recipe.
3. Key scripts by the prototype’s variant switcher (concept / persona / surface). Rewrite step copy for this UI — never paste Money Journey / companion scripts from another app.
4. Wire a **Guide** toggle next to the variant controls; desktop sidebar / mobile sheet; Escape closes.
5. Update the prototype README and, if reusable, `reference/design/prototype-components.md`.

Forbidden: forcing a Guide on every prototype; auto-playing clicks through the product; claiming UX Guardrails pass because a Guide exists.
