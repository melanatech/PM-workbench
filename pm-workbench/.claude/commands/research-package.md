---
description: Full research package for a prototype or concept test
argument-hint: [what's being tested, with whom]
execution_mode: standard   # fast=0 reviewers, standard=1-2, deep=full panel (see CLAUDE.md)
---

Research package for: $ARGUMENTS

**Before designing anything, dispatch `internal-docs-reader`** to check `reference/user-research/` and SharePoint/Confluence for prior research on this same question — no point re-running a study that already exists, and prior findings sharpen the screener and moderator guide. Then → `outputs/research/[name]/`:

Objective; participant criteria + screener; moderator guide (tasks in order, what each is meant to learn, follow-up probes); survey variant for scale; consent placeholder; observation sheet; analysis framework; **decision rules written before any session runs**.

After sessions: drop transcripts/notes in `inbox/research/`, rerun with the same name. Synthesis: findings by task, success/failure rates, severity, segment differences, repeated misunderstandings, requested-solution vs. underlying-problem, **evidence contradicting our hypothesis** (look for it actively), prototype changes, recommended decision. Preserve participants' actual wording. New evidence → `registers/evidence.csv`; shareable findings report included.
