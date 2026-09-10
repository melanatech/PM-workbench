---
name: prototype-build
description: Build a runnable prototype (static HTML, a React/web app, or a mobile app), grounded in the Feature Contract, scaffolded as a real importable repo when it's non-trivial, styled with company design when available, then actually rendered and clicked through in a browser (real QA, not just a logic check) before stakeholder review.
model: sonnet
argument-hint: [what to prototype]
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Build: $ARGUMENTS

A prototype is the one artifact this system produces that a stakeholder will *see and click*, so "the code looks right" is not enough — it has to actually render and behave. This skill scaffolds the right kind of project for the job and then verifies it at runtime, not just on paper.

## Models — which step runs on what

Following the same routing discipline as the rest of the system (haiku=trivial, sonnet=default, opus=deep judgment) rather than leaving every step on the ambient session model:

- **Scaffolding (Step 2)** and **QA auto-fixes (Step 3 loop)** → **sonnet**. Mechanical/structural work with a bounded, well-specified fix target — doesn't need opus's deeper reasoning, and haiku is too weak for real code generation.
- **The stakeholder reviewers (Step 4; 1–2 in Standard, five in Deep)** → **sonnet** each, dispatched in parallel — matching `/prd-package`'s existing panel model, since these are the same reviewer agents.
- **Reconciliation against the PRD (Step 5)** → **sonnet**.
- Nothing in this skill defaults to **opus** — a prototype's judgment calls (does this design work, is this feasible) are exactly what the five-reviewer panel exists to distribute across specialized angles, so no single step needs opus-level depth on its own. If a genuinely hard architectural question comes up mid-build, say so and suggest a manual `/model opus` switch for that one exchange rather than upgrading the whole skill.
- **haiku** is intentionally unused here — nothing in this skill is a `/quick-close`-style trivial lookup.


## Step 0 — decide type, complexity, and design source (ask if unclear)

Three decisions shape everything after. Infer what you can from the flow being prototyped and the Feature Contract; ask only what's genuinely ambiguous.

**Type** — how will this run?
- **static** — HTML/CSS/JS, opens as a file, no build. Right for a single screen or a quick clickable flow.
- **web** — React/Vue/Svelte/etc. Needs `npm install` and a dev server. Right for multi-screen, stateful, or component-driven prototypes.
- **mobile** — Expo / React Native (or Flutter). Right when the interaction is fundamentally a phone experience. Prefer **Expo** because it can also render to web, which makes real QA possible without a simulator.

**Complexity** — throwaway vs. repo?
- **loose** — a couple of files under `prototypes/[name]/`. Fine for a static single-view throwaway.
- **repo** — anything multi-screen, stateful, framework-based, or that imports real components. Scaffold a proper git-initialized project (see Step 2) so it's a clean one-click GitHub import and has a structured home for imported design assets. When in doubt, scaffold a repo — it costs little and makes both import and QA reliable.

**Design source** — does this pull in company look-and-feel?
- Check `reference/design/` and `reference/links.csv` for: a **component library / design-system repo** (import and use its real components), and/or a **style-guide doc** (Figma/Confluence/PDF — extract tokens: colors, type, spacing, and match them). If both exist, prefer real components for structure and the style guide for tokens the components don't cover. If neither exists yet, build clean and generic and note in the README that design import is pending — never invent a fake "company style."

## Step 1 — ground it in the contract

Check `learning/` for this area. If `outputs/prds/[feature]/contract.md` exists, THAT is the spec the prototype implements — the contract, not a fresh reading of the whole PRD. If only a PRD exists, implement what it describes. If checking real product patterns needs a repo, dispatch `code-repo-explorer` rather than loading the repo here.

**Required input.** If no Feature Contract or PRD exists, ask for the flow (screens, the one interaction that matters, what the test needs to learn) before scaffolding. A title is not a spec.

## Step 2 — scaffold to match the type

Every prototype, whatever the type, must include the states that make a test honest — **empty, loading, error, permission-denied** — not just the happy path, plus variants behind a toggle, **visible instrumentation labels** showing which events would fire, and a reset control for repeated sessions.

- **static / loose:** `prototypes/[name]/index.html` (+ optional css/js). README with "open index.html in a browser."
- **web / repo:** a real project (e.g. Vite + React) with `package.json`, lockfile, `src/`, a `.gitignore`, and a README stating the exact run command (`npm install && npm run dev`). `git init` locally. Structure it so imported components have a home (`src/components/`, `src/theme/`).
- **mobile / repo:** an Expo project (`create-expo-app`) with the same README + git treatment, and — importantly — confirm it runs under **`expo start --web`** so it can be QA'd without a simulator. If the interaction truly can't be represented on web, say so and note that QA will be a build check + manual simulator checklist.

If a **component library** is the design source, install/link it and build screens from its real components. If a **style-guide doc** is the source, extract tokens into `src/theme/` (or a `:root` block for static) and apply them.

## Step 3 — QA: actually run it and look (do not skip, do not fake)

This is the step that distinguishes a real prototype from a plausible-looking one. Run the bundled QA harness in `qa/` (see `qa/README.md` for prerequisites — it needs a local browser via Playwright, free/open-source, no API or cost — see note below).

**What the harness does, per type:**
- **static:** open the file, walk to every declared state, screenshot each, click every interactive element once, assert the DOM changes and no console error fires, confirm instrumentation labels are actually visible in each state.
- **web:** `npm install`, then `npm run build` (a build failure is a real failure a demo would hit — catch it here), boot the dev server, wait until ready, then run the same state-walk / click / screenshot / console-error pass against `localhost`.
- **mobile (Expo):** `expo start --web`, then the same browser pass against the web render. Note in the report that this is the web render, not a true native simulator.

**Output — always inspectable, never a bare "looks good":** the harness writes `prototypes/[name]/qa-report.md` (which states pass/fail per check, per state) plus `prototypes/[name]/qa-screenshots/`. Show me the report and the key screenshots.

**Honest environment fallback.** Real rendering needs local execution (i.e. Claude Code on a machine with a browser, and network to `npm install`). 
- In Claude Code with those available → run the full harness above.
- In a chat-only / no-local-exec environment → you **cannot** truly render it. Run structural checks (build config sanity, referenced files exist, state handlers wired) and **say explicitly**: "structural checks only — not visually verified; run `qa/` in Claude Code for a real render." Never claim a visual pass that didn't happen.
- Native-mobile without a simulator → build check + a written manual QA checklist for the states, clearly labeled as needing a device/simulator. Not a fake pass.

### Bounded QA auto-fix loop (objective failures only)

QA failures are objective (a console error, a state that never renders, a click that throws) — safe to fix without asking each time, but **never open-ended**:

1. QA fails → patch the specific failing thing (nothing else) → re-run QA.
2. Repeat up to **1 time** (2 QA runs max: original + 1 retry).
3. Still failing after that → **stop**, show the current `qa-report.md`, and hand it to me rather than continuing to spin. A capped, reported failure beats an uncapped loop quietly consuming usage.

This loop never touches product judgment — it only fixes what QA can prove is broken.

## Step 4 — stakeholder review (now on something known to render)

Dispatch reviewers from the same set `/prd-package` uses (`eng-feasibility-reviewer`, `design-ux-reviewer`, `data-instrumentation-reviewer`, `business-revenue-reviewer`, `customer-facing-reviewer`), once, when the prototype is test-ready — **bounded by execution mode: Standard = the 1–2 most relevant (default `design-ux-reviewer` + `eng-feasibility-reviewer`, stated with the reason); the full five only in Deep or on request.** **QA passing is a hard gate for this step** — do not dispatch reviewers against a prototype QA couldn't get to render cleanly; a review of something broken wastes the panel. Give each reviewer the **actual QA screenshots** (`qa-screenshots/*.png`) and the `qa-report.md` verdict, not a text description of the states — their judgment should be grounded in what actually rendered, not a paraphrase of it. Per execution mode: in Standard, do not also fan out elsewhere in the same run.

### Bounded reviewer-revision loop (judgment calls — gated by you, not automatic)

Reviewer flags are judgment calls, not bugs — a flag might be a real product decision, so this loop never runs silently:

1. Reviewers flag concerns → present them to me **batched**, one list, not five separate interruptions.
2. I say which flags to act on (some may be accepted as-is, deferred, or rejected — my call).
3. Agent revises only what I approved → **re-runs QA** (a revision can break something QA already passed — never skip re-verifying this) → if QA passes, **re-dispatch only the reviewer(s) whose specific concern was addressed**, not the full five-person panel again.
4. Repeat at most **once more** after the first revision round. If concerns remain after that, stop and report current state plainly — "still flagged: X, Y — your call on whether to iterate again or ship with known gaps."

This loop terminates by honest reporting, not by deciding on its own that the prototype has become "acceptable" — that threshold is always yours to call, and each additional round costs a real reviewer dispatch, so the cap keeps that cost visible and bounded rather than open-ended.



## Step 5 — reconcile against the PRD

If `outputs/prds/[feature]/` exists, dispatch `prd-prototype-reconciler` to check what got built against what the PRD specified. Surface discrepancies both directions ("fix the prototype" vs. "building this surfaced something the PRD missed") and let me decide — don't auto-resolve.

## Step 6 — register + repo handoff

Update `registers/initiatives.csv`: stage=prototype, prototype_path, last_updated (create the row if none exists). Then: git is already initialized (Step 2). **I create the GitHub remote myself; you give me the exact push commands and never push yourself.** For a repo-complexity prototype, confirm the README's run command matches what the QA harness actually used — that's the command the next person will trust.

## Step 7 — pair with a research package

Auto-generate the matching research package (same logic as `/research-package`) so the test plan exists the moment the prototype does. After sessions run, if findings contradict a PRD assumption, flag it and suggest `/prd-prototype-sync` rather than letting the two drift.
