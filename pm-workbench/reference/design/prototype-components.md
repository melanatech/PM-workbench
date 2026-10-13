# Prototype component catalog (soft reuse)

Index of reusable UI pieces that already exist under `prototypes/`.  
`/build prototype-build` reads this in Step 0, **copies or adapts** matching pieces into the new feature (does not npm-link a shared package).

When a prototype ships a piece worth stealing later, **append a row** in the same run (prototype-build Step 2 close or after QA). Prefer concrete file paths over vague names.

## How to use

1. Before scaffolding: scan the table for layout shells, cards, tables, filters, empty/error states that match the new flow.
2. Copy the source files into the new prototype (or adapt tokens/markup). Note in the new README: `Adapted from prototypes/[source]/…`.
3. Do **not** invent a fake company design system. If nothing matches, build clean/generic.
4. After a useful new piece lands: add a catalog row (date, path, what it is, when to reuse).

## Catalog

| Date | Name | Source path | Reuse when | Notes |
|---|---|---|---|---|
| 2026-10-13 | Scenario Guide (evaluator panel) | `prototypes/explanations-transactions/src/components/ScenarioGuide.jsx` | Multi-concept / multi-persona demos; optional with prototype-build | Key scripts by variant; look/do/try; desktop sidebar + mobile sheet; see `_scenario-guide.md` |
| 2026-10-13 | Report explanations shell | `prototypes/explanations-transactions/src/` | Transactions-style report concept tests | Concept + state bar; drawers; KPI strip; see README |

_Add rows when a build ships something worth stealing._

## Out of scope (this file)

- A shared `prototypes/_shared/` package — see [`DEFERRED-shared-prototype-package.md`](DEFERRED-shared-prototype-package.md).
- Company UI base pages under `repos/` — that is NEW-USER-SETUP §2a, not this catalog.
