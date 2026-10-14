# Prototype component catalog (soft reuse)

Index of reusable UI pieces that already exist under `prototypes/`.  
`/build prototype-build` reads this in Step 0.

**Prefer `_shared` when present.** If `prototypes/_shared/package.json` exists, wire `@pm-live/prototype-kit` (`file:../_shared`) and import matching primitives from the package. Soft-copy rows below only when the piece is **not** promoted yet (Status ≠ `in _shared`).

When a prototype ships a piece worth stealing later, **append a row** in the same run. Prefer concrete file paths. After a row is copied ≥2 times, offer promotion into `_shared` (ask the PM).

## How to use

1. Before scaffolding: check `_shared` exports, then scan this table for feature-specific pieces.
2. For promoted rows: depend on `@pm-live/prototype-kit`. For others: copy/adapt and note `Adapted from prototypes/[source]/…` in the README.
3. Do **not** invent a fake company design system. If nothing matches, build clean/generic.
4. After a useful new piece lands: add a catalog row (date, path, what it is, when to reuse, status).

## Catalog

| Date | Name | Source path | Reuse when | Status | Notes |
|---|---|---|---|---|---|
| 2026-10-13 | Scenario Guide (evaluator panel) | `prototypes/_shared` → `ScenarioGuide` | Multi-concept / multi-persona demos | in `_shared` | Scripts stay in the feature app; see `_scenario-guide.md` |
| 2026-10-13 | Drawer / HelpPopover / InfoTip | `prototypes/_shared` | Dialogs, column help, KPI info | in `_shared` | Guardrails: Esc, focus return, click+keyboard |
| 2026-10-13 | Sortable table shell | `prototypes/_shared` → `SortableTable` | Simple sortable tables | in `_shared` | Concept-heavy tables may stay local |
| 2026-10-13 | Report explanations shell | `prototypes/explanations-transactions/src/` | Transactions-style report concept tests | soft copy | Concept + state bar; KPI strip; consumer of kit |

_Add rows when a build ships something worth stealing._

## Out of scope (this file)

- Package convention and handoff paths — [`shared-prototype-package.md`](shared-prototype-package.md).
- Company UI base pages under `repos/` — NEW-USER-SETUP §2a, not this catalog.
