# Source atlas

One row per table or domain you probed. The point is whether a later pull could answer the question. Status values: `accepted`, `candidate`, `found-no-join`, `not-found-after-probe`, `blocked-with-reason`.

| Domain or question | Table | Grain | Join key to identity spine | Freshness | Status | Probe date | Query used | Notes |
|---|---|---|---|---|---|---|---|---|
| example: session length | schema.table | session | person id | max date, or unknown | candidate | YYYY-MM-DD | the catalog query | owner or doc, or [NEEDS INPUT] |
