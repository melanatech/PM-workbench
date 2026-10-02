---
description: Make systems agree - reconcile Jira, trace what a change affects, apply a roadmap change everywhere, or archive old register rows.
model: haiku
argument-hint: [jira-reconcile|ripple-check|roadmap-update|rotate-registers] [what changed]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `sync`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `jira-reconcile` | Diff the Jira board against reality and propose a change set |
| `ripple-check` | Something changed (a decision, a Jira update, news): trace what else it touches |
| `roadmap-update` | A roadmap change that must land on every surface it lives on |
| `rotate-registers` | Archive old register rows so active files stay small |

## Choosing

- "Check the board", "is anything stale": `jira-reconcile`.
- "What else does this affect", or a decision that did not go through a normal command: `ripple-check`.
- "The roadmap changed", features moved or added: `roadmap-update`.
- "The registers are getting huge": `rotate-registers`. Warn first that the register hook blocks writes that lose rows (BACKLOG item), so rotation of a current-state register may be refused.
