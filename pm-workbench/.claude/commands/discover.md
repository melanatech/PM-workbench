---
description: Learn from users, the market or the code - discovery, research plans and test packages, competitive scans, how a product flow works, code dives.
model: haiku
argument-hint: [discovery|research-plan|research-package|competitive-scan|learn-product-flow|code-dive] [question or topic]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `discover`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `discovery` | Ask what the evidence says, add new inputs, see what changed, map opportunities |
| `research-plan` | Screening criteria, outreach approach and a guide for a feature or question (never names of people) |
| `research-package` | The full package for a prototype or concept test |
| `competitive-scan` | Dated captures diffed against the last run |
| `learn-product-flow` | Understand a flow end to end: UI walkthrough, doc comparison, metric map |
| `code-dive` | Understand a feature at code level from read-only clones |

## Choosing

- Evidence, themes, "what are users saying", pasted feedback: `discovery`.
- "Who should we talk to", "plan research for": `research-plan`. "Set up a test for": `research-package`.
- Competitors: `competitive-scan`.
- "How does X work" in the product: `learn-product-flow`; in the code: `code-dive`. Often both, in that order; run one and offer the other.
