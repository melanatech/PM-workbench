# Router protocol — how /capture, /brief, /sync, /discover, /build and /report run a workflow

This file is read by the six cluster commands. It is not a command. The workflow files beside it (`.claude/workflows/<name>.md`) are the original command texts, moved unchanged; `routes.json` lists which cluster owns which workflow and which model it runs on. `prototype-build` is the one workflow that lives as a skill (`.claude/skills/prototype-build/SKILL.md`).

A router has no logic of its own. It picks a workflow, runs the safety steps below, hands the work to the `workflow-runner` subagent on the right model, and relays what comes back. Every gate, readiness check, approval tier and model choice stays inside the workflow text and in CLAUDE.md; the router can add a pause but never remove one.

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
- **Deep:** print the usage estimate the workflow asks for and wait for a yes. **Standard:** print exactly one line — `Running <workflow> (Standard / <model>)…` — then **dispatch immediately** in the same turn (that line means work is starting, not waiting). **Fast:** dispatch with no preamble.
- If the workflow's own required-input rule says to ask me something before starting (a feature's problem statement, a date range, a file), ask it now, in one batch. Do not dispatch with the answers missing.
- Write the marker for the run log: `printf '%s' '<cluster>:<workflow>' > state/.run-workflow` (create `state/` if absent). The Stop hook reads it and then removes it. Do not announce that you wrote the marker.
- **Never stop on "ready."** Do not end a turn with "Ready to reprocess," "Ready when you are," "I can run process-inbox next," "Clean — ready," or any equivalent status line that implies the next step is obvious but not started. If the next action is clear (inbox is staged, I said reprocess/reset/go, prep finished), **dispatch or run it in this same turn**. The only allowed stops before work are: Deep yes/no, a required-input question, `state/PAUSE`, or a real ambiguity between workflows.

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
- **One copy of the artifact.** Show the written file **once**: a Markdown link with a **workspace-relative** href (`[outputs/daily/2026-10-05-topic.md](outputs/daily/2026-10-05-topic.md)`), then the content (or key sections). Do **not** use `file://` or bare absolute `/Users/...` paths — the Claude Code extension does not make those clickable (only relative paths under the first workspace folder work). RESULT does not reprint it, and the router does not add "here's what happened" or "Done. Agent processed…".
- **No RESULT + Done pair.** A successful run is one message. If you catch yourself about to write a confirmation under the runner paste, delete it.
- **Re-runs.** If the meeting or input was already closed out, say that in a few lines, name the existing IDs, and go to PROPOSALS. Do not recap every empty checklist item.
