---
description: Pre-PRD product check-in brief - assemble initiative context, frame the problem, then options
argument-hint: [INIT-nnn | COM-nnn | feature or problem]
---

Execution mode: **standard** (fast=0 reviewers, standard=bounded gather, deep not used here — see CLAUDE.md). Override inline if I say so.

Explore / check-in brief for: $ARGUMENTS

This is **not** a PRD package. No readiness score-as-PRD-gate, Feature Contract, stakeholder reviewer panel, or opus path. When the PM later wants a full PRD, they run `/build prd-package` (same gatherer).

**Hard rules**
- **Assemble before options.** Never lead with a single UI pattern or a solution sketch before the problem frame.
- **Decided vs open from the gatherer** — not from the user's last restatement alone.
- **Thought-partner:** challenge problem completeness; don't parrot the last user message into "the" problem.
- Do not invent facts to fill brief sections; use `[NEEDS INPUT: …]` or wait at the gate.

**Step 0 — Resolve.** Parse INIT-/COM-/topic from `$ARGUMENTS`. If the ask is only a vague "brief" with no initiative or commitment, ask once which INIT-/COM-/feature. Resolve COM → related INIT via `registers/commitments.csv` and `registers/initiatives.csv` text/links.

**Step 1 — Gather.** Dispatch `prd-context-gatherer` for this feature/INIT/COM. In parallel, dispatch `internal-docs-reader` when wiki, user research, or shared-drive docs are likely relevant. **Do not draft options or the brief body before the gatherer returns** (and the docs reader, if dispatched).

**Step 2 — Frame (show before concepts).** From the grounding brief, write the problem frame in the reply (and later into the draft):
- Jobs-to-be-done hypotheses
- In / out of scope
- Non-goals (already-decided sibling work from decided-vs-open)
- Evidence strength table (what we know / don't, with strength)

Show this frame **before** any concepts.

**Step 3 — Gate.** If gatherer gaps are material (could change problem, audience, or scope) or the PM is newly owning the area with thin context: return a batched set of QUESTIONS and **wait**. Do not invent answers. If gaps are low-impact, mark `[NEEDS INPUT: …]` in the draft and continue.

**Step 4 — Options.** After the frame (and after any gate answers): 2–4 concepts. For each: what job it serves, density/coverage fit if relevant, risks, what evidence would validate it. Competitive stress-test via `scripts/web_search.py` + WebFetch on **help docs and launch posts** — not fabricated in-app product tours. Mark unverified in-app claims `[external::training]`.

**Step 5 — Write.** Write `drafts/[slug]-product-brief.md` (slug from INIT name or topic). Outline:

1. Status line (draft, meeting/check-in if known, surfaces/scope if known)
2. Summary + explicit ask for the meeting
3. Starting point / what exists (from workspace)
4. Evidence table (what we know / don't — with strength)
5. What decided work leaves unsolved (or open problem parts)
6. Bet or principles (short)
7. Concepts (2–4) with tradeoffs
8. What to measure / learn first (if evidence supports; else `[NEEDS INPUT]`)
9. Open questions

**Step 6 — Close.** Lightly update the INIT row notes with path to the draft and date (keep id/order). Propose a TODO only if an open action is clear. Tell the PM the next step when ready is `/build prd-package` — **do not run it** from this workflow.

End gathering with one line: context used / excluded (rule 18) when the source set was a real choice.
