# AGENTS.md — the third mechanism (alongside commands and skills)

Three different things live in `.claude/`, and they solve different problems:

| Mechanism | Where | What it is | Why use it |
|---|---|---|---|
| **Command** | `.claude/commands/*.md` | A prompt template you invoke by name. Eight exist: six thin cluster routers (`/capture`, `/brief`, `/sync`, `/discover`, `/build`, `/report`), `/quick-close`, `/todo` | What you type |
| **Workflow** | `.claude/workflows/*.md` | The original command texts, moved unchanged; not registered as commands. A router reads one and the `workflow-runner` subagent carries it out | Keeps 26 workflows behind 8 commands without rewriting their logic |
| **Skill** | `.claude/skills/*/SKILL.md` | Same idea, but Claude can auto-invoke it from plain language | Once a command is stable and you'd rather just describe the task (see SKILLS.md) |
| **Subagent** | `.claude/agents/*.md` | A separate Claude instance with its OWN context window and tool access, spawned mid-task | When a step needs isolation — either to stay unbiased, or to keep heavy reading out of your main session |

## Where subagents are actually used, and why

The test is: does this step need **isolation** — either independence from bias, or heavy reading that shouldn't linger in the main session? Applied consistently, not just to the two most obvious cases:

**The runner (model weight, and a router that must stay cheap):**
- `workflow-runner` — dispatched by the six cluster commands on the model `routes.json` names for the chosen workflow (haiku, sonnet or opus). It runs the workflow text, may dispatch the subagents below (a subagent can spawn subagents, to a limited depth), and returns RESULT, PROPOSALS or QUESTIONS because a subagent cannot ask you anything. The router relays and re-dispatches. `inline` skips the runner and runs the workflow in the current session.

**Bias-isolation (an independent verdict matters more than efficiency):**
- `causal-reviewer`, `instrumentation-reviewer`, `ux-harm-reviewer`, `business-value-reviewer`, `ops-feasibility-reviewer` — the five `/build experiment-package` design reviewers. Each sees only the design, not each other or who wrote it.
- `results-integrity-reviewer` — same logic, applied to `/build experiment-analyze`. Sees only the pre-registered design and raw results, never the narrative someone already drafted, so it can catch goalpost-moving or post-hoc segment-fishing without being anchored to a preferred conclusion.

**Heavy-read isolation (keep large raw material out of the main session):**
- `launch-drift-detector` (`/build launch-package`) — PRD + Jira + prototype + docs + marketing at once
- `discovery-source-reader` (`/discover discovery`) — chat channels + support pages + behavior-analytics segments
- `competitive-capture-agent` (`/discover competitive-scan`) — several competitor sites at once
- `return-window-scanner` (`/brief return-brief`) — weeks of chat/Jira/wiki/shared-drive history; the single heaviest read in the kit
- `strategy-synthesizer` (`/report strategy-refresh`) — evidence register + OKR history + competitive log + learning files together
- `code-repo-explorer` (`/discover code-dive`, reused by `/build prototype-build`) — a whole cloned repo's file tree
- `todo-worker` (`/todo propose` and `/todo work`) — reads a bounded set of inbox, meeting and output files to propose to-dos, or reads what one to-do points at to draft outreach or a research plan. Sonnet, read-only (Read/Glob/Grep). It is here for a second reason besides bulk: `/todo` itself runs on the cheap haiku model, and judgment work (what counts as a to-do, what a good message to support says) needs the stronger one. It cannot ask the PM anything, so it returns `[NEEDS INPUT: …]` lines and the main session asks.
- `internal-docs-reader` — general-purpose, dispatched **alongside** another subagent (not instead of it) whenever a task benefits from durable internal documents: user research reports, wiki pages beyond Jira/support, the shared drive, or the local file browser. Used by `/discover discovery`, `/build prd-package`, `/discover research-plan`, `/report strategy-refresh`, `/discover competitive-scan`, `/discover research-package`, and `/discover learn-product-flow`. It checks `reference/user-research/` first (already-indexed) before reading raw documents, and processed findings get indexed there so the next task doesn't re-read the same file.

**Deliberately left as plain commands** — no isolation benefit, would just add latency: `meeting-closeout`, `weekly-update`, `okr-refresh`, `process-inbox`, `rotate-registers`, and the add/update/done/drop/list modes of `/todo` (a script does that work). Note that `jira-reconcile` and `learn-product-flow` remain plain commands overall but now dispatch `internal-docs-reader` for one specific sub-step (a targeted decision-doc check, and the doc-vs-reality comparison, respectively) rather than reading those sources inline — a command can be "mostly plain" and still delegate the one part of it that's genuinely heavy.

## PRD and prototyping: the fullest use of the pattern

These two got a deeper treatment than anything else, because they're the clearest case of both needs at once, plus a third one nothing else in the kit has: **two artifacts that need to stay consistent with each other as both evolve.**

- **Heavy-read isolation:** `prd-context-gatherer` assembles evidence, code findings, OKR baseline, competitive log, and prior decisions/risks in one dispatch, so `/build prd-package` starts from a grounding brief instead of five separate file reads.
- **Multi-stakeholder review:** `eng-feasibility-reviewer`, `design-ux-reviewer`, `data-instrumentation-reviewer`, `business-revenue-reviewer`, `customer-facing-reviewer` — five reviewers (Standard dispatches the 1–2 most relevant; Deep runs all five), each blind to the others, **shared between `/build prd-package` and `/build prototype-build`** so a PRD and its prototype get judged by the same five lenses. Unlike the experiment panel, this isn't a hard gate — a real PRD is allowed to reach real stakeholders imperfect. Every FAIL/CONDITION becomes an entry in the PRD's own "anticipated objections" section instead of blocking anything, which is the actual point for the buy-in duty on your original task list.
- **Cross-artifact reconciliation:** `prd-prototype-reconciler` is the new piece — it doesn't review one artifact, it compares two. Given the current PRD and the current prototype's actual behavior, it reports both directions of drift ("PRD says X, prototype does Y" and "prototype does Z, PRD never mentions it") plus, if research findings exist, whether testing proved the PRD's assumption wrong rather than the prototype. It never decides which side is right — that's a call the main session brings back to you. It runs automatically at the end of both `/build prd-package` and `/build prototype-build` whenever the other artifact already exists, and is also callable standalone as `/build prd-prototype-sync` for whenever something changes outside the normal flow (a stakeholder comment, a build decision) and the two need a manual re-check.

An earlier pass of this kit only built two of these (the experiment reviewers and the launch detector) and stopped once it found clean examples, without checking the rest of the list against the same test — that gap is what the six additions above fix.

## What subagents are NOT
Not the "agent teams" feature you may see mentioned elsewhere (multiple agents coordinating with each other, assigning work back and forth) — that's a separate, more experimental Claude Code feature. Subagents here are simpler and one-directional: dispatch, isolated work, a result comes back. Stable, not experimental, and the right scope for this kit.
