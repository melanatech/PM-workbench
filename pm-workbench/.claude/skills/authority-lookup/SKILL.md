---
name: authority-lookup
description: >
  Use for freeform factual lookups: what did I commit, what's due, what did we decide,
  initiative status, metric value, is the inbox empty, what does the PRD say, board state,
  what instrumentation exists, what did we already conclude, how did you check / verification.
  Enforce CLAUDE.md rule 25–26 authority-first and cache-first lookups — read the authoritative
  surface first, then secondary sources. Never answer from a single find hit, transcript, or draft.
---

# authority-lookup

Freeform lookup — **not** a slash workflow. Enforce CLAUDE.md **Authority-first lookups** / rules 25–26.

1. Classify the question type (commitment, todo, decision, initiative, risk, metric, PRD, inbox, Jira, priorities, **prior analysis / instrumentation**, **verification**).
2. Read the **authoritative surface first** (table in CLAUDE.md).
   - Prior analysis / "what do we already know" / events / instrumentation → run `python3 scripts/context_preflight.py --root <live> --topic "…"` (or read a fresh marker). Cite hits + `primary_sources`.
   - Verification / "how did you check?" / baseline "today" → SOURCE-POLICY claim-type ladder; chain to capture or `repos/…@commit` / locale file. Never stop at "the brief says."
3. Operational matches (process-inbox, jira-reconcile, explore-brief, etc.) still run the workflow — do not improvise a lighter peek.
4. Use digests / archive / raw files only to fill gaps or quote wording.
5. Reply with the answer **plus** a one-line coverage note when the source set is non-obvious.

**Forbidden:** leading with `find` on `archive/`; one meeting file as "the" answer; citing only `drafts/` or `prototypes/` as evidence for product facts; waiting for the PM to push back before checking the index.

**Worked example:** promises/due → `registers/commitments.csv` before transcripts (see CLAUDE.md).
**Worked example:** instrumentation → `context_preflight` before `repos/`.
