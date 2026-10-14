status: template
last_updated:

# KR to metric map

Which already-calculated metric each key result uses. `/report okr-refresh`
matches a displayed number to a key result with this file. It does not
compute the number. This is the OKR context file. Do not add a second one.

Company check-in cadences (when numbers are entered, which columns, who
reads the note) stay in `.claude/CLAUDE.local.md`, not here.

Remove `status: template` and set `last_updated` when the rows are real.
Copy to `reference/metric-definitions/kr-metric-map.md`. One metric YAML per
series still lives beside this file (see `example.yml`).

| KR | Objective | Metric definition | Target | Owner | Source |
|---|---|---|---|---|---|
| [KR] | [objective] | [reference/metric-definitions/metric.yml] | [target] | [owner] | [NEEDS INPUT] |

## Rules

- Cite a key result with its own metric. A parent metric is labeled as the parent, not used in its place.
- If two sources name similar numbers, they are different metrics until this map says they are the same.
