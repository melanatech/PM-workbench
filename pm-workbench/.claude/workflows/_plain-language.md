# Plain-language routing — primetime rule

Applies to every session (interactive or scheduled), every user of this kit —
not only people who remember slash commands.

## The rule

When the user's request matches a row in CLAUDE.md **Command menu** (or the
Choosing lists on `/capture`, `/brief`, `/sync`, `/discover`, `/build`,
`/report`), **run that cluster/workflow**. Do not invent a lighter ad-hoc path
(peek a folder, skim a file, "quick check") that skips the workflow's Step 0,
intake gates, fan-out, or subagent dispatches.

- **Match → run.** Do not ask "did you mean `/capture process-inbox`?" when the
  phrasing clearly matches. Confirm only when two workflows fit equally well.
- **Ambiguous → one short question**, then run. Do not improvise while waiting.
- **No menu match →** answer from registers/`outputs/`/`learning/` if it is a
  lookup; otherwise ask which workflow or what outcome they want.

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
- Skipping Deep usage estimate / required-input gates because the user used
  casual wording
- Treating "context constraints" as a reason to skip the matched workflow
  (dispatch a heavy-read subagent instead — CLAUDE.md)

Routers: after choosing a workflow, dispatch per `_protocol.md` immediately.
