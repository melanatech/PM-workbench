---
description: Find whether a question could be answered from connected data, before anyone marks it blocked
---

# Source scout

Use when a question has no accepted source yet, or someone is about to mark a lane blocked. The point is to see whether we could answer it. Do not compute the answer.

Question: $ARGUMENTS

## Steps

1. State the question in one sentence.
2. Name the grain: person, session, event, case, or transaction. Use the words this workspace already uses for those grains.
3. Write keyword sets for the catalog sweep (table names, then column names).
4. Sweep the catalog the connected warehouse exposes. Record the query text.
5. For each plausible table, run a one-day existence count. Do not scan a month.
6. Look for a join key back to the accepted identity spine for this workspace.
7. Check freshness (the latest date on the date column, if one exists).
8. Record an owner or a doc link only if a file or a companion-agent reply names one. Otherwise write `[NEEDS INPUT]`.
9. Assign one status:
   - `accepted` (a data-pull or equivalent has already accepted it)
   - `candidate` (the table exists and a join looks possible; not accepted)
   - `found-no-join` (the table exists; no join key to the identity spine)
   - `not-found-after-probe` (the catalog sweep returned nothing)
   - `blocked-with-reason` (a named reason, after the probe, such as auth failure or no date column)
10. For anything still unknown, write a paste-ready prompt for the companion agent that might know (search, wiki, or meetings). Do not pretend the agent was called.

Write one row per candidate into the workspace source atlas (see `reference/templates/source-atlas-template.md`). Include the probe date and the query text. Never write "unavailable" without a probe row.

Do not invent table names, columns, or counts. If the warehouse session fails auth, stop and say the probe did not run.
