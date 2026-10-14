# Workspace aliases (name → path)

When the PM (or a capture) names a surface — "term registers", "events digest", "PPP" — **look it up here first**, then search (`context_preflight` / Glob), then ask. Do **not** guess the nearest-sounding file (e.g. `glossary.md` for "term registers").

Copy this file into your live workspace as `reference/context/workspace-aliases.md` and keep it updated.

| Phrase | Path | Meaning |
|---|---|---|
| term registers | `outputs/definitions-review/term-registers/` | Per-area Cube term workbooks (Orders, Payments, …). **Not** `glossary.md`. |
| definitions review | `outputs/definitions-review/` | Style guide, datasheet-vs-cube, term registers hub |
| events digest / instrumentation digests | `outputs/daily/*events*` (e.g. `2026-10-07-events-we-should-track.md`) | Prior analysis of analytics events — authority before re-reading `repos/` |
| PPP | `reference/templates/ppp-template.md` (or house PPP under templates) | Product Performance Plan shape |
| glossary | `reference/context/glossary.md` | Standing acronyms / company terms for chat — **not** Cube field definitions |

_Add a row when a name you use often maps to a specific path._
