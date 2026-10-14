---
name: context-setup
description: >
  Use when the PM says fill my context, set up my context, context setup,
  or who am I in this workbench. Runs /brief context-setup. Mines existing
  material, the PM's own chat, and auto-memory, then asks only for the gaps.
  Never invent company facts. Never write identity into tracked CLAUDE.md.
---

# context-setup

Plain-language entry for **`/brief context-setup`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/context-setup.md` in full. Prefer the `/brief` router; otherwise run the workflow inline.
3. Draft first. Promote `reference/context/` and `.claude/CLAUDE.local.md` only after the one Tier 2 batch is accepted.

Forbidden: inventing a role, a metric, or a ticket prefix; copying assistant text into durable files; writing personal identity into tracked `CLAUDE.md`.
