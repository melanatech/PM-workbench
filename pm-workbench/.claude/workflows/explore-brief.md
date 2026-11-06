---
description: Pre-PRD product check-in brief - assemble initiative context, frame the problem, then options
argument-hint: [INIT-nnn | COM-nnn | feature or problem]
---

Execution mode: **standard** (fast=0 reviewers, standard=bounded gather, deep not used here — see CLAUDE.md). Override inline if I say so.

Context dependencies: soft: product-areas, audiences | hard: none

Explore / check-in brief for: $ARGUMENTS

This is the precursor to a PRD. It discovers and explores the idea so the PM can walk into a discussion and, later, a PRD. The original job still leads: frame the problem, write the user stories, and explore alternatives before any one of them is the answer.

From that, the brief also answers:

- What is this going to be, and what does it do?
- What should the requirements focus on? The problems, jobs, and boundaries a later PRD has to specify. Not the process of writing them.
- How do we explain it to the team so the discussion is productive?
- How does the PM sell it cross-functionally?

It is **not** a PRD package. No readiness score-as-PRD-gate, Feature Contract, stakeholder reviewer panel, or opus path. When the PM later wants a full PRD, they run `/build prd-package` (same gatherer).

**Hard rules**
- **Assemble before options.** Never lead with a single UI pattern or a solution sketch before the problem frame.
- **Workspace before repos.** Technical claims (instrumentation, how code works, what exists in product) must cite the gatherer's **Prior workspace analysis** section (paths + dates). Forbidden: "from the clone…" as the only source when `outputs/daily/` or `learning/` already analyzed the same topic. If you must re-check code, say why the prior analysis is insufficient or stale.
- **Decided vs open from the gatherer** — not from the user's last restatement alone.
- **Thought-partner:** challenge problem completeness; don't parrot the last user message into "the" problem.
- Do not invent facts to fill brief sections; use `[NEEDS INPUT: …]` or wait at the gate.
- **The file is the product brief, not the research log.** Sources are a short citation on the claim they support (path, decision id, date). Do not add sections that narrate the work: what was looked at, what was read, what was reviewed, what each source said, what is still unread, or how the agent got there. A finding that changes the product becomes one product sentence (a constraint, a gap, a precedent) with that citation. "Context used / excluded" is one line in the reply, not a section in the draft.

**Step 0 — Resolve + preflight.** Parse INIT-/COM-/topic from `$ARGUMENTS`. If the ask is only a vague "brief" with no initiative or commitment, ask once which INIT-/COM-/feature. Resolve COM → related INIT via `registers/commitments.csv` and `registers/initiatives.csv` text/links. Then run:
`python3 scripts/context_preflight.py --root <live> --topic "$ARGUMENTS"`
(use `--verify` if the PM asked to re-check). Read `state/.context-preflight.json`. One RESULT line: recommendation + hit count. Do not continue until this runs.

**Step 1 — Gather.** Dispatch `prd-context-gatherer` with the preflight marker (it consumes `.context-preflight.json` for Prior workspace analysis — do not replace the script with ad-hoc Grep). In parallel, dispatch `internal-docs-reader` when wiki, user research, or shared-drive docs are likely relevant. **Do not draft options or the brief body before the gatherer returns** (and the docs reader, if dispatched). On `reuse_and_refresh`, spot-check the newer surface before locking the frame.

**Step 1.5 — External grounding (web).** Follow `.claude/workflows/_web-search.md`. Run `python3 scripts/web_search.py` (not native WebSearch-only) and WebFetch for **problems, market/category, users, and solutions** relevant to the topic — unless the PM scoped fewer axes. Prefer help docs, launch posts, and public research over invented in-app tours. Write `state/web-search/YYYY-MM-DD-<slug>.md` when findings are consequential; index with `--kind web-search`. Reuse a same-day capture for the same slug when queries would not change. Mark unverified claims `[external::training]`. Workspace evidence still outranks web hits on conflict (rule 8).

**Step 2 — Problem frame (show before alternatives).** From the grounding brief **and** the web capture (if any), write the problem frame in the reply, then carry it into the draft as product content, not as a research recap:
- The problem, who has it, and the job to be done
- User stories: customer or operator needs (As a … I need … so that …). Needs, not a solution in disguise. Mark which are hypotheses.
- In / out of scope
- Non-goals (already-decided sibling work from decided-vs-open)

Show this frame **before** any alternatives.

**Step 3 — Gate.** If gatherer gaps are material (could change problem, audience, or scope) or the PM is newly owning the area with thin context: return a batched set of QUESTIONS and **wait**. Do not invent answers. If gaps are low-impact, mark `[NEEDS INPUT: …]` in the draft and continue.

**Step 4 — Alternatives.** After the frame (and after any gate answers): 2–4 alternatives. Exploring them is the point. Do not collapse to one recommendation unless the PM asked for a pick. For each: what it does, the user flow or workflow, which user story it serves, what it leaves out, what choosing it leaves on the table, the risk, the tradeoff, what would show this one is the right bet, and what its requirements would focus on. Stress-test against the Step 1.5 **solutions** (and competitive) hits — deepen with `_web-search.md` if the capture was thin on solutions. Not fabricated in-app product tours.

**Step 5 — Write.** Write `drafts/[slug]-product-brief.md` (slug from INIT name or topic). Write it so the PM can use it in the room. Lead with the problem frame, the user stories, and the alternatives. Then what the requirements should focus on, how to explain it so the discussion is productive, and how to sell it cross-functionally. It is the precursor to the PRD, not the PRD, and not a rundown of the research.

Outline:

1. Status line (draft, meeting if known, surfaces and scope if known)
2. Summary and the explicit ask for the meeting
3. Problem frame: the problem, who has it, in and out of scope, non-goals
4. User stories: the needs, marked as hypotheses where they are not yet evidenced
5. Starting point / what exists (cite the prior analysis by path and date on the claim; do not narrate the read)
6. What we know and what we don't, only where it changes the bet. A short list, each line cited. Not an evidence-strength table and not a tour of sources.
7. What decided work leaves unsolved
8. Bet or principles (short)
9. Alternatives (2–4): what each does, the user flow or workflow, which story it serves, what choosing it leaves on the table, the risk, the tradeoff, what would show it is the right bet, and what its requirements would focus on. Keep them as alternatives.
10. What the requirements should focus on, across those alternatives: the problems, jobs, and boundaries. Not the process of producing them.
11. What to measure or learn first
12. The discussion: how to explain this so the team can compare the alternatives, the case for each function that has to buy in, and what a productive outcome of the meeting is
13. Open questions

Do not add an evidence-strength table, a source-by-source tour, or a "what I reviewed" section.

Before the PM sees the brief, run the voice check (`_protocol.md` § Voice check) on `drafts/[slug]-product-brief.md`.

**Step 6 — Close.** Lightly update the INIT row notes with path to the draft and date (keep id/order). Propose a TODO only if an open action is clear. Tell the PM the next step when ready is `/build prd-package` — **do not run it** from this workflow.

End gathering with one line: context used / excluded (rule 18) when the source set was a real choice.

**Step 7 — Publish.** Defaults: `audience: internal`, `formats: [md]`. The brief in `drafts/` stays the internal source. Produce an external version only when the PM asks, then follow Audience and formats and Publish in `.claude/workflows/_protocol.md`. This workflow is Standard: when an external version is written, dispatch `external-readiness-reviewer` once on the rendered file and the audience line. Publishing or sending is Tier 3 and waits for an explicit yes. Do not call a wiki create API or a chat send API from this step.
