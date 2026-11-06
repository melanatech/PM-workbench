# Session memory (Plan E Part 2)

Keeps a short register per Claude Code session (goal, where it stands, decisions, constraints, corrections,
don't-retry, open questions) so a decision survives compaction and a new chat can pick up earlier work.
Standard library only. Every hook fails open.

## Scope and boundaries

- **Claude Code only.** Cursor Agent also runs user-level `~/.claude/settings.json` hooks. Every script here
  exits 0 on a Cursor payload (`conversation_id`, `cursor_version`, `workspace_roots`, `generation_id`) until
  the PM's probe test settles whether it should run there.
- **Working context, not durable memory.** Session registers hold per-session working context. A project's
  own durable memory (in a workbench: `reference/context/pm-brain.md`, governed by its CLAUDE.md rule) stays
  the record for durable PM-stated facts. Session memory never writes project files; the restore preface and
  the CLAUDE.md block tell Claude to save durable corrections the project's way.
- **Precedence.** Within a session, the newer statement wins. Between a session entry and the project's
  durable memory file, the newer of the two wins, and Claude brings the file up to date by the project's rule.
- **Stale-session guard.** A prompt in a chat idle at least 60 minutes, and holding at least 80k tokens
  above a new chat's starting context, is not sent (exit 2). Where it stands is saved first. `!force` at
  the start sends it anyway. The reading reminder does not block, and it is off once the partner skill is
  used in a session: judgment work reads its sources in full in the main conversation.
- **Cost cap.** Headless model calls (`claude -p --model haiku`) are capped per day across all projects:
  `SESSION_MEMORY_DAILY_CALLS` (default 200). Over the cap, captures are skipped and logged. A question-only
  call runs with no tools, no MCP, no skills, and no project context.

## Pieces

| File | Event | What it does |
|---|---|---|
| `hooks/keeper.py` | Stop | Starts a detached worker that captures the latest exchange; audits every 10 captures; consolidates past ~1,500 words |
| `hooks/restore.py` | SessionStart | `compact`: prints the preface plus active entries. `startup`: offers a waiting weekly review once |
| `hooks/prompt.py` | UserPromptSubmit | Stale-session guard (idle ≥ 60 min and ≥ 80k tokens blocks; `!force` sends it), related-work detector on a session's first prompt, the one-line reading reminder, reading-tally reset |
| `hooks/reading.py` | PostToolUse (reads, Skill) | Reading-budget notice past 25k tokens or 4 sources in one turn |
| `agents/session-reader.md` | — | Sonnet reader that returns a cited answer under 800 words |
| `commands/pickup.md`, `pickup.py` | — | `/pickup <goal words>` manual fallback |
| `weekly_review.py` | — | Counts from the logs; `--write` saves a report that the next session start offers |
| `haiku-instructions.md` | — | What the headless model may record. Changes need the user's approval |

Data: `~/.claude/session-memory/<cwd-slug>/<session-id>.jsonl`, `index.json`, `log.jsonl` (override with
`SESSION_MEMORY_HOME`). Supersession follows the same rule as `pm-workbench/scripts/register_view.py`; a test
checks both agree.

## Install, check, remove

```
python3 session-memory/install.py --dry-run
python3 session-memory/install.py
python3 session-memory/install.py --uninstall
```

Not built yet, by design: scheduling the weekly review and the audit job, and
`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=70`. Both wait until Phase 2 is proven in the Claude Code panel and terminal.
