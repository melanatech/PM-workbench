# Router protocol — how /capture, /brief, /sync, /discover, /build and /report run a workflow

This file is read by the six cluster commands. It is not a command. The workflow files beside it (`.claude/workflows/<name>.md`) are the original command texts, moved unchanged; `routes.json` lists which cluster owns which workflow and which model it runs on. `prototype-build` is the one workflow that lives as a skill (`.claude/skills/prototype-build/SKILL.md`).

A router has no logic of its own. It picks a workflow, runs the safety steps below, hands the work to the `workflow-runner` subagent on the right model, and relays what comes back. Every gate, readiness check, approval tier and model choice stays inside the workflow text and in CLAUDE.md; the router can add a pause but never remove one.

## 0. Pause switch

If `state/PAUSE` exists, stop before doing anything: say "Paused: `state/PAUSE` exists. Delete that file to resume." and append nothing to any register. This applies to every run, attended or not, so a pause really means nothing moves. A run started by a schedule also logs `BLOCKED: paused` to `logs/run-log.csv`.

## 1. Pick the workflow

1. Read `.claude/workflows/routes.json` and take the entry for your cluster.
2. If the first word of the input (leading `/` ignored) is one of the cluster's workflow names, that is the workflow and the rest of the input is its arguments. An old command name typed as a slash command inside a request ("run /prd-package on bulk export") means the same thing.
3. Otherwise use the selection rules in the router file. If more than one workflow fits, or none does, ask one short question that names the options. Never guess between workflows that write different things.
4. A workflow name that belongs to another cluster: tell me which command owns it (`/build prd-package`, say) and stop.
5. If the input contains the word `inline`, run in inline mode (step 4) instead of dispatching.

## 2. Before running

- Read the workflow file's first line for its execution mode (Fast, Standard, Deep) and its required-input rules.
- **Deep:** print the usage estimate the workflow asks for and wait for a yes. **Standard:** print one line, "About to run <workflow> in Standard mode on <model>", and continue unless I stop it. **Fast:** run.
- If the workflow's own required-input rule says to ask me something before starting (a feature's problem statement, a date range, a file), ask it now, in one batch. Do not dispatch with the answers missing.
- Write the marker for the run log: `printf '%s' '<cluster>:<workflow>' > state/.run-workflow` (create `state/` if absent). The Stop hook reads it and then removes it.

## 3. Dispatch

Call the Agent tool with `subagent_type: workflow-runner` and `model:` set to the model for that workflow in `routes.json`. The prompt must contain: the workflow name and its file path, the user's arguments verbatim, today's date, and any answers I have already given. Nothing else; the runner reads what it needs.

The runner returns exactly one of:

- **RESULT** — the work is done. It includes the full text of every artifact written or changed, the register rows it appended or edited, the context-used-and-excluded line, and the run-log note.
- **PROPOSALS** — Tier 2 or Tier 3 items waiting for approval (grouped diffs, Jira changes, anything that changes scope, owner, date or priority, anything to be sent).
- **QUESTIONS** — what it needs from me (CLAUDE.md rule 12), batched, with what it did finish.

Relay it as follows. Show RESULT text in full (CLAUDE.md rule 20), not a summary of it. Present PROPOSALS as the runner wrote them, one grouped list; ask me to approve, change or drop each. Ask QUESTIONS in one batch.

When I answer, dispatch the runner again with: the same workflow, the original arguments, the runner's previous output, and my answers. The runner continues from its run manifest (`logs/run-manifest-*.md`) and does not redo finished steps. Approvals I give are carried out by the runner on the second dispatch, then it re-reads the record and verifies it (CLAUDE.md rule 1). After two rounds on the same workflow with questions still open, stop and tell me plainly what is blocking.

**Unattended runs** (started by a schedule, or I said I am away): there is nobody to answer. Do not wait and do not guess. Have the runner finish what it can, write what it finished to `outputs/` with the gaps labelled, append `BLOCKED: <what it needed>` to `logs/run-log.csv`, and stop (CLAUDE.md rule 22).

## 4. Inline mode (the fallback)

When I say `inline`, or when the runner cannot be dispatched: read the workflow file and carry it out yourself, in this session, with no runner. Say once at the top which model this session is running on and which one the workflow normally uses, so the cost is visible; if the workflow normally runs on opus and this session is not, offer `/model opus` before starting a Deep or Standard run. Everything else is the same as above.

## 5. Always

- The router never writes to a register, an output or an external system itself; the runner or the inline workflow does, under the same hooks.
- Old workflow names keep working as the first argument, so existing notes, schedules and habits still work with the cluster name in front.
- If `routes.json` or a workflow file is missing or unreadable, say which and stop. Do not reconstruct a workflow from memory.
- End with one line naming the workflow that ran and the model it ran on.
