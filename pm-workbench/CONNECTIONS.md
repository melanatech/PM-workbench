# CONNECTIONS.md — how everything actually links together

Almost nothing in this kit runs in isolation. This is the map — what each command writes, what it reads, and what notices it when something else changes. Read this when a command feels like it's missing context it should have, or when adding something new (see EVOLVING.md for that recipe).

## The reference layer: `reference/links.csv`

A lightweight bookmark list, not a register — logged links to templates, policy docs, and dashboards that live in Confluence/SharePoint and can be fetched live rather than downloaded and processed. Checked by `internal-docs-reader` before it goes looking for a local copy. See `reference/LINKS-README.md`.

## The hub: `registers/initiatives.csv`

One row per feature, tracking its stage and links to every artifact about it. Stage values: `prd`, `prototype`, `experiment`, `launched`, `killed`, `iterating` (post-launch work on a shipped thing). **The stage is descriptive, not a forced pipeline** — real work doesn't move linearly. A prototype can precede a PRD, an experiment can run without either, and a launched feature loops back to `iterating`. Each command sets the stage that reflects what just happened; none of them should refuse to run because "the previous stage" hasn't happened. This is what turns "a bunch of files that happen to share a feature name" into something commands can actually query. Written by `/prd-package`, `/prototype-build`, `/experiment-package`, `/experiment-analyze`, `/launch-package`. Read (cross-checked) by `/discovery`, `/competitive-scan`, `/meeting-closeout`, `/jira-reconcile`, `/okr-refresh`, `/strategy-refresh`, `/weekly-update`, and `/ripple-check`.

## Full write/read map

| Command | Writes to | Reads / cross-checks against |
|---|---|---|
| `/return-brief` | `registers/decisions.csv`, `registers/risks.csv`, `registers/commitments.csv` (seeds them) | Slack/Jira/Confluence/SharePoint (via `return-window-scanner`) |
| `/meeting-closeout` | `registers/decisions.csv`, `registers/commitments.csv`, `registers/risks.csv` | Same registers (conflict check) + `registers/initiatives.csv` (downstream flag) + Jira |
| `/jira-reconcile` | `state/jira-snapshots/`, proposed Jira writes | `registers/decisions.csv`, `commitments.csv`, `evidence.csv`, `initiatives.csv`, recent meeting outputs |
| `/discovery` | `registers/evidence.csv` | Slack/support/FullStory (`discovery-source-reader`) + internal docs (`internal-docs-reader`) + `registers/initiatives.csv` (relevance flag) |
| `/okr-refresh` | `state/okr-history.csv` | Dashboard values + `registers/initiatives.csv` (which initiative this metric belongs to) |
| `/research-plan` | `outputs/research/[date]-candidates.md`, (later) `registers/research-participants.csv` | QuickSight/FullStory/Jira + internal docs (personas/prior research) |
| `/prd-package` | `outputs/prds/[feature]/`, `registers/initiatives.csv` (creates/updates) | `evidence.csv`, `learning/`, `okr-history.csv`, competitive log, `decisions.csv`/`risks.csv` (via `prd-context-gatherer` + `internal-docs-reader`) + `prototypes/[feature]/` if it exists |
| `/prototype-build` | `prototypes/[feature]/`, `registers/initiatives.csv` (updates) | `learning/`, repo patterns (`code-repo-explorer`) + `outputs/prds/[feature]/` if it exists |
| `/prd-prototype-sync` | (report only, no writes) | Both `outputs/prds/[feature]/` and `prototypes/[feature]/` directly |
| `/research-package` | `outputs/research/[name]/` | Prior research (`internal-docs-reader`) + prototype it's testing |
| `/experiment-package` | `outputs/experiments/[name]/`, `registers/initiatives.csv` (updates) | `evidence.csv`, `okr-history.csv` (baseline), five review subagents |
| `/experiment-analyze` | `registers/decisions.csv`, `registers/initiatives.csv` (stage → shipped/killed) | The pre-registered design + results + `results-integrity-reviewer` |
| `/launch-package` | `outputs/launches/[feature]/`, `registers/initiatives.csv` (stage → launched) | PRD, Jira, prototype, docs (`launch-drift-detector`) + `initiatives.csv` (related_okr for monitoring plan) |
| `/competitive-scan` | `outputs/monthly/competitive-log.md` | External sites (`competitive-capture-agent`) + internal battlecards (`internal-docs-reader`) + `registers/initiatives.csv` (relevance flag) |
| `/strategy-refresh` | `outputs/strategy/[date]/` | Everything: `evidence.csv`, `okr-history.csv`, competitive log, `learning/` (via `strategy-synthesizer` + `internal-docs-reader`) + `registers/initiatives.csv` (portfolio view) |
| `/weekly-update` | `outputs/weekly/[date]-leadership-update.md` | `initiatives.csv`, jira-reconcile output, `commitments.csv`, `decisions.csv`, `risks.csv`, discovery output, OKR narrative |
| `/meeting-prep` | (report only) | `registers/initiatives.csv`, `decisions.csv`, `risks.csv`, `commitments.csv`, recent meeting outputs, `reference/links.csv` — the before-meeting mirror of `/meeting-closeout`'s after |
| `/ripple-check` | (report only, offers to log) | Everything — the on-demand version of what the commands above do automatically |

## The two ways connection actually happens

**Automatic, baked into a command's own steps** — most of the table above. When you run `/meeting-closeout`, it doesn't just file the decision; it checks whether that decision touches something already in motion and tells you.

**On-demand, when something happened outside the normal flow** — `/ripple-check`. Use it after a hallway conversation, a decision made over Slack DM that never became a formal meeting, or news that arrived some other way. It's the same cross-checking logic, invoked manually instead of triggered by a specific command's normal work.

## Where this can still fall short (be honest with yourself about it)

The cross-checks above are only as good as the initiative actually being *in* `initiatives.csv` with the right name. If you build a prototype before ever running `/prd-package`, or a feature never gets a formal PRD at all, nothing will connect it automatically — that's why `/prototype-build` creates a row even without a PRD, and why it's worth naming things consistently. When in doubt about whether something is tracked, just ask in a session — "is [feature] in the initiatives register?" — rather than assuming the connection exists.
