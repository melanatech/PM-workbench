# Prototype readiness checklist

Org-agnostic gate before sharing a prototype. Score each dimension Green / Yellow / Red. No company design-system names required.

## Dimensions

1. **Correctness** — primary flow matches the Feature Contract / stated intent
2. **States** — brief-stage: populated sample data only; name skipped states (empty, zero, error, loading, setup, permission) in one line, and do not score Red for leaving them out. PRD-stage (`/build prd-package`, or a flesh-out ask): no-data / error / loading / permission are intentional, not broken UI. If the stage is unclear, score as brief.
3. **A11y basics** — labels, contrast, keyboard reach for primary controls
4. **Performance sanity** — interactive without multi-second freezes on happy path
5. **Instrumentation hooks** — events/metrics named if the experiment needs them (or explicitly N/A)

## Scoring

Use **worst-score-wins**: one Red dimension makes the overall verdict Red. Yellows without Reds → Yellow. All Green → Green.

List any Red dimensions in the prototype-build RESULT. Non-blocking unless the PM asked for a hard gate.
