# CONNECTIONS.md — how everything actually links together

Almost nothing in this kit runs in isolation. This is the map — what each command writes, what it reads, and what notices it when something else changes. Read this when a command feels like it's missing context it should have, or when adding something new (see EVOLVING.md for that recipe).

## The reference layer: `reference/links.csv`

A lightweight bookmark list, not a register — logged links to templates, policy docs, and dashboards that live in your wiki or shared drive and can be fetched live rather than downloaded and processed. Checked by `internal-docs-reader` before it goes looking for a local copy. See `reference/LINKS-README.md`.

## The hub: `registers/initiatives.csv`

One row per feature, tracking its stage and links to every artifact about it. Stage values: `discovery`, `building`, `prd`, `prototype`, `experiment`, `launched`, `killed`, `iterating` (continued work after a confirmed decision to iterate, including post-launch work). `/capture meeting-closeout` and `/capture process-inbox` **seed** rows when PM-scoped product work is named (enhancements fold into `notes`; eng-only infra never gets a row). `/build` workflows then attach prd/prototype/experiment/launch paths and refine stage. `/build experiment-analyze` maps confirmed outcomes: ship → `launched`, kill → `killed`, iterate → `iterating`. **The stage is descriptive, not a forced pipeline** — real work doesn't move linearly. A prototype can precede a PRD, an experiment can run without either, and a launched feature can loop back to `iterating`. Each command sets the stage that reflects what just happened; none of them should refuse to run because "the previous stage" hasn't happened. This is what turns "a bunch of files that happen to share a feature name" into something commands can actually query. Written by `/capture meeting-closeout`, `/capture process-inbox` (seed/update), `/build prd-package`, `/build prototype-build`, `/build experiment-package`, `/build experiment-analyze`, `/build launch-package`. Read (cross-checked) by `/discover discovery`, `/discover competitive-scan`, `/capture meeting-closeout`, `/sync jira-reconcile`, `/report okr-refresh`, `/report strategy-refresh`, `/report weekly-update`, and `/sync ripple-check`.

### Manual check: experiment decision register updates

Use a disposable initiative/decision-register copy or inspect the expected changes without editing live registers. For each outcome, check the result before and after explicit user confirmation:

| Experiment recommendation | Before confirmation | After confirmation |
|---|---|---|
| Ship | Results memo only; no decision row or initiative change | Add decision row; set initiative stage to `launched` and link `related_decisions` to that row |
| Kill | Results memo only; no decision row or initiative change | Add decision row; set initiative stage to `killed` and link `related_decisions` to that row |
| Iterate | Results memo only; no decision row or initiative change | Add decision row; set initiative stage to `iterating` and link `related_decisions` to that row |

Pass only if none of the three recommendations changes either register while unconfirmed, and each confirmed outcome writes the mapped stage and decision link.

## Full write/read map

The first column is the workflow name. Run it through its cluster command: `/capture` (meeting-closeout, process-inbox), `/brief` (daily-brief, return-brief, meeting-prep), `/sync` (jira-reconcile, ripple-check, context-reconcile, roadmap-update, rotate-registers), `/discover` (discovery, research-plan, research-package, competitive-scan, learn-product-flow, code-dive, explore-brief), `/build` (prd-package, prototype-build, prd-prototype-sync, experiment-package, experiment-analyze, launch-package), `/report` (weekly-update, okr-refresh, strategy-refresh, workbench-health, monthly-review). `/todo` is its own command. Writes and reads are unchanged by the routing.

| Command | Writes to | Reads / cross-checks against |
|---|---|---|
| `/brief return-brief` | `registers/decisions.csv`, `registers/risks.csv`, `registers/commitments.csv` (seeds them) | chat/Jira/wiki/shared-drive (via `return-window-scanner`) |
| `/capture meeting-closeout` | `registers/decisions.csv`, `registers/commitments.csv`, `registers/risks.csv`, `registers/initiatives.csv` (seed/update); `reference/context/assumptions-and-open-questions.md`; `learning/[area].md`; `outputs/todo-proposals/` (queue only) | Same registers (conflict check) + Jira |
| `/capture process-inbox` | `registers/evidence.csv`; meetings → meeting-closeout writes; initiatives notes/EV links; assumptions + learning + todo-proposals as above | `state/processed-files.txt`, existing evidence/initiatives (dedupe) |
| `/sync jira-reconcile` | `state/jira-snapshots/`, proposed Jira writes | `registers/decisions.csv`, `commitments.csv`, `evidence.csv`, `initiatives.csv`, recent meeting outputs |
| `/discover discovery` | `registers/evidence.csv` | chat/support/behavior-analytics (`discovery-source-reader`) + internal docs (`internal-docs-reader`) + `registers/initiatives.csv` (relevance flag) |
| `/report okr-refresh` | `state/okr-history.csv` | Dashboard and/or dated internal metric surfaces + `registers/initiatives.csv` (which initiative this metric belongs to) |
| `/discover research-plan` | `outputs/research/[topic]/plan.md` (criteria, outreach drafts, guide, decision rules — never names), (later) `registers/research-participants.csv` | dashboards/behavior analytics/Jira + internal docs (personas/prior research) |
| `/discover explore-brief` | `drafts/[slug]-product-brief.md`, `state/web-search/YYYY-MM-DD-<slug>.md` (when web grounding ran), light INIT notes | Preflight + same gatherer as prd-package (`prd-context-gatherer` + optional `internal-docs-reader`); `_web-search.md` axes (problems / market / users / solutions); stops before full PRD |
| `/build prd-package` | `outputs/prds/[feature]/`, `state/web-search/` (refresh or reuse), `registers/initiatives.csv` (creates/updates) | Same gatherer + `_web-search.md` Step 0.5 + readiness gate; `evidence.csv`, `learning/`, `okr-history.csv`, competitive log, `decisions.csv`/`risks.csv` + `prototypes/[feature]/` if it exists |
| `/build prototype-build` | `prototypes/[feature]/` (incl. local git checkpoints via `scripts/prototype_checkpoint.py`), `logs/prototype-checkpoints/[feature].md`, `registers/initiatives.csv` (updates) | `learning/`, repo patterns (`code-repo-explorer`) + `outputs/prds/[feature]/` if it exists |
| `/build prd-prototype-sync` | (report only, no writes) | Both `outputs/prds/[feature]/` and `prototypes/[feature]/` directly |
| `/discover research-package` | `outputs/research/[name]/` | Prior research (`internal-docs-reader`) + prototype it's testing |
| `/build experiment-package` | `outputs/experiments/[name]/`, `registers/initiatives.csv` (updates) | `evidence.csv`, `okr-history.csv` (baseline), five review subagents |
| `/build experiment-analyze` | `registers/decisions.csv`, `registers/initiatives.csv` (confirmed ship → `launched`, kill → `killed`, iterate → `iterating`) | The pre-registered design + results + `results-integrity-reviewer` |
| `/build launch-package` | `outputs/launches/[feature]/`, `registers/initiatives.csv` (stage → launched) | PRD, Jira, prototype, docs (`launch-drift-detector`) + `initiatives.csv` (related_okr for monitoring plan) |
| `/report monthly-review` | `outputs/monthly/[date]-workbench-review.md`, `state/health-history.csv` (one row per snapshot), `logs/review-notes.csv` (you edit) | `scripts/workbench_metrics.py` over the registers, `logs/run-log.csv`, `logs/todo-proposals.csv`, `state/output-hashes.csv`, `workbench_health.py` |
| `/discover competitive-scan` | `state/competitive/YYYY-MM-DD-<slug>.md` (agent-written, mandatory), `outputs/monthly/competitive-log.md` (same run, no ask), watchlist URL backfill | External sites via `competitive-capture-agent` (`scripts/web_search.py` then WebFetch per `_web-search.md`; seed URLs optional) + internal battlecards (`internal-docs-reader`) + `registers/initiatives.csv` (relevance flag) |
| `/report strategy-refresh` | `outputs/strategy/[date]/` | Everything: `evidence.csv`, `okr-history.csv`, competitive log, `learning/` (via `strategy-synthesizer` + `internal-docs-reader`) + `registers/initiatives.csv` (portfolio view) |
| `/report weekly-update` | `outputs/weekly/[date]-leadership-update.md` | `initiatives.csv`, jira-reconcile output, `commitments.csv`, `decisions.csv`, `risks.csv`, discovery output, OKR narrative |
| `/brief meeting-prep` | (report only) | `registers/initiatives.csv`, `decisions.csv`, `risks.csv`, `commitments.csv`, recent meeting outputs, `reference/links.csv` — the before-meeting mirror of `/capture meeting-closeout`'s after |
| scheduled runs (`scripts/run_scheduled.py`) | `logs/scheduled-runs.csv`, `logs/run-log.csv` (BLOCKED rows on failure), `state/inbox-seen.json`, `state/.scheduled.lock`; `/todo sweep` writes `outputs/todo-drafts/`; `/todo propose queue` writes `outputs/todo-proposals/` (nothing added to `registers/todos.csv`) | the workflows named in SCHEDULING.md; `state/PAUSE` (you create it) stops them |
| `/todo` | `registers/todos.csv` (via `scripts/todo_register.py`), `outputs/todo-drafts/` (`work` mode, drafts only) | `registers/todos.csv`; for `propose`/`work`, up to 12 inbox/output/register files via `todo-worker`. Read by `/brief daily-brief` (counts), `/brief meeting-prep` (open to-dos for the topic) and `/build prd-package` (readiness gate: open to-dos whose `blocks` names the PRD) |
| `/sync ripple-check` | Tier 1 fan-out via `_fan-out.md` (assumptions, learning, priorities, competitive, INIT notes, etc.); report + suggested next workflows | Everything — the on-demand version of what the commands above do automatically |
| `/sync context-reconcile` | Backfill `_fan-out.md` gaps from archive/outputs; `assumptions-and-open-questions.md`; INIT notes; learning/research/competitive as needed; `outputs/todo-proposals/[date]-context-reconcile.md`; `outputs/daily/[date]-context-reconcile.md`; todo hygiene as PROPOSALS only | `archive/` + digests (bounded), registers, living context, competitive log, existing todo-proposals |

## The two ways connection actually happens

**Automatic, baked into a command's own steps** — most of the table above. When you run `/capture meeting-closeout`, it doesn't just file the decision; it checks whether that decision touches something already in motion and tells you.

**On-demand, when something happened outside the normal flow** — `/sync ripple-check`. Use it after a hallway conversation, a decision made over Slack DM that never became a formal meeting, or news that arrived some other way. It's the same cross-checking logic, invoked manually instead of triggered by a specific command's normal work. Mid-chat facts the PM drops after a freeform answer should still write-back in that turn (CLAUDE.md rule 24); ripple-check is for a full cross-surface pass, not a prerequisite for logging one clear fact.

## Where this can still fall short (be honest with yourself about it)

The cross-checks above are only as good as the initiative actually being *in* `initiatives.csv` with the right name. If you build a prototype before ever running `/build prd-package`, or a feature never gets a formal PRD at all, nothing will connect it automatically — that's why `/build prototype-build` creates a row even without a PRD, and why it's worth naming things consistently. When in doubt about whether something is tracked, just ask in a session — "is [feature] in the initiatives register?" — rather than assuming the connection exists.

**Registers alone are not enough.** Capture used to stop after DEC-/EV-/INIT- rows. `.claude/workflows/_fan-out.md` routes each extracted item type to the surfaces that can hold it (`scripts/fanout_route.py`). The end block lists surfaces written and the cross-initiative line. A chat answer is not proof those surfaces hold the same detail — Rule 23 in `_fan-out.md`.

## Register schemas

This file owns the schemas. CLAUDE.md rule 7 states the append-vs-update rule; it does not repeat the columns.

- `registers/decisions.csv` — id, date, decision, made_by, source_link, affects. Immutable history: append; correct by a linked superseding row.
- `registers/commitments.csv` — id, description, owner, due_date, audience, source, status, last_updated. Current state: update in place. PM-scoped only (promises the PM owns, chases, or depends on for product work) — not eng/ops chores overheard in a meeting; see `/capture meeting-closeout` PM-scope filter.
- `registers/risks.csv` — id, date_raised, risk, severity, mitigation, status, source. Current state: update in place.
- `registers/evidence.csv` — the discovery evidence graph (see `/discover discovery` for the full schema). Immutable history.
- `registers/research-participants.csv` — who we contacted, when, outcome (prevents over-contacting). Immutable history.
- `registers/todos.csv` — id, description, owner, due_date, priority, status, initiative, blocks, links, origin, source, created, last_updated, note. Current state, written only through `/todo` (`scripts/todo_register.py`). Not a commitment and not a decision. Cite as `TODO-nnn`. Drop marks a row `dropped`; do not delete it.
- `registers/initiatives.csv` — the hub: one row per feature, stage, and links to every artifact. Current state. Seeded by `/capture` when product work is named; refined by `/build`.
- **Cite only IDs that exist** for every DEC-/COM-/RISK-/EV-/INIT-/TODO- prefix. Write the row in the same run before citing it, or write `proposed: COM row needed` with no ID. The provenance hook rejects phantom citations.

Meetings feed the registers. The registers feed the weekly update, tracker reconciliation, PRDs, and strategy.

## Key file map

- `scripts/todo_register.py` — the only way `/todo` writes `registers/todos.csv` (IDs, dates, and CSV quoting in code; refuses a changed header, lost rows, symlinks).
- `inbox/` — new raw captures by type. `state/` — snapshots and cursors. `state/web-search/` — external grounding (see `_web-search.md`). `state/competitive/` — competitor page dumps.
- `scripts/web_search.py` — URL discovery that does not depend on a hosted web-search tool (always before native WebSearch).
- `outputs/` — reviewed work products by cadence and type. `archive/` — processed raw inputs.
- `reference/` — templates (including `templates/formatted/`, where the template owns branding and `scripts/render_template.py` supplies content), metric definitions (one YAML per OKR metric), product knowledge, `user-research/` (indexed research summaries).
- `learning/` — per-area product knowledge from deep-dives and code-dives.
- `repos/` — read-only code clones and optional UI-base symlinks (NEW-USER-SETUP §2a). `prototypes/` — greenfield prototypes from `/build prototype-build`. Soft reuse catalog: `reference/design/prototype-components.md`. When present, live `prototypes/_shared/` (`@pm-live/prototype-kit`) is the shared primitive package (`reference/design/shared-prototype-package.md`).
