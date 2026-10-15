# Fan-out — typed routing after a capture

Read by `/capture meeting-closeout`, `/capture process-inbox`, `/discover discovery`,
`/discover competitive-scan`, `/sync ripple-check`, and `/sync context-reconcile`.
`context-reconcile` is the backfill. Forward captures still fan out in the same run.

**Source triage first.** Before tagging claims, classify each source with
`.claude/workflows/_source-triage.md` and append a `state/source-index.csv` row
(`scripts/source_index.py`). Triage decides promote / index / hold / ignore /
duplicate. Only **promote** outcomes go through the claim table below.

Registers are an index. Tag each extracted item with a type, then read and write
only the surfaces that type maps to. The map is `scripts/fanout_route.py`
(this table must match it):

```sh
python3 scripts/fanout_route.py --types decision,evidence
```

| Type | Surfaces | Write when |
|---|---|---|
| decision | 1, 3, 5 | A decision. 3 when an initiative is named (every INIT touched). 5 only if this week's priorities moved |
| commitment | 1 | A PM-scoped promise |
| risk | 1, 5 | A risk. 5 only if it is top-of-mind this week |
| evidence | 2, 3, 7 | A discovery signal about users/product. 7 when the source is research. Not for internal directions (use exploratory-thinking hold) |
| metric | 12 | A pre-calculated number with an as-of date. Never recompute |
| competitor | 3, 8 | Competitor behavior, including from a meeting or a research doc |
| term | 11 | A standing acronym or internal name (W+M, MAPU, AAB). Ordinary phrases stay in learning |
| durable-product-fact | 3, 6 | How the product works. Area file plus `learning/entities/` when a named entity is claimed |
| assumption | 4 | An assumption, open question, or unresolved conflict |
| follow-up | 9, 10 | Mine. 9 is a proposal, never a silent todo add. 10 only when this workflow is already drafting a ticket |
| analysis | 13 | A durable analysis under `outputs/` or `learning/` |
| external-grounding | 14 | `state/web-search/` per `_web-search.md` (not competitor dumps) |
| strategy-frame | 3, 4, 5, 6, 12, 15 | Company OKRs, planning Q&A, board/DOP decks. Dated frame in `learning/` (objectives, KRs, implications, inferences labeled); map `related_okr` on INIT rows they plausibly drive (mark hypothesis when the doc names no initiative); log dated metrics; name `/report strategy-refresh` as next consumer. **Surface 5 is proposal only (Tier 3)** — never write `current-priorities.md` directly. Do not skip as "business-level." |
| semantic-definition | 3, 4, 6, 13, 15 | Product/report term, metric, or enumerated value with an agreed meaning (not a glossary acronym). Update learning entities / definition artifacts; note conflicts in assumptions; index the analysis. Acronyms stay `term` → 11 |
| stakeholder-stance | 15 | Preference or position from a named stakeholder. Write the dated, sourced stance to `reference/context/people.md` via `_source-triage.md`; index the source |

Surfaces: 1 registers (decisions, commitments, risks) · 2 `registers/evidence.csv` · 3 `registers/initiatives.csv` · 4 `reference/context/assumptions-and-open-questions.md` · 5 `reference/context/current-priorities.md` · 6 `learning/` · 7 `reference/user-research/` · 8 `state/competitive/` and `outputs/monthly/competitive-log.md` · 9 `outputs/todo-proposals/` · 10 `drafts/` · 11 `reference/context/glossary.md` · 12 `state/okr-history.csv` · 13 `state/analysis-index.csv` · 14 `state/web-search/` · 15 `state/source-index.csv`.

**Surface budget.** Do not add a fan-out surface unless a type has nowhere to go. Output staleness extends surface 13 (it is not a new surface). Entity links are written by `jira-reconcile`, not by this checklist. Surface 15 is the triage index; every classified source lands there via `_source-triage.md`.

## Mechanical writes

No model reasoning for these. Call the script.

- **Metric** → one `state/okr-history.csv` row per series (displayed value, as-of, timeframe, filters, displayed delta). `scripts/log_metrics.py` is still a stub: append with Python's `csv` module and say the automated check did not run.
- **Analysis** → `python3 scripts/analysis_index.py append --root <live> --topic-key "…" --path <rel> --kind <kind> --as-of YYYY-MM-DD --one-line "…" --primary-sources "…" --initiative-ids "…" --source-workflow <name>`. Idempotent by path. After the deliverable itself is updated, `append --refresh` clears `stale_since`.
- **Staleness** → when a new fact shares an `initiative_ids` token or a `primary_sources` token with an indexed row: `python3 scripts/analysis_index.py mark-stale --root <live> --initiative-ids "…" --primary-sources "…" --since YYYY-MM-DD --reason "…" --except-path <the new output>`. Sets `stale_since` and `stale_reason`. Does not rewrite the PRD, brief, strategy, or roadmap. The earliest `stale_since` is kept.
- **Source triage** → `python3 scripts/source_index.py append --root <live> --path <rel> --source-role … --temporal-status … --origin … --outcome … --reason "…" --entities "…" --summary "…"`. Then `match` / `promote` / `find-duplicate` as `_source-triage.md` requires.

## End block

List only surfaces written. No N/A list.

```
Surfaces updated: [paths / INIT-/EV-/DEC- ids]
Cross-initiative: [INIT-a, INIT-b — one line each on what was appended]
```

If a finding should change strategy or the weekly narrative and those docs are not rewritten on this capture: append one dated bullet under assumptions or the INIT notes, and name `/report strategy-refresh` or `/report weekly-update` as the next consumer.

**Cite only IDs that exist.** Write the row, then cite it. Otherwise write `proposed: COM row needed — <description>` with no ID.

## Rule 23 — chat answer is not the durable file

Digests, register rows, and learning notes are lossy on purpose (rule 15). An ad-hoc reply often re-reads a richer source and adds justification the digest never held. **Forbidden:** "it's all captured in `outputs/…`" / "same as the summary" after a richer chat answer, unless you claim-checked (every material claim in the reply appears in that file) or you wrote that content into the file this turn. When the reply surfaces material facts missing from digests, registers, or learning, say the gap and either append (Tier 1, dated source) or list what would be written. Topic overlap is not claim coverage.

## Rule 24 — user-injected context after freeform chat

When the PM adds new facts mid-thread outside `/capture` / `/quick-close`, treat that as durable input. Do not only acknowledge it in chat. **Clear material claims** (decision, commitment, risk, open conflict, durable product fact, assumption): write the matching surface this turn (Tier 1) or present a one-line PROPOSAL of the exact row or append if Tier 2/3 (scope, owner, dates, send). **Ambiguous:** ask one short question naming the candidate surface. **Conversational only:** stay silent on write-back. Source the write as `chat:[date]` or the thread topic plus any archive path named. Route the claim through the type table above. `/sync ripple-check` is the full cross-check; it is not required for one obvious fact. `/sync context-reconcile` reuses `scripts/chat_harvest.py` for facts that were said in chat and never written back. When the PM parks a question ("not yet", "just notes"), mark it `parked YYYY-MM-DD` in assumptions and do not re-ask unless a new source touches it.

## Anti-patterns

- Writing only DEC-/COM-/RISK-/EV- rows and calling the capture done
- Citing IDs that were never written
- Listing every surface as N/A
- Walking all 15 surfaces for an item whose type names two
- Rewriting a stale PRD, brief, strategy, or roadmap from the staleness flag (offer a refresh; do not auto-revise)
- Skimming a long source "because of context constraints" instead of dispatching the heavy-read agent and then applying this table
- Skipping a company OKR or strategy doc as "business-level"
- Logging internal directions as evidence rows
- Writing `current-priorities.md` from a strategy-frame without Tier 3 confirmation
