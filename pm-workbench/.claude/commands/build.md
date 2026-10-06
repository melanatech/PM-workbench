---
description: Make the thing - a PRD package, a prototype, a PRD-prototype check, an experiment design or its analysis, a launch package. The initiative's stage decides which when you do not say.
model: haiku
argument-hint: [prd-package|prototype-build|prd-prototype-sync|experiment-package|experiment-analyze|launch-package] [feature or problem]
---

Input: $ARGUMENTS

Read `.claude/workflows/_protocol.md` and follow it with CLUSTER = `build`. Do not run anything before you have read it.

## What this command covers

| Workflow | Use it for |
|---|---|
| `prd-package` | Grounded context, readiness gate, draft, stakeholder pre-review (opus) |
| `prototype-build` | A runnable prototype from the Feature Contract, with real browser QA (the skill at `.claude/skills/prototype-build/SKILL.md`) |
| `prd-prototype-sync` | Check a PRD and its prototype against each other |
| `experiment-package` | Experiment design with the adversarial review gate (opus) |
| `experiment-analyze` | Results against the pre-registered design |
| `launch-package` | Drift report first, then all audience docs |

## Choosing

**Plain language:** follow `.claude/workflows/_plain-language.md` — match → run; never improvise a lighter path.

- A named workflow wins. Otherwise look up the feature in `registers/initiatives.csv`:
  - no row, or stage `discovery` / `prd`, and the words "spec", "PRD", "write up": `prd-package`
  - words "prototype", "mock", "build", or a PRD exists with no prototype and I asked to see it: `prototype-build`
  - both PRD and prototype exist and I mention a change, a comment or "still match": `prd-prototype-sync`
  - "test", "experiment", "A/B": `experiment-package`; "results" with an export: `experiment-analyze`
  - "launch", "release notes", "get this ready": `launch-package`
- If the stage and my words disagree, or the feature is only a name, ask one short question. A feature name alone is not enough input for `prd-package`; its required-input rule applies.
- `prototype-build` is a skill, not a workflow file: the runner reads its SKILL.md and follows it.
