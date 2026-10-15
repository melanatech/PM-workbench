# Source triage — classify the source before claim fan-out

Read by `/capture process-inbox`, `/capture meeting-closeout`, and
`/sync context-reconcile`. Run after extraction (and vision when needed),
**before** tagging claims and applying `_fan-out.md`.

Goal: loss-aware compression. Promote what matters, index or hold the rest,
ignore only with a stated reason. Never dismiss a source as "business-level."

## 1. Triage block (one per source)

Write this block into thinking, then append a `state/source-index.csv` row via
`python3 scripts/source_index.py append …`.

```text
source_role: evidence | operating-update | product-knowledge | semantic-system | strategy | exploratory-thinking | operating-model | business-process | design-artifact | stakeholder-stance | roadmap-plan | engineering | template | how-to | data | kit-feedback | other
temporal_status: current | historical-baseline | superseded | conflicting | unknown
origin: primary | second-hand | ai-summary | derived-own
outcome: promote | index | hold | ignore | duplicate
reason: one line
entities: INIT-/metric/term/field ids or names
same_as: path of the copy kept (duplicate/version/bundle/meeting only)
sensitivity: none | customer | commercial | personal
unread: what was not read (pages, comments, sheets), or blank
```

Outcomes:

- **Promote** — send claims through `_fan-out.md` / `scripts/fanout_route.py`.
- **Index** — short summary + entity tags in the source index. Registers unchanged.
- **Hold** — weak or partial signal. Keep until a second source supports or contradicts it.
- **Ignore** — drop from PM context, with a stated reason. Raw file stays in `archive/`.
- **Duplicate** — same content already kept elsewhere; set `same_as` to the kept path. Facts logged once.

## 2. Rules by source kind

### Old company / product / decision context

Label `historical-baseline` or `superseded`. Feeds rationale ("why we decided X"),
what changed since, and abandoned approaches. Never overwrites current state.
Decisions stay append-only. Conflict with current state → assumptions (rule 8).

### Engineering

Keep a detail only when it changes one of: merchant-visible behavior;
API / event / schema / metric meaning; launch readiness or critical path;
reliability / performance / data quality; instrumentation; architecture that
limits future scope; cost or capacity. Otherwise **ignore**, with that reason.
Replaces the blunt "eng-only" filter.

### Templates

Keep the existing flow: index row in `found-templates-index.md` + Tier 2
PROPOSAL to create `reference/templates/<slug>.md`. Never invent a template.

### How-tos

- Recurring PM procedure → proposal for a workflow or skill update.
- Product-support instructions → `learning/`.
- One-time ops procedure → index only.
- Conflicting how-tos → report the conflict; do not pick a winner.

### Data

Write a compact **data profile** (source + access path, grain, date range and
filters, key field **names**, displayed metrics, quality limits, the question
it could answer). Displayed metrics → `state/okr-history.csv`. Definitions →
`semantic-definition`. Raw rows are never copied. A dataset with no question
attached is indexed, not analyzed. Redact before writing (see Sensitivity).

### Strategy (company OKRs, planning decks)

Route as claim type `strategy-frame`. **Forbidden** to skip as "business-level."

### Exploratory thinking

Meeting notes framed as ideas, "things to think about", directions with no
owner or decision:

- Outcome `hold`. Short dated "Ideas and directions" entry on the matching
  `learning/` strategy page + source-index row tagged to entities.
- **No EV rows.** Evidence is for discovery signals about users and the product,
  not internal directions.
- **No DEC / COM rows**, and **no questions about owners or decisions**.
  A missing owner is expected, not a gap to chase.
- Ideas return when a later source matches them (cross-source pass) or when
  `/report strategy-refresh` runs.

### Operating model / process

Example: eval-first process (define JTBD and evals → build to threshold →
add to Airo features matrix → monitor traces → ops alerts).

- Role `operating-model`. Index with status `proposal` | `adopted` | `unknown`.
- Propose where it could land if adopted (e.g. an eval section in the PRD
  template) as a Tier 2 proposal, only when the PM asks or status becomes
  `adopted`.
- Do **not** log as evidence.

### Design and vision artifacts

Storyboards, phase playgrounds, capability maps, prototypes, mockups:

- Role `design-artifact`. Index and link to the matching initiative and
  strategy page as statements of **product intent**. Not facts or evidence.
- Vision-read when they arrive as images or PDFs.

### Other teams' business processes

Examples: commission prep guides, partner payout process docs.

- Role `business-process`.
- Write a short current-state baseline in the matching `learning/` entity
  (e.g. INIT-035 for commissions): steps, inputs, systems, manual pain points.
- Pain points become EV rows only when stated as observed problems.

### Stakeholder stances

"Pranay prefers the insights path", "Dhruv has no requirement":

- Role / claim type `stakeholder-stance`.
- Append dated, sourced lines to `reference/context/people.md`, labeled as
  stances, not decisions. Never invent a stance from silence.
- `/brief meeting-prep` reads these.

### Kit feedback

PM corrections about how the kit behaved ("why don't you treat OKRs as strategy"):

- Role `kit-feedback`.
- Fix the data in the current run.
- Append a `BACKLOG.md` friction line naming the rule and a test that would
  have caught it.
- Do **not** edit workflow text in the same run unless the PM asks for a kit
  fix. Stops one-off rule patches.

## 2b. Repeats, trust, privacy, partial reads

### Duplicates and versions

Before extracting, run
`python3 scripts/source_index.py find-duplicate --root <live> --path <file>`.
Same content in another format (PDF / Pages / PNG / HTML) or an older version
→ outcome `duplicate` with `same_as`. Keep the most complete copy. Older
versions → `superseded`. Facts logged once.

### Multi-file bundles

One workbook exported to many CSVs, or `.xlsx` + `.xlsm`: group by stem into
one bundle. One data profile per bundle, listing member files.

### One meeting, several transcripts

Match on meeting title, date, attendees. Fullest transcript is primary. Others
fill gaps only and are marked `duplicate` with `same_as`.

### Own outputs coming back

Paths under `outputs/`, `drafts/`, `prototypes/`, or detected via
`python3 scripts/source_index.py is-own-output --path <file>`:

- Origin `derived-own`.
- Never a source of evidence, decisions, or metrics (rule 26). Index only,
  unless the PM says it now contains new input.

### AI summaries and second-hand sources

Slack AI digests, AI-written syntheses: origin `ai-summary` or `second-hand`.
In the cross-source pass they **cannot confirm** a held item alone.
Confirmation needs at least one `primary` source. A superseded AI report is
not extracted.

### Status claims

"Done", "pulled into sprint", "at 100%": tag `needs-authority`. When an
Atlassian connection or export is available, check Jira in the same run.
Jira wins (SOURCE-POLICY); conflict → assumptions. With no Jira access, label
the claim unverified.

### Sensitivity

Set `sensitivity` from content: merchant/customer names, partner/commercial
terms (pricing, organizations, payouts), personal data. Data profiles,
summaries, and EV rows must be **redacted before any durable write** (rule 15).
Profiles list field names and counts, never identifying values.

### Partial reads

Connector can't read comments, sampled vision pages, sheets skipped: record in
`unread`. QC lists them. Never report "nothing found" for a source that was
only partly read.

## 2a. Asking questions and proportion

- **Ask budget**: at most one batch of questions per run, and only for gaps
  that block a write the source clearly calls for (e.g. a named decision with
  an unclear owner). Never ask for owners, decisions, or adoption on
  `exploratory-thinking` sources.
- **Parked questions**: when the PM says "not yet", "can't answer", or "just
  notes", mark the question `parked YYYY-MM-DD` in
  `reference/context/assumptions-and-open-questions.md`. Do not raise a parked
  question again unless a new source touches it.
- **Answers to earlier questions** (e.g. "W+M = web plus marketing"): resolve
  the open item in place and update the one affected surface. Do not re-run
  the whole fan-out.
- **Proportion**: writing scales with the source. A short note usually needs
  1–3 surfaces, not every surface a claim type could reach. QC lists what was
  written and why.
- **Glossary**: acronyms and standing internal names only (W+M, MAPU, AAB).
  Ordinary phrases ("end-to-end evals") stay in the learning entry.

## 5. Cross-source pass

After claim fan-out (or after indexing/holding), before the QC report:

```bash
python3 scripts/source_index.py match --root <live> --entities "INIT-004,MAPU,…"
```

Plus a short read of matching register rows. Then:

- One weak mention stays `hold`.
- A second independent source raises confidence. **At least one of the two
  must be `primary`.** Duplicates, AI summaries, and own outputs never count
  as independent. Promote through fan-out and set `status=promoted`.
- A conflicting source → open question in assumptions.
- A fragment that completes an existing DEC / RISK / definition is promoted,
  citing that ID.

## 6. Initiative candidates (Tier 3, proposal only)

Raise `INITIATIVE CANDIDATE` when at least **3** of these hold:

- topic recurs across sources
- dedicated artifacts exist
- decisions, commitments, or risks are attached
- several initiatives depend on it
- it has its own outcome
- it needs ongoing review

Proposal format: name, evidence count per criterion, proposed parent or
dependents. Never create the INIT row silently. Sits alongside the "fold
small enhancements" rule, which stays.

## 7. Implications check (write only what applies)

1. Does this change product strategy?
2. Does it reveal or change an initiative?
3. Does it create a dependency between initiatives?
4. Does it change the definitions products or agents rely on?

Answers become labeled hypotheses, proposals, or
`next consumer: /report strategy-refresh`. Never silent rewrites.
Surface 5 (`current-priorities.md`) is **proposal only** for strategy-frame
writes (Tier 3).
