# Router protocol — how /capture, /brief, /sync, /discover, /build and /report run a workflow

This file is read by the six cluster commands. It is not a command. The workflow files beside it (`.claude/workflows/<name>.md`) are the original command texts, moved unchanged; `routes.json` lists which cluster owns which workflow and which model it runs on. `prototype-build` is the one workflow that lives as a skill (`.claude/skills/prototype-build/SKILL.md`).

A router has no logic of its own. It picks a workflow, runs the safety steps below, hands the work to the `workflow-runner` subagent on the right model, and relays what comes back. Gates, readiness checks, and approval tiers stay inside the workflow text and in CLAUDE.md. Execution modes are below. Model choice is `.claude/workflows/routes.json`. The router can add a pause but never remove one.

## 0. Pause switch

If `state/PAUSE` exists, stop before doing anything: say "Paused: `state/PAUSE` exists. Delete that file to resume." and append nothing to any register. This applies to every run, attended or not, so a pause really means nothing moves. A run started by a schedule also logs `BLOCKED: paused` to `logs/run-log.csv`.

## 1. Pick the workflow

Do this silently. Do not print "checking routes.json", "reading the protocol", or any other plumbing line — those belong in the model's private thinking, not in chat.

1. Read `.claude/workflows/routes.json` and take the entry for your cluster.
2. If the first word of the input (leading `/` ignored) is one of the cluster's workflow names, that is the workflow and the rest of the input is its arguments. An old command name typed as a slash command inside a request ("run /prd-package on bulk export") means the same thing.
3. Otherwise use the selection rules in the router file **and** `.claude/workflows/_plain-language.md`. Plain language that matches a Choosing / Command-menu phrase **is** a workflow pick — dispatch it; do not improvise a lighter path outside the workflow.
4. If more than one workflow fits, or none does, ask one short question that names the options. Never guess between workflows that write different things.
5. A workflow name that belongs to another cluster: tell me which command owns it (`/build prd-package`, say) and stop.
6. If the input contains the word `inline`, run in inline mode (step 4) instead of dispatching.

## 2. Before running

- Read the workflow file for its execution mode (look for `Execution mode:` near the top; Fast, Standard, or Deep) and its required-input rules. If the line is missing, treat the workflow as **fast**.
- **Deep:** tell me to switch to Claude Code plan mode (Shift+Tab) for the usage estimate and the approval. Print the usage estimate the workflow asks for and wait for a yes. **Standard:** print exactly one line — `Running <workflow> (Standard / <model>)…` — then **dispatch immediately** in the same turn (that line means work is starting, not waiting). **Fast:** dispatch with no preamble.
- If the workflow's own required-input rule says to ask me something before starting (a feature's problem statement, a date range, a file), ask it now, in one batch. Do not dispatch with the answers missing.
- **Cache-first (consequential workflows):** if the workflow synthesizes product/tech/strategy facts (discover/*, build prd|prototype|experiment|launch, report weekly|okr|strategy|roadmap-build|ship-signal|monthly-review, brief meeting-prep|return-brief, sync ripple|context-reconcile|roadmap), require Step 0 `python3 scripts/context_preflight.py --root <live> --topic "<args>"` before gatherer/draft/`repos/` reads. Paste one preflight line in RESULT. Do not dispatch the runner until preflight has been run in this session (or the workflow file embeds that Step 0 for the runner). See CLAUDE.md rule 26.
- Write the marker for the run log: `printf '%s' '<cluster>:<workflow>' > state/.run-workflow` (create `state/` if absent). The Stop hook reads it and then removes it. Do not announce that you wrote the marker.
- **Never stop on "ready."** Do not end a turn with "Ready to reprocess," "Ready when you are," "I can run process-inbox next," "Clean — ready," or any equivalent status line that implies the next step is obvious but not started. If the next action is clear (inbox is staged, I said reprocess/reset/go, prep finished), **dispatch or run it in this same turn**. The only allowed stops before work are: Deep yes/no, a required-input question, `state/PAUSE`, or a real ambiguity between workflows.

## 2b. Gather plan

Before the first tool call of a workflow step, list that step's reads. Batch the independent reads in one turn. Sequence only a read that depends on an earlier result. When this session has already read a file, pass the distilled brief to a subagent instead of having it re-read the raw file. Re-reading the same file for a different task is fine: prompt caching makes the repeat cheap, and the purposes differ. No session cache.

`daily-brief`, `weekly-update`, and `jira-reconcile` each open with their own gather list. Other workflows follow this rule even when they do not repeat the list.

## 3. Dispatch

Call the Agent tool with `subagent_type: workflow-runner` and `model:` set to the model for that workflow in `routes.json`. The prompt must contain: the workflow name and its file path, the user's arguments verbatim, today's date, and any answers I have already given. Nothing else; the runner reads what it needs.

The runner returns exactly one of:

- **RESULT** — the work is done. Compact: what changed, paths, new or edited rows. Full artifact text only when the user cannot see it any other way (see Compact output below).
- **PROPOSALS** — Tier 2 or Tier 3 items waiting for approval (grouped diffs, Jira changes, anything that changes scope, owner, date or priority, anything to be sent).
- **QUESTIONS** — what it needs from me (CLAUDE.md rule 12), batched, with what it did finish.

**Relay = paste, then stop.** Your entire chat reply is the runner's return text, copied once, unchanged. Do not paraphrase, condense, re-bullet, or "confirm" it. Forbidden after the paste (exact examples from real bad runs): `Done.`, `Agent processed…`, `Registers updated:`, `Key conflicts:`, `Here's what happened`, `Output:`, a second list of the same DEC-/COM-/RISK- IDs, or any other wrap-up that restates RESULT. If RESULT already listed files and register rows, do not list them again under a new heading.

If the runner returned PROPOSALS or QUESTIONS, those sections are already the ask — present them as-is; do not rewrite them into a friendlier summary underneath. The workflow name and model belong as the **last line of RESULT** (the runner writes it); you do not add a second footer.

When I answer, dispatch the runner again with: the same workflow, the original arguments, the runner's previous output, and my answers. The runner continues from its run manifest (`logs/run-manifest-*.md`) and does not redo finished steps. Approvals I give are carried out by the runner on the second dispatch, then it re-reads the record and verifies it (CLAUDE.md rule 1). After two rounds on the same workflow with questions still open, stop and tell me plainly what is blocking. That plain stop is the only time the router writes its own prose instead of pasting the runner.

**Unattended runs** (started by a schedule, or I said I am away): there is nobody to answer. Do not wait and do not guess. Have the runner finish what it can, write what it finished to `outputs/` with the gaps labelled, append `BLOCKED: <what it needed>` to `logs/run-log.csv`, and stop (CLAUDE.md rule 22).

## 4. Inline mode (the fallback)

When I say `inline`, or when the runner cannot be dispatched: read the workflow file and carry it out yourself, in this session, with no runner. Say once at the top which model this session is running on and which one the workflow normally uses, so the cost is visible; if the workflow normally runs on opus and this session is not, offer `/model opus` before starting a Deep or Standard run. Everything else is the same as above.

## 5. Always

- The router never writes to a register, an output or an external system itself; the runner or the inline workflow does, under the same hooks.
- Old workflow names keep working as the first argument, so existing notes, schedules and habits still work with the cluster name in front.
- If `routes.json` or a workflow file is missing or unreadable, say which and stop. Do not reconstruct a workflow from memory.
- Do not add a closing "Done" or a second summary after a successful runner paste. The runner's last line already names the workflow and model.

## 6. Compact output (every workflow)

User-facing chat and durable files omit empty work. The checks in the workflow still run.

### 6a. Provenance vs equivalence (CLAUDE.md rule 23)

Citing a file as an **input** ("I used the 10-05 digest + the archive transcript") is fine. Claiming the **chat reply is the same as** that file is not, unless claim-checked or written this turn. Digests compress; ad-hoc answers expand. If you answered from a richer source than the linked digest, say so in one line. Never use "yes, it's all captured" as a topic checklist (keywords present) — that is how users open a file and find a thinner story than the chat.

**Provenance tags (CLAUDE.md rule 4):** in analytical RESULT prose, mark unverified claims `[hypothesis: …]` and unsourced model-knowledge claims `[external::training]`. Hypotheses that remain after the run → append to `reference/context/assumptions-and-open-questions.md`. Tags are not evidence.

### 6b. User-injected context (CLAUDE.md rule 24)

Applies outside capture workflows too (including after meeting-prep or "what happened on…"). New material facts from the PM → write-back or one concrete ask; never acknowledge-only when a register/learning row is clearly warranted.

- **Silent when empty:** no assumptions stated, no prior-decision change, no Jira/tickets, no drafts, no new register rows, "nothing excluded for relevance," unconfigured access paths. Write those only when they are a finding (a conflict, a missing owner, a ticket that disagrees) or a decision for me. **Exception:** if capture/meeting named PM-scoped product work and `initiatives.csv` has no matching row, that is a finding — seed the INIT- row (do not stay silent because the register was empty).
- **Do not narrate plumbing.** Do not explain that the kit clone has no live `.claude` data, that the Stop hook will write the run log, that "the run log row comes from the Stop hook," that you are about to read `routes.json`, or that you skipped a duplicate row — unless the project folder is wrong and work would land in the wrong place. Router setup and run-log bookkeeping stay in thinking; chat gets only the Standard one-liner (when applicable), then the runner's RESULT/PROPOSALS/QUESTIONS pasted once.
- **Do not announce readiness and wait.** "Ready to reprocess" / "Clean, ready" / "I can run X next" without starting X in the same turn is a protocol failure. Prep that enables a clear next workflow must continue into that workflow immediately (Fast/Standard) unless Deep needs a yes or a required input is missing.
- **Every existing path is a clickable link.** Any file or folder that exists under the live root must appear as `[path](path)` (workspace-relative; folders keep a trailing slash). Never leave a bare or backtick-only path for something that exists. Exceptions: fenced code blocks, shell commands, paths that do not exist yet, globs. Show each new artifact **once** with its link, then the content (or key sections). Do **not** use `file://` or bare absolute `/Users/...` paths. RESULT does not reprint it, and the router does not add "here's what happened" or "Done. Agent processed…".
- **Name resolution.** When the PM names a surface ("events digest", "weekly scorecard"), check `reference/context/workspace-aliases.md` then `context_preflight --topic "…"`. Do not guess.
- **No RESULT + Done pair.** A successful run is one message. If you catch yourself about to write a confirmation under the runner paste, delete it.
- **Re-runs.** If the meeting or input was already closed out, say that in a few lines, name the existing IDs, and go to PROPOSALS. Do not recap every empty checklist item.

## Execution modes

Usage is finite. A half-finished PRD that hits a limit is worse than a simpler run that completes. Every workflow runs in one mode. The declaration lives in the workflow body (`Execution mode: fast|standard|deep`) — frontmatter is stripped before the prompt reaches the model — and the PM can override inline ("run this in fast mode").

| Mode | For | Behavior |
|---|---|---|
| **Fast** | meetings, tracker hygiene, weekly updates, quick-close, ordinary discovery/OKR | one pass, no parallel reviewers, bounded source set, cheapest model that fits |
| **Standard** | most PRDs, research synthesis, launch packages, roadmap updates | context assembler + at most 1–2 relevant reviews, not the full panel |
| **Deep** | major strategy, high-stakes causal experiments, exec planning | parallel analysis, but only after printing a usage estimate and asking to proceed |

Governing rules for every mode:

- **Bounded sources.** Default max 12 source files per assembly. If more are relevant, report what was included and excluded and offer to widen. Bounded sources choose which files; they are not a license to skim the ones selected.
- **No context shortchanging.** Feeling context-constrained is not a reason to shallow-process or replace a full pass with a thinner summary. Dispatch the matching heavy-read subagent (AGENTS.md). Forbidden: "Given context constraints, I'll efficiently…", "too long so I'll only capture the vision", "selectively update existing initiatives" when the workflow asked for complete reconciliation.
- **No faux pauses.** "Ready to reprocess" / "About to run" / "I can do X next" without starting X in the same turn is not a mode. Fast and Standard continue; only Deep waits for an explicit yes (or a required-input question).
- **Bounded reviewers.** Fast = 0, Standard = 1–2, Deep = up to the full panel. Never invoke parallel reviewers in Fast or Standard.
- **Resumable manifest.** Any multi-step or multi-agent workflow writes `logs/run-manifest-[date-cmd].md` as it goes. If interrupted, re-running reads the manifest and continues.
- **No auto-revise loops.** A workflow proposes; it does not silently re-run itself to improve the output. Revision is the PM's call.
- **Compact fallback.** Only when usage or API budget is actually low, not because a document is long. Then finish with no extra agents, and say so. Prefer a heavy-read subagent before compact fallback.

## Model routing

`.claude/workflows/routes.json` is the single source of truth for which model each workflow runs on. Change a model there, not in the workflow file. `/quick-close` and `/todo` are their own commands.

- **Haiku** — `/quick-close`, `/todo`, and the workflows `get-started`, `daily-brief`, `rotate-registers`, `workbench-health`. `/todo propose`, `/todo work`, `/todo plan`, `/todo dispatch`, and `/todo reconcile` hand judgment to the sonnet `todo-worker`.
- **Sonnet** — day-to-day default (meetings, tracker hygiene, discovery, OKRs, updates, prototypes, launches). `roadmap-build` is sonnet here.
- **Opus** — `prd-package`, `strategy-refresh`, `experiment-package`. A Deep run of `roadmap-build` dispatches the runner on opus after the usage estimate and a yes. Leave that workflow's `routes.json` entry on sonnet.

A router adds a pause, never removes one. Standard prints one line then dispatches. Deep prints a usage estimate and waits. Say `inline` to run the workflow in the current session. `/model` is a session command for the PM; the agent does not switch its own model mid-response.

## Rule 18 — context used and excluded

Report context used and excluded in one line, only when it is a real choice. Workflows that assemble from many sources (PRD packages, strategy refreshes, launch drift checks) end gathering with one line: what was included ("8 of 23 evidence records, DEC-014/015, code findings") and what was deliberately excluded ("15 low-relevance records, archived drafts"). Skip the line when the source set is obvious (a single meeting file, a named ticket). Do not list empty registers, unconfigured systems, or "nothing was excluded for relevance."

## Rule 19 — log every workflow run

Append one line to `logs/run-log.csv` (timestamp, workflow, approx_duration, success, one-line note). The Stop hook usually writes this; do it in chat only when the row is missing. Never narrate "the run log comes from the Stop hook" or similar plumbing in RESULT.

## Rule 20 — clickable workspace paths

Every existing workspace path is a clickable Markdown link. Any file or folder that exists under the live root — created this turn, an older artifact, a register, or `inbox/documents/` — must appear as `[path](path)` (workspace-relative). Folders keep a trailing slash: `[inbox/documents/](inbox/documents/)`. Never leave a bare or backtick-only path when the target exists. Exceptions: inside fenced code blocks and shell commands; paths that do not exist yet (say so); glob patterns. Hrefs must not use `file://` or absolute `/Users/...` (the client resolves relative paths under the first workspace folder). The live workspace must be that first folder. After creating or updating a file, show the link **once**, then the content (or key sections). Cluster routers paste the `workflow-runner` return **once** and stop — never RESULT, then "Done. Agent processed…", then a second recap. Omit empty negatives. Hooks enforce unlinked existing paths in chat and in written `.md` files.

## Rule 23 — chat answer is not the durable file

A chat answer is not the durable file. Full rule: `.claude/workflows/_fan-out.md` (Rule 23).

## Rule 24 — user-injected context after freeform chat

Facts added mid-chat are durable input. Write them back or ask once. Full rule: `.claude/workflows/_fan-out.md` (Rule 24).

## Context dependencies

A workflow that needs living context declares it under the execution-mode line:

`Context dependencies: soft: <ids> | hard: <ids or none>`

Ids are the `id` column in `reference/context/_manifest.md`. Before gathering, run `python3 scripts/context_health.py --root <live> --ids <those ids>`.

- **Soft gap** (missing, template-empty, or stale): derive what you can and label it. Priorities, when `current-priorities` is empty, may be drafted from open initiatives plus key-result names in `kr-metric-map.md` when that file is filled. Label the draft "derived, not stated priorities" and ask the PM to confirm. Ask two or three questions instead when a derivation would invent a fact. Do not hard-block. Do not present the derivation as something the PM stated.
- **Hard gap:** ask the short batch before the artifact is treated as complete. An unattended run marks that section incomplete and appends `BLOCKED:` (rule 22). Still do not invent.
- The health script exits 0 when the root exists. A gap is a notice, not a failed command.

## Audience and formats

A deliverable keeps one internal source. Published copies carry frontmatter the hooks read:

```
audience: internal|external
formats: [md, html, docx, confluence, slack]
```

`audience` is who the copy is for. `reference/context/audiences.md` (manifest id `audiences`) says which systems that audience can open. `scripts/publish.py` turns a citation into a link only when the matching row lists the system (tracker or jira, wiki or confluence, slack, dashboard). A missing file, or one still marked `status: template`, grants no links: the citation stays plain text. Do not invent audience rows.

Workflow defaults:

| Workflow | audience | formats | External version |
|---|---|---|---|
| weekly-update | internal | md, slack | always, for those formats |
| launch-package (customer-facing docs) | external | docx, confluence | always, for those docs |
| strategy-refresh | internal | md | only when the PM asks |
| explore-brief | internal | md | only when the PM asks |
| roadmap-build | internal | md | only when the PM asks |

`roadmap-build` is `.claude/workflows/roadmap-build.md`. Its Publish step points at the section below. Do not invent a second procedure.

## Publish

Run this after the internal draft is saved. The internal file stays the source of record. Do not overwrite it.

1. Leave register ids, workspace paths, and internal tags in the internal draft. They are how the workspace stays traceable.
2. Run `python3 scripts/publish.py <draft> --root <live>`. The script reads registers and writes a neutralized copy for each requested format under `outputs/external/`, plus a `<draft>.sources.md` sidecar next to the internal draft (id to neutral label).
3. A workspace label becomes a short footnote and a closing Sources line. A meeting row becomes the meeting name and date plus "(meeting notes)". An uploaded file becomes "Uploaded document:" and the file name. A tracker item becomes "Jira" plus the issue key, linked only when this audience has the tracker. A wiki row becomes "Confluence:" plus the page title, linked only when this audience has the wiki. A chat row becomes "Slack" plus the channel and date. A metric becomes "Internal dashboard:" plus the name and as-of date. A workspace path becomes the document title or the file name. A `[hypothesis]` tag becomes inline wording such as "unverified" or "early signal". An id that is not in a register fails the command. `[NEEDS INPUT]` stops publishing until it is resolved: the script writes nothing.
4. Reviewer: in Standard or Deep, dispatch `external-readiness-reviewer` once on the rendered file and the single audience line. It does not see the internal draft, the sidecar, or the registers. Fast: do not dispatch it. Escalate that reviewer to sonnet only when the PM asks.
5. Confluence storage-format XML and Slack mrkdwn are local drafts. Creating a wiki page or sending a chat message is Tier 3: wait for an explicit yes, then re-read the record and verify it. Do not call a wiki create API or a chat send API from Publish.

Customer-facing launch docs use the external formats in the table. Strategy, explore-brief, and roadmap-build stay on internal markdown until the PM asks for an external version; then run steps 2–5 for the formats they name.
