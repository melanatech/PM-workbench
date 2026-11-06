# IDE parity

Claude Code stays the primary editor. Codex (CLI and the VS Code extension) is the first parity target. Cursor keeps working. VS Code Copilot has a light instruction file.

| IDE | Always-on rules | Commands | Skills | Subagents | Hooks | MCP |
|---|---|---|---|---|---|---|
| Claude Code | `CLAUDE.md` | `.claude/commands/` | `.claude/skills/` | `.claude/agents/` | not shipped in the kit | `.mcp.json` in the live workspace |
| Cursor | `.cursor/rules/workbench.mdc` | `.cursor/commands/` points at the Claude commands | same skill files if the editor loads them | Cursor does not run `workflow-runner` | `.cursor/hooks.json` | `.cursor/mcp.json.example` only. Live config stays out of the kit. |
| Codex | `AGENTS.md` | `.codex/prompts/` | `.agents/skills` when present | `.codex/agents/` | `.codex/hooks.json.example` plus the Python hooks | `.codex/config.toml.example` |
| VS Code Copilot | `.github/copilot-instructions.md` | `.github/prompts/` | not loaded as skills | none | none. The instruction file states the gates. It does not block a write. | none |

## File check

`python3 scripts/check_ide_parity.py` from the kit root checks that every router has a twin and that the hook files exist.

## Fresh-chat acceptance

Not run inside this session. A fresh chat in each IDE still has to show that the rules load, a slash command routes, a shared artifact without a ledger is blocked, and a ticket write asks for approval.

| IDE | Rules load | Slash command routes | Ledger block | Write asks for approval |
|---|---|---|---|---|
| Claude Code | [NEEDS INPUT] fresh chat | [NEEDS INPUT] | [NEEDS INPUT] | [NEEDS INPUT] |
| Cursor | [NEEDS INPUT] fresh chat | [NEEDS INPUT] | live hooks exist; not re-tested this pass | live `beforeMCPExecution` exists; not re-tested this pass |
| Codex | [NEEDS INPUT] fresh chat | [NEEDS INPUT] | hook file is in the kit; live `hooks.json` still points at the live copies | [NEEDS INPUT] |
| VS Code Copilot | [NEEDS INPUT] fresh chat | prompt files exist; the editor does not enforce them | fail: no hook | fail: no hook |

Known gap: Cursor Agent does not run `workflow-runner`. VS Code Copilot cannot block a write. The instruction file tells it to ask.
