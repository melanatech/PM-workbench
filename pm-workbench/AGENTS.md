# AGENTS.md — subagent index

Subagents are one-directional: dispatch, isolated work, a result comes back. They are not a multi-agent team that assigns work to each other. Use one when a step needs isolation (an unbiased verdict, or a heavy read that should not stay in the main session). Runner behavior, pauses, and execution modes live in `.claude/workflows/_protocol.md`. Standing rules live in CLAUDE.md — do not restate them here.

| Mechanism | Where | What it is |
|---|---|---|
| **Command** | `.claude/commands/*.md` | What you type. Six thin routers (`/capture`, `/brief`, `/sync`, `/discover`, `/build`, `/report`) plus `/quick-close` and `/todo`. |
| **Workflow** | `.claude/workflows/*.md` | The step text. A router reads one; `workflow-runner` carries it out. |
| **Skill** | `.claude/skills/*/SKILL.md` | Same job, auto-invoked from plain language (see SKILLS.md). |
| **Subagent** | `.claude/agents/*.md` | A separate context window, spawned mid-task. |

| Agent | Kind | Used by |
|---|---|---|
| `workflow-runner` | Runner | The six cluster commands, on the model in `routes.json`. Returns RESULT, PROPOSALS, or QUESTIONS. `inline` skips it. |
| `causal-reviewer`, `instrumentation-reviewer`, `ux-harm-reviewer`, `business-value-reviewer`, `ops-feasibility-reviewer` | Blind review | `/build experiment-package` (each sees only the design) |
| `results-integrity-reviewer` | Blind review | `/build experiment-analyze` (pre-registered design + raw results only) |
| `eng-feasibility-reviewer`, `design-ux-reviewer`, `data-instrumentation-reviewer`, `business-revenue-reviewer`, `customer-facing-reviewer` | Review, not a hard gate | `/build prd-package` and `/build prototype-build`. FAIL/CONDITION becomes an anticipated objection. |
| `prd-prototype-reconciler` | Cross-artifact | End of prd-package and prototype-build when the other artifact exists; also `/build prd-prototype-sync`. Reports drift; does not pick a winner. |
| `prd-context-gatherer` | Heavy read | `/discover explore-brief` and `/build prd-package` (check-in brief vs full PRD). Do not invent a second gatherer. |
| `launch-drift-detector` | Heavy read | `/build launch-package` |
| `discovery-source-reader` | Heavy read | `/discover discovery`; also the discovery phase in `/report roadmap-build` and strategy-refresh from scratch. Not a second gatherer. |
| `competitive-capture-agent` | Heavy read | `/discover competitive-scan` (`scripts/web_search.py` first; writes `state/competitive/`). Reused by roadmap-build and strategy-refresh from scratch when no fresh capture exists. |
| `return-window-scanner` | Heavy read | `/brief return-brief` |
| `strategy-synthesizer` | Heavy read | `/report strategy-refresh` (refresh path; not the from-scratch discovery phase) |
| `strategy-red-team-reviewer` | Blind review | `/report strategy-refresh` and `/report roadmap-build` (Standard: one pass). Sees the draft and its cited sources only. Findings become Anticipated objections. Optional single pass on `/report weekly-update` when the PM asks; not the Fast default. |
| `external-readiness-reviewer` | Blind review | Publish step in Standard or Deep (`.claude/workflows/_protocol.md`). Sees the rendered file and one audience line only. Fast skips it. |
| `code-repo-explorer` | Heavy read | `/discover code-dive`; reused by `/build prototype-build` |
| `todo-worker` | Heavy read | `/todo propose` and `/todo work` (read-only). Returns `[NEEDS INPUT: …]`; the main session asks. |
| `internal-docs-reader` | Heavy read | Alongside another agent for research, wiki, and shared-drive docs: discovery, prd-package, explore-brief, research-plan, strategy-refresh, competitive-scan, research-package, learn-product-flow. Checks `reference/user-research/` first. |

**Plain (no subagent):** `meeting-closeout`, `weekly-update`, `okr-refresh`, `process-inbox`, `rotate-registers`, and `/todo` add/update/done/drop/list. `jira-reconcile` and `learn-product-flow` stay plain overall and dispatch `internal-docs-reader` for one sub-step.

Context pressure is a dispatch signal (`_protocol.md` execution modes). Do not thin a deliverable because the session feels full.

## Keeping this fast — context/token guardrails

- Register files (`registers/*.csv`) grow every week. Default to reading **only recent or relevant rows** (last 60–90 days, or filtered by id or metric) unless the ask is for full history (CLAUDE.md rule 13).
- If a register or state file is large enough that a full read would be wasteful, say so and suggest `/sync rotate-registers`.
- In a long session, `/compact` or `/clear` is available. This workspace has no automatic retrieval over growing files.
- Heavy reads (many discovery sources, a leave window, a strategy refresh, a code repo, multi-page decks) **dispatch the matching subagent above** so the main session gets a brief, not a skim. Bounded sources (max 12) choose which files; each chosen file still gets a full pass.
