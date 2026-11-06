Usage rows: 13 calls, 5 sessions, 2026-07-06 to 2026-07-14 (5 days with activity).
- Week of 2026-07-06: 2026-07-06 to 2026-07-09, 3 active days
- Week of 2026-07-13: 2026-07-13 to 2026-07-14, 2 active days

### Work mix by week (share of calls / share of tokens)

| Kind of work | Week of 2026-07-06 | Week of 2026-07-13 |
|---|---|---|
| Capture | 0% / 0% | 20% / 18% |
| Correction or redo | 38% / 34% | 20% / 18% |
| Lookup | 12% / 11% | 20% / 18% |
| Named workbench workflow | 38% / 44% | 40% / 46% |
| Subagent result returned | 12% / 11% | 0% / 0% |

### Named workflows by week (calls)

- Week of 2026-07-06: process-inbox 1, meeting-closeout 1, weekly-update 1
- Week of 2026-07-13: meeting-closeout 1, process-inbox 1

### Corrections

Labeled correction calls: 5. From subagent results (excluded): 1. Real correction calls: 4 (31% of all calls) from 4 distinct turns.
- Week of 2026-07-06: 3 of 8 calls (38%)
- Week of 2026-07-13: 1 of 5 calls (20%)
- By day: 2026-07-06 1, 2026-07-07 1, 2026-07-09 1, 2026-07-14 1

### Corrections per PM message, with coverage

Unit: one PM message (`user_uuid`), not one call. Subagent results are left out of both sides, and so is a row with no `user_uuid`. Labeled = any tag other than `other`.
- Week of 2026-07-06: corrections 3 of 7 PM messages (43%); coverage 7 of 7 (100%); among labeled 3 of 7 (43%)
- Week of 2026-07-13: corrections 1 of 5 PM messages (20%); coverage 5 of 5 (100%); among labeled 1 of 5 (20%)

### Returns past the stale-session line (Plan E)

Line: 60+ minutes since the previous reply and 80,000+ tokens of context before it. A chat that crosses twice counts twice. Cold = the return wrote 80% or more of its context from scratch. The median is tokens written from scratch on the first reply in the chat that continued: the same chat, or a new chat only when a pick-up was accepted. This file has no pick-up record, so the reply scored is the one in the same chat. A return that starts with !force stays in the median and is also counted on its own line. Token counts, not cost.
- Week of 2026-07-06: 0 returns in 0 chats; cold 0; started with !force 0; median from-scratch tokens: —
- Week of 2026-07-13: 0 returns in 0 chats; cold 0; started with !force 0; median from-scratch tokens: —
- All rows in this file: 0 eligible returns; started with !force 0; median from-scratch tokens: —

### Correction turns to theme (internal only — do not quote in external output)

- 2026-07-06: you missed the support export as a source
- 2026-07-07: the risk is secondhand, not a fact
- 2026-07-09: wrong template, use last week's layout
- 2026-07-14: you missed the capture file

### Surface

panel 11, terminal 2

### Outcomes per week (on or after 2026-07-06)

- Decisions: 2 of 2 on file (week of 2026-07-06: 1, week of 2026-07-13: 1)
  - `made_by` is free text: read it to say who decided, do not count it by exact match
- Commitments (by last update): [registers/commitments.csv](registers/commitments.csv) missing or empty
- Evidence: [registers/evidence.csv](registers/evidence.csv) missing or empty
- Initiatives (by last update): [registers/initiatives.csv](registers/initiatives.csv) missing or empty
- To-dos created: 3 of 3 on file (week of 2026-07-06: 2, week of 2026-07-13: 1)
  - Done: 1 of 3

Cost is not computed here. Use the internal cost dashboard (spend, tokens, and its date range).
