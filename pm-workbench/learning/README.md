# learning/

Per-area product knowledge from meeting walkthroughs, `/discover learn-product-flow`, `/discover code-dive`, and process-inbox compiles. Maintained summaries — update in place with new dated lines; do not treat as an event log.

## Two layers

| Layer | Path | Role |
|---|---|---|
| **Area digests** | `learning/[area].md` | Short dated navigation + highest-signal claims for a product area (e.g. `commerce-intelligence.md`). Not a full dump of archive sources. |
| **Entity pages** | `learning/entities/<slug>.md` | Optional compounding pages for a named initiative, metric, JTBD, or decision. Created from `reference/templates/learning-entity-stubs/`. When process-inbox (or discovery) extracts claims that attach to a named entity, **back-propagate** a dated `## From …` block here — same idea as an LLM wiki ingest, without a parallel wiki tree. |

**Registers remain source of truth** for decisions, commitments, risks, and evidence events (`registers/*.csv`). Learning pages are compiled summaries with source paths; never invent an entity or “resolver” for a gap you cannot name — put unnamed gaps in `reference/context/assumptions-and-open-questions.md`.

Redact customer names/identifiers before writing (CLAUDE.md rule 15). Raw captures stay in `inbox/` → `archive/`.
