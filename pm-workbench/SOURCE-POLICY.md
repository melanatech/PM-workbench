# SOURCE-POLICY.md — who wins when sources disagree

This file owns the claim-type authority ladder. CLAUDE.md points here; do not restate the ladder in other kit docs.

Registers and local files are an INDEX and working memory — never the ultimate authority. When sources conflict, report the conflict; never silently pick one (CLAUDE.md rule 8). When you must rank, this is the hierarchy:

| Information | Authoritative source | Notes |
|---|---|---|
| Current delivery status | Jira | Meeting notes/Slack are leads to verify against Jira, not overrides |
| Approved product scope | Approved Confluence PRD + a recorded decision with a named owner | A newer Slack message does NOT override an approved scope — it's a signal that a decision may be pending |
| Implemented behavior (split by claim type — see ladder below) | Highest available rung for that claim type | Code at a commit ≠ deployment; drafts/prototypes are never evidence |
| Official metrics | Pre-calculated value with as-of date **and** the timeframe/filters the figure covers: OKR dashboard (preferred when available), or internal leadership/metric deck, wiki page, or export that states the same metric | Never recalculate from raw rows. Log to `state/okr-history.csv` with source path, timeframe, filters, displayed delta (if any), calculation/definition `notes`, and per-series rows for multi-metric charts. Live dashboard beats a same-definition older deck; a **newer as_of_date** on an internal doc is the working figure while conflicts of **definition/cohort** stay open (ask what's official). Not web search. |
| Support history | Jira support cases | |
| Launch commitments | The approved launch record | Slack cannot override |
| Customer problems | Direct research + support evidence + observed behavior | A stakeholder's opinion or proposed enhancement is **input**: log it on `registers/evidence.csv` as `inferred` (or `reported` if they are relaying users). It must not be treated as proof of a customer problem when answering discovery questions or writing PRDs |
| Meeting interpretation | Local notes, until validated or formally recorded | |
| Prototype behavior | The prototype repo itself | |

## Claim-type authority ladder (current product facts)

When a claim is about **what exists / fires / behaves today**, pick the highest available rung. Self-authored `drafts/`, `prototypes/`, and product briefs are **never evidence** for these rows — follow their citations to a primary source, or mark `[hypothesis: …]`.

**What users see today (UI, copy, states)** — ranked highest first:
1. Live product capture (walkthrough clipper, dated screenshots)
2. Product UI base or product repo at a **named commit**, including locale/string files
3. Dated code-dive or product-flow analysis that cites (1) or (2)

**Instrumentation / events firing:**
1. Live network or analytics capture, dated
2. Dated inventory analysis that cites a repo commit
3. Repo at that commit

**Code behavior:**
1. Repo at a named commit
2. Dated code-dive that cites that commit

**Verification questions** ("how did you check?", "where did the baseline come from?"): answer with the chain down to the primary source (path:line, commit, capture). If the chain stops at a draft, say **unverified** and climb the ladder — never answer "the brief says."

**Deploy lag:** code at a commit is not proof of what merchants see (flags, shared packages, lagging `main`). Flag those gaps when the claim is about live UI.

**Cache-first:** prefer a dated analysis that already cites a primary source (`state/analysis-index.csv` / `context_preflight.py`) over re-reading `repos/` blank-slate. Reuse must carry the analysis's `primary_sources` forward, not treat the digest as the authority.

Corollary: **recency ≠ authority for decisions and ideas.** A hallway Slack comment does not override an approved PRD; newer opinion earns a "possible pending change" flag, not a silent scope update.

**Learning pages** (`learning/[area].md`, `learning/entities/`) are compiled summaries with source paths — never invent entity resolvers for unnamed gaps, and never treat them as overrides of DEC/COM/RISK/EV registers or approved PRDs.

**Exception — dated internal numbers:** for metric values from internal documents (leadership/metric decks, wiki metric pages, exports) that carry an as-of or report date, treat the **most recent as_of_date** as the best available reading of that series unless a same-definition live dashboard contradicts it. Still surface definition conflicts (e.g. one KR vs a split cohort of the same name) and ask which is official — do not silently merge unlike metrics. This exception does **not** apply to web search or unverified external pages.


## Roadmap surface authority

The roadmap lives on four surfaces; they are NOT equal sources. When they
disagree, this table decides which wins — never a silent pick, and never
"newest surface wins":

| Roadmap information | Authority |
|---|---|
| Current delivery status | **Jira** |
| Portfolio sequencing (Now/Next/Later) | the named **roadmap board or spreadsheet** |
| Approved strategic commitment | a **recorded decision** or approved planning doc |
| Detailed feature scope | the **approved PRD + decisions** |
| Leadership presentation | a **communication snapshot** — reflects, doesn't define |
| Slack update | a **notification** — never authority |

Consequence: a Slack message or a slide can never override Jira status or an
approved scope decision. `/sync roadmap-update` and `/report okr-refresh` cite this table.

Note on completeness: CSV/Markdown fallbacks are fine during setup, but the
roadmap workflow is not "done" until the real spreadsheet and deck templates are
configured and one full change has actually applied across every required
surface. Until then, say so honestly — "drafted for these surfaces" is not
"the roadmap is updated."
