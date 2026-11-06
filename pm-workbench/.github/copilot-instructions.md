# Workbench instructions for VS Code Copilot

Follow CLAUDE.md, .claude/workflows/_operator-rules.md, .claude/workflows/_protocol.md, and AGENTS.md.

Edit an existing artifact in place. Shared artifacts that carry numbers need a ledger and scripts/check_number_consistency.py. HTML must pass scripts/check_design_preserved.py.

Do not write to a ticket tracker, chat, or wiki without approval.

Slash-style jobs live in .github/prompts/. Each one points at the matching file in .claude/commands/.

A question is not blocked until a source-scout record exists.
