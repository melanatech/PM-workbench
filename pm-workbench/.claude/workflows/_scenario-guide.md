# Scenario guide recipe — optional evaluator walkthrough for prototypes

Use when a prototype needs a **scripted demo/QA panel** so someone new can run
the same story twice. Not merchant onboarding. Not always required.

Reference: `@pm-live/prototype-kit` `ScenarioGuide` when `prototypes/_shared/` exists;
feature apps keep scripts local (see `prototypes/[feature]/src/scenarios.js`).
When the prototype has a `src/data` fixture, Scenario Guide text reads values through selectors
(do not hardcode fixture numbers into step copy).

## When to add

Offer (do not force) when any of these are true:

- Multi-concept / multi-persona toggle where evaluators get lost
- Stakeholder walkthrough in the next ~week
- Flows that chain expand → panel → deep-link (easy to skip a step)
- Companion / “ask” steps that must be spoken consistently

Skip for single-screen throwaways and static one-pagers.

## Framework (copy shape, rewrite scripts)

| Piece | Guidance |
|---|---|
| Step types | `look` (observe), `do` (click/open), `try` or `ask` (engage companion / concept affordance) |
| Scripts | Static map keyed by **variant id** (concept, persona, surface) — not one global script |
| Live data | Prefer `text: (data) => …` when numbers/dates come from mock data (avoids drift) |
| Navigation | Optional **Go →** that switches variant or route via **in-product** controls; footer: narrate, don’t replace nav |
| Shell | `guideOpen` + header **Guide** toggle; desktop ~280px push sidebar; mobile bottom sheet + backdrop; Escape closes |
| Swap | Changing the concept/persona chip reloads which scenarios show; first scenario expanded by default |

## Port steps

1. Import `ScenarioGuide` from `@pm-live/prototype-kit` (or copy/adapt if `_shared` is missing). Put **scripts** in the feature app.
2. Wire toggle into the prototype controls bar (same bar as variant switcher).
3. Write **one scenario per variant** first; expand only if demos need a second path.
4. Re-walk each step against the live UI (labels, Esc, focus).
5. Catalog only unpromoted local forks in `reference/design/prototype-components.md`.
6. Document in the prototype README: Guide is evaluator-only.

## Anti-patterns

- Hard-coded amounts that disagree with the mock UI
- Guide that auto-clicks the product for the user (narrate + optional Go, don’t puppet)
- Treating Guardrails / QA as satisfied because a Guide exists
- Shipping Guide scripts that mention controls the prototype never built
