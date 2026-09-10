# AGENTS.md — the third mechanism (alongside commands and skills)

Three different things live in `.claude/`, and they solve different problems:

| Mechanism | Where | What it is | Why use it |
|---|---|---|---|
| **Command** | `.claude/commands/*.md` | A prompt template you (or the menu) invoke by name | Your everyday workflows — this is most of the kit |
| **Skill** | `.claude/skills/*/SKILL.md` | Same idea, but Claude can auto-invoke it from plain language | Once a command is stable and you'd rather just describe the task (see SKILLS.md) |
| **Subagent** | `.claude/agents/*.md` | A separate Claude instance with its OWN context window and tool access, spawned mid-task | When a step needs isolation — either to stay unbiased, or to keep heavy reading out of your main session |

## Where subagents are actually used, and why

The test is: does this step need **isolation** — either independence from bias, or heavy reading that shouldn't linger in the main session? Applied consistently, not just to the two most obvious cases:

**Bias-isolation (an independent verdict matters more than efficiency):**
- `causal-reviewer`, `instrumentation-reviewer`, `ux-harm-reviewer`, `business-value-reviewer`, `ops-feasibility-reviewer` — the five `/experiment-package` design reviewers. Each sees only the design, not each other or who wrote it.
- `results-integrity-reviewer` — same logic, applied to `/experiment-analyze`. Sees only the pre-registered design and raw results, never the narrative someone already drafted, so it can catch goalpost-moving or post-hoc segment-fishing without being anchored to a preferred conclusion.

**Heavy-read isolation (keep large raw material out of the main session):**
- `launch-drift-detector` (`/launch-package`) — PRD + Jira + prototype + docs + marketing at once
- `discovery-source-reader` (`/discovery`) — chat channels + support pages + behavior-analytics segments
- `competitive-capture-agent` (`/competitive-scan`) — several competitor sites at once
- `return-window-scanner` (`/return-brief`) — weeks of chat/Jira/wiki/shared-drive history; the single heaviest read in the kit
- `strategy-synthesizer` (`/strategy-refresh`) — evidence register + OKR history + competitive log + learning files together
- `code-repo-explorer` (`/code-dive`, reused by `/prototype-build`) — a whole cloned repo's file tree
- `internal-docs-reader` — general-purpose, dispatched **alongside** another subagent (not instead of it) whenever a task benefits from durable internal documents: user research reports, wiki pages beyond Jira/support, the shared drive, or the local file browser. Used by `/discovery`, `/prd-package`, `/research-plan`, `/strategy-refresh`, `/competitive-scan`, `/research-package`, and `/learn-product-flow`. It checks `reference/user-research/` first (already-indexed) before reading raw documents, and processed findings get indexed there so the next task doesn't re-read the same file.

**Deliberately left as plain commands** — no isolation benefit, would just add latency: `meeting-closeout`, `weekly-update`, `okr-refresh`, `process-inbox`, `rotate-registers`. Note that `jira-reconcile` and `learn-product-flow` remain plain commands overall but now dispatch `internal-docs-reader` for one specific sub-step (a targeted decision-doc check, and the doc-vs-reality comparison, respectively) rather than reading those sources inline — a command can be "mostly plain" and still delegate the one part of it that's genuinely heavy.

## PRD and prototyping: the fullest use of the pattern

These two got a deeper treatment than anything else, because they're the clearest case of both needs at once, plus a third one nothing else in the kit has: **two artifacts that need to stay consistent with each other as both evolve.**

- **Heavy-read isolation:** `prd-context-gatherer` assembles evidence, code findings, OKR baseline, competitive log, and prior decisions/risks in one dispatch, so `/prd-package` starts from a grounding brief instead of five separate file reads.
- **Multi-stakeholder review:** `eng-feasibility-reviewer`, `design-ux-reviewer`, `data-instrumentation-reviewer`, `business-revenue-reviewer`, `customer-facing-reviewer` — five reviewers (Standard dispatches the 1–2 most relevant; Deep runs all five), each blind to the others, **shared between `/prd-package` and `/prototype-build`** so a PRD and its prototype get judged by the same five lenses. Unlike the experiment panel, this isn't a hard gate — a real PRD is allowed to reach real stakeholders imperfect. Every FAIL/CONDITION becomes an entry in the PRD's own "anticipated objections" section instead of blocking anything, which is the actual point for the buy-in duty on your original task list.
- **Cross-artifact reconciliation:** `prd-prototype-reconciler` is the new piece — it doesn't review one artifact, it compares two. Given the current PRD and the current prototype's actual behavior, it reports both directions of drift ("PRD says X, prototype does Y" and "prototype does Z, PRD never mentions it") plus, if research findings exist, whether testing proved the PRD's assumption wrong rather than the prototype. It never decides which side is right — that's a call the main session brings back to you. It runs automatically at the end of both `/prd-package` and `/prototype-build` whenever the other artifact already exists, and is also callable standalone as `/prd-prototype-sync` for whenever something changes outside the normal flow (a stakeholder comment, a build decision) and the two need a manual re-check.

An earlier pass of this kit only built two of these (the experiment reviewers and the launch detector) and stopped once it found clean examples, without checking the rest of the list against the same test — that gap is what the six additions above fix.

## What subagents are NOT
Not the "agent teams" feature you may see mentioned elsewhere (multiple agents coordinating with each other, assigning work back and forth) — that's a separate, more experimental Claude Code feature. Subagents here are simpler and one-directional: dispatch, isolated work, a result comes back. Stable, not experimental, and the right scope for this kit.
