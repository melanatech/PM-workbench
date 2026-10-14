# Plain-language routing — primetime rule

Applies to every session (interactive or scheduled), every user of this kit —
not only people who remember slash commands.

## The rule

When the user's request matches a row in the **Command menu** below (or the
Choosing lists on `/capture`, `/brief`, `/sync`, `/discover`, `/build`,
`/report`), **run that cluster/workflow**. Do not invent a lighter ad-hoc path
(peek a folder, skim a file, "quick check") that skips the workflow's Step 0,
intake gates, fan-out, or subagent dispatches.

- **Match → run.** Do not ask "did you mean `/capture process-inbox`?" when the
  phrasing clearly matches. Confirm only when two workflows fit equally well.
- **Ambiguous → one short question**, then run. Do not improvise while waiting.
- **No menu match →** answer from registers/`outputs/`/`learning/` if it is a
  lookup; otherwise ask which workflow or what outcome they want.
- **Factual lookups** (commit / due / decide / initiative status / metric /
  inbox empty / PRD scope / board) → authority-lookup skill, CLAUDE.md rule 25:
  authoritative surface first, then secondary sources. Never lead
  with `find` on raw archive or one convenient file as if complete.

## Why this exists

Slash commands already work. Real users say "process the web clips", "draft my
update", "is the board stale." Without this rule, the model improvises and
skips mandatory steps (e.g. Downloads pull before claiming inbox empty). That
is a kit defect, not user error.

## Skills

High-frequency phrases also have `.claude/skills/*/SKILL.md` files whose
`description:` fields are the auto-invoke signal. Skills point at the same
workflows; they do not replace `routes.json`. Prefer the skill or the slash
command — never a third improvised path.

## Anti-patterns (forbidden)

- "I'll just check `inbox/`…" when intake/process-inbox matches
- "Quick look at Jira…" when jira-reconcile matches
- "Summarize from memory/registers only…" when weekly-update or okr-refresh matches
  and the workflow requires reconciliation first
- Improvising a "quick release readout" when ship-signal / "did this ship move the needle" matches
- Drafting a Now/Next/Later list from registers alone when "build a roadmap" or "draft a roadmap from scratch" matches — run `/report roadmap-build` (discovery phase first)
- Treating "the roadmap changed" as a from-scratch roadmap — that is `/sync roadmap-update`
- Skipping Deep usage estimate / required-input gates because the user used
  casual wording
- Treating "context constraints" as a reason to skip the matched workflow
  (dispatch a heavy-read subagent instead — CLAUDE.md)
- Answering a factual lookup from one transcript, `find` hit, or folder peek
  without reading the authoritative surface first (CLAUDE.md rule 25 —
  commitments.csv for promises; intake_status for inbox; initiatives/PRD path
  for scope; etc.)
- When INIT-/COM- is named and the ask is a product brief / check-in brief /
  explore options / alternatives before a PRD: improvising a generic brainstorm
  skill or freeform chat that skips `prd-context-gatherer` — run
  `/discover explore-brief` instead
- Native WebSearch-only (or inventing URLs) when external grounding is needed —
  use `scripts/web_search.py` per `_web-search.md` and write `state/web-search/`
  (or `state/competitive/` for competitive-scan)
- Re-reading `repos/` for instrumentation/events/code behavior when
  `outputs/daily/` or `learning/` already has a dated analysis of that topic —
  cite the workspace analysis first (CLAUDE.md rule 25)

Routers: after choosing a workflow, dispatch per `_protocol.md` immediately.

## Eight commands — the workflows are arguments

You type one of eight commands. Six are routers over the workflows in `routes.json`; `/quick-close` (the 60-second capture) and `/todo` stand alone.

| Command | Workflows behind it |
|---|---|
| `/capture` | `meeting-closeout`, `process-inbox` |
| `/brief` | `get-started`, `context-setup`, `daily-brief`, `return-brief`, `meeting-prep` |
| `/sync` | `jira-reconcile`, `ripple-check`, `context-reconcile`, `roadmap-update`, `rotate-registers` |
| `/discover` | `discovery`, `research-plan`, `research-package`, `competitive-scan`, `learn-product-flow`, `code-dive`, `explore-brief` |
| `/build` | `prd-package`, `prototype-build`, `prd-prototype-sync`, `experiment-package`, `experiment-analyze`, `launch-package` |
| `/report` | `weekly-update`, `okr-refresh`, `strategy-refresh`, `roadmap-build`, `workbench-health`, `monthly-review`, `ship-signal` |

Name the workflow as the first word (`/build prd-package Bulk Export`) or describe the job (`/build spec out Bulk Export`) and the router picks from the initiative's stage, asking if it cannot tell. Older notes may say `/prd-package` or `/daily-brief`. Those are workflow names; run them as `/build prd-package`, `/brief daily-brief`. Week one is `/quick-close`, `/capture`, `/report`, `/sync`, `/discover`, plus `/brief`. `/build` and `/todo` may be name-only in `.claude/settings.json`. `.claude/settings.core.json` hides them; `.claude/settings.full.json` shows everything. Workflow texts live in `.claude/workflows/`.

## Command menu — when I describe a need instead of typing a slash command

Plain language that matches a row **is** an instruction to run that workflow. Confirm only when two rows fit equally. Future users will not memorize slash commands; this menu plus the skills are the product surface.

| I say something like... | Run |
|---|---|
| "How do I get started" / "set up the workbench" / "create my pm-live" / "first-time setup" / "new user setup" | `/brief get-started` |
| "Fill my context" / "set up my context" / "context setup" | `/brief context-setup` |
| "What changed while I was out" / "back from leave" | `/brief return-brief` |
| "What's new" / "morning" / "catch me up" / "daily brief" | `/brief daily-brief` |
| "Catch up the inbox" / "process clips" / "web clips" / "process documents" / "I uploaded something" / "new PDFs" / "what's waiting" | `/capture process-inbox` |
| "Close out this meeting" / paste notes / "log this meeting" | `/capture meeting-closeout` |
| Between meetings, 60 seconds or less / "quick capture" | `/quick-close` |
| "Add / update / finish / drop a to-do" / "what's on my list" / "what should I be doing" / "help me do TODO-nnn" / "draft help for what is due" | `/todo` (`sweep` drafts for the few that are due) |
| "Plan these to-dos" / "plan the queue" / "dispatch plan for TODO-nnn" / "what would it take to do these" | `/todo plan` |
| "Dispatch the plan" / "run the approved to-do plan" / "draft these in parallel" | `/todo dispatch` |
| "Which to-dos did I already finish" / "reconcile to-dos" / "mark the ones I already did" | `/todo reconcile` (propose only; `done` only after I confirm) |
| Before a meeting, need to walk in ready / "prep me for" | `/brief meeting-prep` |
| "Check the Jira board" / "is anything stale" / "board hygiene" | `/sync jira-reconcile` |
| "What's new in discovery" / "any new themes" / "what are users saying" | `/discover discovery` |
| "Pull this week's/month's numbers" / "OKR refresh" / "update metrics" | `/report okr-refresh` |
| "Draft my weekly update" / "leadership update" | `/report weekly-update` |
| "Ship signal" / "did this release move the needle" / "advance the release loop" / "release readout" | `/report ship-signal` |
| "Find people to talk to about X" / "plan research" (criteria only — never names) | `/discover research-plan` |
| "Product brief" / "explore brief" / "check-in brief" / "options for INIT-/COM-" / "alternatives before a PRD" | `/discover explore-brief` |
| "Spec out X" / "write a PRD for X" | `/build prd-package` |
| "Build a prototype of X" / "mock this up" | `/build prototype-build` |
| "Do the PRD and prototype for X still match" | `/build prd-prototype-sync` |
| "What else does this affect" / a decision that didn't go through a normal command | `/sync ripple-check` |
| "Propagate context everywhere" / "backfill from archive" / "todos feel wrong" / open questions scattered | `/sync context-reconcile` |
| "Set up a test for X" / "research package" | `/discover research-package` |
| "Design an experiment for X" / "A/B test design" | `/build experiment-package` |
| "What did the experiment results say" | `/build experiment-analyze` |
| "Get this ready to launch" / "launch package" | `/build launch-package` |
| "The roadmap changed" / features moved or were added | `/sync roadmap-update` |
| "Build a roadmap" / "draft a roadmap from scratch" | `/report roadmap-build` |
| "Strategy from scratch" / "draft a strategy from scratch" | `/report strategy-refresh` |
| "What are competitors doing" / "competitive scan" | `/discover competitive-scan` |
| "Search the web for" / "market scan" / "how do others solve" / external grounding (problems, market, users, solutions) | skill `web-search` → `_web-search.md` (`state/web-search/`); if it's a brief or PRD ask, run explore-brief / prd-package instead |
| "Update the strategy doc" / "strategy refresh" | `/report strategy-refresh` |
| "I need to understand how X works" (product) | `/discover learn-product-flow` then often `/discover code-dive` |
| "How does X work in the code" / "code dive" | `/discover code-dive` |
| "The registers are getting huge" | `/sync rotate-registers` |
| "How is the workbench itself doing" / "what do I actually use" | `/report workbench-health` |
| "Is the workbench helping" / monthly check on dropped balls and decision quality | `/report monthly-review` |

Not everything needs a command. "What did we decide about X" and similar factual asks are authority-lookup (rule 25), not a workflow. If the phrasing matches a row above, that is not a freeform lookup.
