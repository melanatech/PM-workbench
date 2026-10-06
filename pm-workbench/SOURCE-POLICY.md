# SOURCE-POLICY.md — who wins when sources disagree

Registers and local files are an INDEX and working memory — never the ultimate authority. When sources conflict, report the conflict; never silently pick one (CLAUDE.md rule 7). When you must rank, this is the hierarchy:

| Information | Authoritative source | Notes |
|---|---|---|
| Current delivery status | Jira | Meeting notes/Slack are leads to verify against Jira, not overrides |
| Approved product scope | Approved Confluence PRD + a recorded decision with a named owner | A newer Slack message does NOT override an approved scope — it's a signal that a decision may be pending |
| Implemented behavior | Verified product behavior + current code | Code is evidence of implementation, not proof of deployment or intent |
| Official metrics | Pre-calculated value with as-of date: OKR dashboard (preferred when available), or internal MBR/PPP/deck/wiki/export that states the same metric | Never recalculate from raw rows. Log to `state/okr-history.csv` with source path. Live dashboard beats a same-definition older deck; a **newer as_of_date** on an internal doc is the working figure while conflicts of **definition/cohort** stay open (ask what's official). Not web search. |
| Support history | Jira support cases | |
| Launch commitments | The approved launch record | Slack cannot override |
| Customer problems | Direct research + support evidence + observed behavior | A stakeholder's opinion or proposed enhancement is **input**: log it on `registers/evidence.csv` as `inferred` (or `reported` if they are relaying users). It must not be treated as proof of a customer problem when answering discovery questions or writing PRDs |
| Meeting interpretation | Local notes, until validated or formally recorded | |
| Prototype behavior | The prototype repo itself | |

Corollary: **recency ≠ authority for decisions and ideas.** A hallway Slack comment does not override an approved PRD; newer opinion earns a "possible pending change" flag, not a silent scope update.

**Exception — dated internal numbers:** for metric values from internal documents (MBR decks, PPPs, leadership packs, wiki metric pages) that carry an as-of or report date, treat the **most recent as_of_date** as the best available reading of that series unless a same-definition live dashboard contradicts it. Still surface definition conflicts (e.g. one KR vs Payments/Commerce splits) and ask which is official — do not silently merge unlike metrics. This exception does **not** apply to web search or unverified external pages.


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
