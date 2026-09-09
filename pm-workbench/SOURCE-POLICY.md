# SOURCE-POLICY.md — who wins when sources disagree

Registers and local files are an INDEX and working memory — never the ultimate authority. When sources conflict, report the conflict; never silently pick one (CLAUDE.md rule 7). When you must rank, this is the hierarchy:

| Information | Authoritative source | Notes |
|---|---|---|
| Current delivery status | Jira | Meeting notes/Slack are leads to verify against Jira, not overrides |
| Approved product scope | Approved Confluence PRD + a recorded decision with a named owner | A newer Slack message does NOT override an approved scope — it's a signal that a decision may be pending |
| Implemented behavior | Verified product behavior + current code | Code is evidence of implementation, not proof of deployment or intent |
| Official metrics | QuickSight / FullStory / experiment tool / OKR site | Never recalculate; a stale export loses to the live dashboard |
| Support history | Jira support cases | |
| Launch commitments | The approved launch record | Slack cannot override |
| Customer problems | Direct research + support evidence + observed behavior | A stakeholder's opinion is input, not evidence |
| Meeting interpretation | Local notes, until validated or formally recorded | |
| Prototype behavior | The prototype repo itself | |

Corollary: **recency ≠ authority.** The most recent mention of something is often the least authoritative (a hallway comment vs. an approved PRD). Newer information earns a "possible pending change" flag, not a silent state update.


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
approved scope decision. `/roadmap-update` and `/okr-refresh` cite this table.

Note on completeness: CSV/Markdown fallbacks are fine during setup, but the
roadmap workflow is not "done" until the real spreadsheet and deck templates are
configured and one full change has actually applied across every required
surface. Until then, say so honestly — "drafted for these surfaces" is not
"the roadmap is updated."
