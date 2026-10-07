# Fan-out checklist — after any capture / discovery / competitive ingest

Read by `/capture meeting-closeout`, `/capture process-inbox`, `/discover discovery`,
`/discover competitive-scan`, `/sync ripple-check`, and `/sync context-reconcile`.
This is the fix for "registers updated but the insight died in chat."

`context-reconcile` is the **backfill** path: it re-reads already-processed
archive/outputs and applies this checklist to close gaps. Forward captures
must still fan out in the same run so backfill stays rare.

Registers are an **index**, not the whole memory. After you extract facts, walk
every durable surface below. **Update what applies in the same run** (Tier 1).

**Ad-hoc enrichment:** if a later chat answer (meeting recall, "what happened on…", brief follow-up) pulls material claims from a transcript that the daily digest or registers do not hold, that is a fan-out gap — append the missing claims (or say what is chat-only). Do not point at the old digest and claim equivalence (CLAUDE.md rule 23).

**User-injected context (rule 24):** if the PM adds new material facts in chat (not via `/capture` / `/quick-close`), apply the same surfaces below this turn — write Tier 1, or one concrete PROPOSAL/ask when ambiguous or Tier 3. Do not wait for them to remember `/sync ripple-check`.
Do not ask "should I also update learning/?" when the content clearly belongs
there. Ask only for Tier 3 (scope/owner/dates/send) or genuine ambiguity.

## Surfaces (check each; write or mark N/A)

| # | Surface | Write when |
|---|---|---|
| 1 | `registers/decisions.csv` / `commitments.csv` / `risks.csv` | Meeting/decision/risk (PM-scoped) |
| 2 | `registers/evidence.csv` | Discovery signal, customer quote, inferred enhancement |
| 3 | `registers/initiatives.csv` | Named product work — seed/update **and** append cross-cutting notes to **every** INIT- the finding touches (not only the primary one) |
| 4 | `reference/context/assumptions-and-open-questions.md` | Assumptions, open questions, unresolved conflicts |
| 5 | `reference/context/current-priorities.md` | Changes this week's top 3, leadership pressure, watched risks, or dated milestones — dated one-liners, do not invent a new priority without evidence |
| 6 | `learning/[area].md` **and** `learning/entities/<slug>.md` when claims attach to named entities | Durable product/how-it-works facts: area file gets a short digest; back-propagate claims into entity stubs (see process-inbox learning compile). Registers stay SoT for DEC/COM/RISK/EV — do not invent entity resolvers for unnamed gaps |
| 7 | `reference/user-research/[dated]-*.md` | Research reports / synthesis docs (per that folder's README) |
| 8 | `state/competitive/` + `outputs/monthly/competitive-log.md` | Competitor behavior, pricing, parity, market gaps (even if the source was a meeting or research doc, not a formal scan) |
| 9 | `outputs/todo-proposals/` | My follow-ups (never silent `/todo` add) |
| 10 | `drafts/` (Jira etc.) | When the workflow already drafts tickets |
| 11 | `reference/context/glossary.md` | New standing acronym/term worth keeping |
| 12 | `state/okr-history.csv` | Pre-calculated metric with as-of date from dashboard **or** internal deck/doc/export (SOURCE-POLICY dated-internal-numbers exception) |

Skip empty negatives in chat, but **do** end the run with one compact block:

```
Surfaces updated: [paths / INIT-/EV-/DEC- ids]
Surfaces checked N/A: [short list, e.g. competitive, glossary]
Cross-initiative: [INIT-a, INIT-b — one line each on what was appended]
```

If a finding should change strategy or the weekly narrative but those docs are
not rewritten every capture: append one dated bullet under
`reference/context/assumptions-and-open-questions.md` or the relevant INIT-
`notes`, and name `/report strategy-refresh` or `/report weekly-update` as the
next consumer — do not leave the insight only in the daily output markdown.

## Anti-patterns (forbidden)

- Writing only DEC-/COM-/RISK-/EV- rows and calling the capture "done"
- Narrowing a multi-theme source to one customer question when other themes
  were in the material (see competitive-scan scope discipline)
- "Should I also update learning / competitive-log / priorities?" when the
  checklist row clearly applies — just update
- Putting cross-cutting insight only in `outputs/daily/` (those are digests;
  living files and registers must hold what next week's commands need)
- Skimming a long strategy/research source "because of context constraints"
  instead of dispatching `internal-docs-reader` (or the workflow's heavy-read
  agent) and then applying this checklist from the brief