# SKILLS.md — where commands become skills (and why you might care)

You asked about skills. Short version: **skills are the newer format of the exact same thing your commands already are**, with one meaningful upgrade.

A workflow is a markdown file at `.claude/workflows/okr-refresh.md` → you run it as `/report okr-refresh` through its router. (Originally each lived in `.claude/commands/` and was typed directly; the routers replaced that.)
A skill is the same content at `.claude/skills/okr-refresh/SKILL.md` → you can still type `/okr-refresh`, **and** Claude can now invoke it on its own when it recognizes the situation calls for it.

That auto-invocation is the practical difference. With commands alone, if someone says "hey, pull this week's numbers," Claude may **improvise**. With skills + `.claude/workflows/_plain-language.md`, it must recognize the Command-menu job and run the tuned workflow — same guardrails, same output format — without the user remembering the slash name.

## Primetime policy (this kit)

1. **Slash commands and routers stay the source of truth** (`routes.json` + `.claude/workflows/*.md`).
2. **Plain language is a first-class product surface.** Future users will not memorize `/capture process-inbox`. Matching phrases must run the workflow, not a lighter improvisation.
3. **Thin skills** under `.claude/skills/<workflow>/SKILL.md` cover high-frequency Command-menu phrases. Their `description:` is the auto-invoke signal; the body points at the workflow file. Do not fork logic into the skill.
4. **`process-inbox`** and **`prototype-build`** are richer skills (intake gate / QA harness). Others stay thin wrappers.
5. When adding a new workflow that users will ask for in everyday language, add a Command-menu row **and** a thin skill in the same change.

## Recommended path for new workflows
Ship as a workflow behind a cluster router first. Add a thin skill as soon as you notice (or expect) plain-language asks — do not wait for repeated improvisation failures in the field.

## Converting a full workflow into a skill-only home (rare)
```
mkdir -p .claude/skills/okr-refresh
mv .claude/workflows/okr-refresh.md .claude/skills/okr-refresh/SKILL.md
# update routes.json path; keep cluster router
```
Only do this when the skill must bundle extra files (see prototype-build). Otherwise keep the workflow file and a thin skill wrapper.

## Already special
- **`prototype-build`** — full skill with QA harness and repo scaffolding.
- **`process-inbox`** — skill emphasizes Downloads intake; workflow remains the step source of truth.
- **Thin skills** — get-started, meeting-closeout, daily-brief, return-brief, meeting-prep, jira-reconcile, ripple-check, context-reconcile, roadmap-update, discovery, competitive-scan, research-plan, research-package, learn-product-flow, code-dive, weekly-update, okr-refresh, strategy-refresh, prd-package, experiment-package, experiment-analyze, launch-package, workbench-health, monthly-review.
