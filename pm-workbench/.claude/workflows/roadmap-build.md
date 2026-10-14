---
description: Build a roadmap from scratch - problems, bets, then Now / Next / Later, every item sourced
model: sonnet
argument-hint: [area or initiative, or blank for the whole portfolio]
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so. Deep is one word away (`run this in deep mode`).

**Model.** `routes.json` registers this workflow as sonnet. Fast and Standard use that sonnet runner. When execution mode is Deep, dispatch `workflow-runner` on opus after the usage estimate and an explicit yes. Do not change the `routes.json` entry for that one run. An unattended run never upgrades to opus (rule 22: Fast or Standard only).

Context dependencies: soft: current-priorities, product-areas, kr-metric-map, audiences, people, systems-map | hard: none

This builds a roadmap. A change to a roadmap that already exists on a tracker, a sheet, or a deck is `/sync roadmap-update`, not this workflow.

Roadmap: $ARGUMENTS

Write `logs/run-manifest-[date]-roadmap-build.md` as you go.

## Discovery phase

Do this before any Now / Next / Later sequencing. Do not start from registers alone. Do not create a second gatherer. The agents below already exist.

1. **Preflight.** `python3 scripts/context_preflight.py --root <live> --topic "roadmap $ARGUMENTS"`. Reuse fresh hits. On `reuse`, do not redo that analysis. On `reuse_and_refresh`, spot-check the newer surface and report conflicts (rule 8). Pass hits into the steps below.
2. **Themes.** Dispatch `discovery-source-reader` over `registers/evidence.csv` and recent `inbox/` items that preflight did not already cover. Bounded: if more than 12 source files are relevant, name what was included and excluded and offer to widen. Do not skim the files you did select.
3. **Market.** If preflight's recommendation is `reuse` and a `state/competitive/` capture is among the hits, cite that capture and do not re-scan. Otherwise dispatch `competitive-capture-agent` (it writes `state/competitive/YYYY-MM-DD-<slug>.md`). If `reference/competitive-watchlist.md` is empty and no capture exists, do not invent competitors — add "who are the competitors, if any" to the cold-start batch below.
4. **External grounding.** For problems, market, users, and solutions, follow `.claude/workflows/_web-search.md`. Discover URLs with `python3 scripts/web_search.py` and save `state/web-search/YYYY-MM-DD-<slug>.md`. Reuse a fresh file there instead of searching again.
5. **Health.** `python3 scripts/context_health.py --root <live> --ids current-priorities,kr-metric-map,product-areas,audiences,people,systems-map`. A gap is a notice. Use it in Cold start. Do not treat a template-empty file as something the PM stated.

## Cold start

If `current-priorities` or `kr-metric-map` is missing, template-empty, or stale:

- Do not write Now / Next / Later in the same turn as the question.
- Derive a draft priority list from open rows in `registers/initiatives.csv`, displayed rows in `state/okr-history.csv` (never recomputed), key-result names in `kr-metric-map.md` when that file is filled, and the discovery themes from this run.
- Label every derived line **derived, not stated priorities**. A stated priority that context health marks ok stays unlabeled as derived. Each derived line cites at least one source (register id or file path). A line with no source is dropped or marked `[NEEDS INPUT]`.
- Return one batched QUESTIONS list: confirm or correct the derived list (and competitors, if that question is open). One batch, not one question per item. Wait for a yes before sequencing.
- **Unattended:** do not wait and do not treat the draft as confirmed. Write the derived list into `roadmap/[date]-roadmap.md` with the label, leave Now / Next / Later as `[NEEDS INPUT: confirm derived priorities]`, append `BLOCKED: confirm derived priorities` to `logs/run-log.csv`, and stop sequencing. The sonnet runner stays; do not upgrade to opus.

If both ids are ok, sequence without this confirmation.

## Sequence

After discovery, and after a yes when Cold start applied:

1. **Problems and opportunities**, each with a source.
2. **Bets**, each with the alternatives considered and why this one was chosen. An alternative with no source is `[NEEDS INPUT]`, not a guessed option.
3. **Now / Next / Later.** Each item has: rationale, the KR it moves (from `kr-metric-map` or `[NEEDS INPUT]`), confidence, dependencies, and source IDs (`EV-` / `DEC-` / `COM-` / `INIT-` / `RISK-` / `TODO-`, a tracker key, or a file path). An item with no source is not written.

**No invented dates.** A date appears on an item only when a tracker issue or a `registers/commitments.csv` row states it, and the item cites that source. Otherwise write `[NEEDS INPUT]` where a date would have gone. Do not infer a quarter, sprint, or ship date from confidence or from the Now / Next / Later bucket. The date in the filename is the run date, not an item date. Ticket-key shape comes from `systems-map` when that file is filled; do not invent a project prefix.

Save the internal draft to `roadmap/[date]-roadmap.md`. The file always has an **Anticipated objections** section.

Index it: `python3 scripts/analysis_index.py append --root <live> --topic-key "roadmap $ARGUMENTS" --path roadmap/[date]-roadmap.md --kind roadmap --as-of [date] --one-line "…" --source-workflow roadmap-build --primary-sources "<cited paths>"`.

## Red team

Standard and Deep: dispatch `strategy-red-team-reviewer` once, after the draft exists. Blind: the draft plus the sources it cites. Not the chat, not your reasoning, not registers you did not cite. One pass. Put findings in **Anticipated objections**. Do not silently rewrite the draft. Fast does not dispatch it; the section then says the pass was skipped because the mode is Fast. If Cold start stopped before a full draft, the section says the pass has not run and why.

## Deep only — optional persona lenses

Not in the default flow. Not in Fast or Standard. Only when the PM opts in and the mode is Deep, after the usage estimate and the yes.

These are role lenses, not impersonation. Build each lens from recurring concerns in `reference/context/people.md` that have a dated source. Drop a concern with no date. One blind pass per lens: the draft and its cited sources only. Keep the concerns, never transcripts. Findings join **Anticipated objections**. Do not add reviewer agents for this.

**Publish.** Defaults: `audience: internal`, `formats: [md]`. The roadmap draft stays the internal source. Produce an external version only when the PM asks, then follow Audience and formats and Publish in `.claude/workflows/_protocol.md`. When an external version is written, dispatch `external-readiness-reviewer` once on the rendered file and the audience line, unless this workflow's execution mode is Fast (Fast does not dispatch it). Publishing or sending is Tier 3 and waits for an explicit yes. Do not call a wiki create API or a chat send API from this step.
