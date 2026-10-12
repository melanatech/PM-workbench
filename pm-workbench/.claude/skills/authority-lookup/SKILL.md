---
name: authority-lookup
description: >
  Use for freeform factual lookups: what did I commit, what's due, what did we decide,
  initiative status, metric value, is the inbox empty, what does the PRD say, board state.
  Enforce CLAUDE.md rule 25 authority-first lookups — read the authoritative surface first,
  then secondary sources. Never answer from a single find hit or transcript as complete.
---

# authority-lookup

Freeform lookup — **not** a slash workflow. Enforce CLAUDE.md **Authority-first lookups** / rule 25.

1. Classify the question type (commitment, todo, decision, initiative, risk, metric, PRD, inbox, Jira, priorities).
2. Read the **authoritative surface first** (table in CLAUDE.md). Operational matches (process-inbox, jira-reconcile, etc.) still run the workflow — do not improvise a lighter peek.
3. Use digests / archive / raw files only to fill gaps or quote wording.
4. Reply with the answer **plus** a one-line coverage note when the source set is non-obvious.

**Forbidden:** leading with `find` on `archive/`; one meeting file as "the" answer; waiting for the PM to push back before checking the index.

**Worked example:** promises/due → `registers/commitments.csv` before transcripts (see CLAUDE.md).
