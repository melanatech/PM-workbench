---
description: Pre-PRD product check-in brief - assemble initiative context, frame the problem, then options
argument-hint: [INIT-nnn | COM-nnn | feature or problem]
---

Execution mode: **standard** (fast=0 reviewers, standard=bounded gather, deep not used here — see CLAUDE.md). Override inline if I say so.

Explore / check-in brief for: $ARGUMENTS

This is **not** a PRD package. No readiness score-as-PRD-gate, Feature Contract, stakeholder reviewer panel, or opus path. When the PM later wants a full PRD, they run `/build prd-package` (same gatherer).

**Hard rules**
- **Assemble before options.** Never lead with a single UI pattern or a solution sketch before the problem frame.
- **Workspace before repos.** Technical claims (instrumentation, how code works, what exists in product) must cite the gatherer's **Prior workspace analysis** section (paths + dates). Forbidden: "from the clone…" as the only source when `outputs/daily/` or `learning/` already analyzed the same topic. If you must re-check code, say why the prior analysis is insufficient or stale.
- **Decided vs open from the gatherer** — not from the user's last restatement alone.
- **Thought-partner:** challenge problem completeness; don't parrot the last user message into "the" problem.
- Do not invent facts to fill brief sections; use `[NEEDS INPUT: …]` or wait at the gate.

**Step 0 — Resolve + preflight.** Parse INIT-/COM-/topic from `$ARGUMENTS`. If the ask is only a vague "brief" with no initiative or commitment, ask once which INIT-/COM-/feature. Resolve COM → related INIT via `registers/commitments.csv` and `registers/initiatives.csv` text/links. Then run:
`python3 scripts/context_preflight.py --root <live> --topic "$ARGUMENTS"`
(use `--verify` if the PM asked to re-check). Read `state/.context-preflight.json`. One RESULT line: recommendation + hit count. Do not continue until this runs.

**Step 1 — Gather.** Dispatch `prd-context-gatherer` with the preflight marker (it consumes `.context-preflight.json` for Prior workspace analysis — do not replace the script with ad-hoc Grep). In parallel, dispatch `internal-docs-reader` when wiki, user research, or shared-drive docs are likely relevant. **Do not draft options or the brief body before the gatherer returns** (and the docs reader, if dispatched). On `reuse_and_refresh`, spot-check the newer surface before locking the frame.

**Step 1.5 — External grounding (web).** Follow `.claude/workflows/_web-search.md`. Run `python3 scripts/web_search.py` (not native WebSearch-only) and WebFetch for **problems, market/category, users, and solutions** relevant to the topic — unless the PM scoped fewer axes. Prefer help docs, launch posts, and public research over invented in-app tours. Write `state/web-search/YYYY-MM-DD-<slug>.md` when findings are consequential; index with `--kind web-search`. Reuse a same-day capture for the same slug when queries would not change. Mark unverified claims `[external::training]`. Workspace evidence still outranks web hits on conflict (rule 8).

**Step 2 — Frame (show before concepts).** From the grounding brief **and** the web capture (if any), write the problem frame in the reply (and later into the draft):
- Jobs-to-be-done hypotheses
- In / out of scope
- Non-goals (already-decided sibling work from decided-vs-open)
- Evidence strength table (what we know / don't, with strength)

Show this frame **before** any concepts.

**Step 3 — Gate.** If gatherer gaps are material (could change problem, audience, or scope) or the PM is newly owning the area with thin context: return a batched set of QUESTIONS and **wait**. Do not invent answers. If gaps are low-impact, mark `[NEEDS INPUT: …]` in the draft and continue.

**Step 4 — Options.** After the frame (and after any gate answers): 2–4 concepts. For each: what job it serves, density/coverage fit if relevant, risks, what evidence would validate it. Stress-test against the Step 1.5 **solutions** (and competitive) hits — deepen with `_web-search.md` if the capture was thin on solutions. Not fabricated in-app product tours.

**Step 5 — Write.** Write `drafts/[slug]-product-brief.md` (slug from INIT name or topic). Outline:

1. Status line (draft, meeting/check-in if known, surfaces/scope if known)
2. Summary + explicit ask for the meeting
3. Starting point / what exists (from workspace — cite prior analyses by path/date; do not present a fresh code read as first-line truth when a dated digest exists)
4. Evidence table (what we know / don't — with strength)
5. What decided work leaves unsolved (or open problem parts)
6. Bet or principles (short)
7. Concepts (2–4) with tradeoffs
8. What to measure / learn first (if evidence supports; else `[NEEDS INPUT]`)
9. Open questions

**Step 6 — Close.** Lightly update the INIT row notes with path to the draft and date (keep id/order). Propose a TODO only if an open action is clear. Tell the PM the next step when ready is `/build prd-package` — **do not run it** from this workflow.

End gathering with one line: context used / excluded (rule 18) when the source set was a real choice.
