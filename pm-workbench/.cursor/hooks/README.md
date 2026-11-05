# Workbench Cursor project hooks

These hooks mechanically enforce workbench rules on shared artifacts and external writes. They load from `.cursor/hooks.json` when the workspace is trusted.

## What each hook enforces

| Event | Script | Behavior |
|---|---|---|
| `afterFileEdit` | `after_file_edit.py` | After Write/StrReplace on a **shared artifact**, runs HTML design check and number-consistency check. On any other `outputs/**/*.md` (see `claim_check` in `shared-artifacts.json`), runs the claim check: a missing-PRD/ticket/epic claim, "assigned to <not the PM>", or a wrong PM name needs a `| Claim | Source |` table. Records pass/fail in `state/hooks/gate-status.json` under the editing conversation (a worker's own id when a worker edits). |
| `stop` | `stop_gate.py` | Sends the agent back (`followup_message`) when a file recorded for this conversation is failing or changed since its last pass, when a worker's failing file or unsourced claim was filed here by `subagentStop`, or when an earlier reply here was flagged by `afterAgentResponse`. `loop_limit` is 3; on the last loop the agent must report the failure to the PM plainly. Does not fire on turns started by a subagent-completion notice. |
| `preToolUse` | `dispatch_inject.py` | Prepends the dispatch block (the PM's identity from `pm-identity.json`, workflow-read instruction, AGENTS.md dispatch header, number gate, claim-table rule) to a Task prompt via `updated_input`. **Does not fire for Tasks dispatched through `CallDynamicTool`** (verified 2026-11-02), so coordinators reference `.cursor/hooks/dispatch-block.md` instead (rule in `.cursor/rules/workbench.mdc`). Regenerate that file with `.cursor/hooks/dispatch_inject.py --write-block` after editing `pm-identity.json`. |
| `subagentStart` | `subagent_start.py` | Log-only. Records whether a shared-edit Task carried the header + number gate and whether the dispatch block was referenced. Always allows. |
| `subagentStop` | `subagent_claims_gate.py` | Reads the worker's final message (payload `summary`, or the worker transcript found from `child_conversation_id`), checks absence/person claims, and files any unsourced claim plus the worker's failing files under `parent_conversation_id` so the coordinator's next stop blocks. Also returns `followup_message`, but the IDE Task handler ignores it (verified 2026-11-02). |
| `afterAgentResponse` | `relay_claims_check.py` | Observe-only. Records a reply with unsourced absence/person claims under its conversation; the next stop that fires there sends the agent back. |
| `beforeMCPExecution` | `before_mcp.py` | Returns `permission: ask` for Atlassian write tools and Slack write tools so the PM always gets an approval card. Read-only Atlassian calls pass through. |

`failClosed: true` is set on stop and beforeMCPExecution. Kit tests: `python3 -m unittest tests.test_cursor_hooks` (from the kit folder).

## PM identity (local only)

Copy `pm-identity.example.json` to `pm-identity.json` in this folder and fill in the PM's name, email, and (optional) tracker account id, ideally from the tracker's current-user lookup. `username_examples` lists usernames or account names that must never be read as a person's name. Both `pm-identity.json` and the rendered `dispatch-block.md` are gitignored: they name a person. With no identity file, the block says `[NEEDS INPUT: PM name/email]` and the wrong-PM check is off. After editing it, run `.cursor/hooks/dispatch_inject.py --write-block`.

## What is proven on the IDE path

- Verified live: the `outputs/**/*.md` claim check; subagentStop filing a worker's unsourced claims and failing files under `parent_conversation_id`, then the coordinator's next stop sending it back; subagentStart log-only.
- Cursor drops a subagentStop `followup_message` on the IDE Task path, and `stop` does not fire on turns started by a subagent-completion notice. The send-back therefore happens on the coordinator's next PM-started turn.
- `afterAgentResponse` recording is unproven live. `preToolUse` injection does not fire for Tasks dispatched through `CallDynamicTool`; it is kept because it is harmless and helps where Cursor exposes Task directly.

## Shared artifact patterns

Edit `.cursor/hooks/shared-artifacts.json` to change what counts as shareable under `outputs/`.

Included by default:

- `*.html`
- `*slack-draft*.md`
- anything under a `*jira-drafts*` folder
- `*confluence*.md`
- paths matching `*readout*` or `*deck*`

Excluded by default (internal): number ledgers, supplements, method notes, question plans, other `*-plan.md`, underscore-prefixed scratch, py/csv/json.

### Number ledger convention

Next to the artifact: `<artifact-stem>-number-ledger.md`.

Example: `outputs/strategy/2026-10-26/interactive-reports-first-readout.html` pairs with `interactive-reports-first-readout-number-ledger.md`.

Optional overrides live in `ledger_by_artifact` in the config (map artifact path → ledger path, both relative to the project root). Share packs that reuse one ledger (HTML + Slack draft) must list each share path there.

**Gate sources:** the ledger’s `## Gate sources` section lists saved-result CSV/MD paths. `check_number_consistency.py --ledger <ledger> <artifact>` loads those automatically — same invocation for hooks and manual runs. Extra CLI `--source` flags still append; they are not required when the section is complete.

### Subagent detector (log-only since 2026-11-02)

A Task is treated as a shared edit when the prompt has a write verb (`edit`, `update`, `rewrite`, …) **and** either an `outputs/` path or a shared name (`.html`, `slack-draft`, jira draft, confluence, readout, deck). Negated phrases like `do not edit` are stripped before the verb scan. `subagent_start.py` logs `would_have_denied` when such a prompt lacks `Keep its design, CSS, markup structure` or a number-gate phrase. It no longer denies: the deny did not stop workers, Cursor skips subagentStart on resumed workers, and blocking delegation is not wanted.

## Logs and status

- Decision log (append-only): `state/hooks/hook-log.jsonl`
- Per-file gate results: `state/hooks/gate-status.json`
- Design baselines (last version that passed the design check): `state/hooks/design-baselines/` (mirrors the artifact path under the project root, e.g. `state/hooks/design-baselines/outputs/strategy/.../file.html`)

Both under `state/` (local runtime; not required in git).

## Design baselines (no-git workbench)

The live workspace is often not a git repo, so `--git HEAD` cannot be the only prior. The afterFileEdit hook:

1. Prefers `check_design_preserved.py <html> --git HEAD` when that blob exists in git.
2. Otherwise compares against the baseline under `state/hooks/design-baselines/`.
3. On **pass**: records `design=pass` and updates the baseline to the current file.
4. On **fail**: records `design=fail` and leaves the baseline unchanged. The stop gate blocks (same as a number fail).
5. **No baseline and no git** (brand-new shared HTML): records `design=new`, seeds the baseline from the current file, and treats that as ok for the design dimension. Later edits must preserve that baseline.
6. **`design=skipped` is a FAIL** for shared HTML (it used to count as ok when git was missing — that hole is closed).

### Accepting an approved redesign

Only the PM’s explicit ask justifies advancing a baseline after a deliberate redesign:

```bash
# Run from the live workspace root (scripts/ may be a kit symlink).
python3 scripts/accept_design_baseline.py <file.html>
# or: python3 scripts/accept_design_baseline.py --root <live-workspace> <file.html>
```

That copies the current file over the baseline and appends an acceptance row to `state/hooks/hook-log.jsonl`. Agents must not run it to clear a failing gate after an unapproved design change.

## Checks invoked

```bash
python3 scripts/check_design_preserved.py <file.html> --git HEAD
# or (hooks fall back to this when git has no blob):
python3 scripts/check_design_preserved.py <file.html> --before state/hooks/design-baselines/<rel-path>

# Same command hooks use: ledger ## Gate sources supplies saved results.
python3 scripts/check_number_consistency.py --ledger <ledger.md> <artifact> [...]
# Optional: --source <saved-result> (repeatable) appends beyond Gate sources.

# Deliberate redesign acceptance (the PM only):
python3 scripts/accept_design_baseline.py <file.html>
```

If `scripts/check_number_consistency.py` is missing, the number gate fails closed with `number check not installed`.

## Temporarily disable

Edit `.cursor/hooks.json`: remove or comment out the event entry you want off, or rename `hooks.json` so Cursor stops loading project hooks. Cursor reloads on save; restart Cursor if a change does not appear.

Do not leave gates disabled for shared work without the PM knowing.

## Requirements

- `python3` on PATH (stdlib only; no `jq` required)
- Project trusted so Cursor loads project hooks
