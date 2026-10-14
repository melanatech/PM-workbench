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
- **The stakeholder reviewers (Step 4; 1–2 in Standard, five in Deep)** → **sonnet** each, dispatched in parallel — matching `/build prd-package`'s existing panel model, since these are the same reviewer agents.
- **Reconciliation against the PRD (Step 5)** → **sonnet**.
- Nothing in this skill defaults to **opus** — a prototype's judgment calls (does this design work, is this feasible) are exactly what the five-reviewer panel exists to distribute across specialized angles, so no single step needs opus-level depth on its own. If a genuinely hard architectural question comes up mid-build, say so and suggest a manual `/model opus` switch for that one exchange rather than upgrading the whole skill.
- **haiku** is intentionally unused here — nothing in this skill is a `/quick-close`-style trivial lookup.


## Step 0 — preflight, source selection, type, complexity, design source

**0a. Context preflight (required).** Run `python3 scripts/context_preflight.py --root <live> --topic "$ARGUMENTS"`. Read `state/.context-preflight.json` hits + `repo_map`. Reuse prior code-dive / product-flow analyses before dispatching `code-repo-explorer`. Do not open `repos/` until `allow_repos` is true.

**0b. Source-derived baseline (third mode).** When any variant depicts **today**, use fixed id `baseline`. Greenfield apps that cannot run a private UI base still **port** screens from the highest-ranked source on SOURCE-POLICY's "what users see today" ladder:

1. Read preflight `repo_map` rows for the surfaces being prototyped.
2. Prefer live captures if present; else the **product** repo at a named commit; else the **mock** repo for surfaces the product repo doesn't cover (flag as dated snapshot).
3. Port needed pieces into `prototypes/[name]/src/baseline/` (or equivalent). Write `prototypes/[name]/BASELINE-SOURCES.md` — one row per visible baseline element: element, source path:line or commit or capture, as-of date. Elements without a source are `[assumed]` here and labeled in the UI.
4. **Fidelity:** baseline must not be worse or better than today. If a source shows an element exists (e.g. a placeholder tooltip), include it with that source's content.
5. After clone/symlink of any repo, run `python3 scripts/repo_profile.py --root <live>`.

"Not runnable" (private registry) means **port from source**, not "ignore the repo."

Then decide type / complexity / design source. Infer what you can from the flow and Feature Contract; ask only what's genuinely ambiguous.

**Type** — how will this run?
- **static** — HTML/CSS/JS, opens as a file, no build. Right for a single screen or a quick clickable flow.
- **web** — React/Vue/Svelte/etc. Needs `npm install` and a dev server. Right for multi-screen, stateful, or component-driven prototypes.
- **mobile** — Expo / React Native (or Flutter). Right when the interaction is fundamentally a phone experience. Prefer **Expo** because it can also render to web, which makes real QA possible without a simulator.

**Complexity** — throwaway vs. repo?
- **loose** — a couple of files under `prototypes/[name]/`. Fine for a static single-view throwaway.
- **repo** — anything multi-screen, stateful, framework-based, or that imports real components. Scaffold a proper git-initialized project (see Step 2) so it's a clean one-click GitHub import and has a structured home for imported design assets. When in doubt, scaffold a repo — it costs little and makes both import and QA reliable.

**Design source** — does this pull in company look-and-feel?
- Check `reference/design/` and `reference/links.csv` for: a **component library / design-system repo** (import and use its real components), and/or a **style-guide doc** (Figma/Confluence/PDF — extract tokens: colors, type, spacing, and match them). If both exist, prefer real components for structure and the style guide for tokens the components don't cover. If neither exists yet, build clean and generic and note in the README that design import is pending — never invent a fake "company style."
- **Shared kit + soft reuse:** if `prototypes/_shared/package.json` exists, new **web** / **repo** prototypes add `"@pm-live/prototype-kit": "file:../_shared"`, import `@pm-live/prototype-kit/theme.css` + `kit.css`, and use matching exports (Drawer, HelpPopover, InfoTip, ScenarioGuide, …) instead of copying them. Quantity helpers are `sum`, `ratio`, `format`, and `assertInvariant` from `@pm-live/prototype-kit/numbers` (see Grounded numbers in Step 2). Still read `reference/design/prototype-components.md` for pieces **not** promoted (Status ≠ `in _shared`) — copy/adapt those and note `Adapted from …` in the README. If `_shared` is missing, soft-copy only. Promotion rule: catalog row copied ≥2 times → offer move into `_shared` (ask the PM). See `reference/design/shared-prototype-package.md`. If nothing matches, skip — do not invent fake shared components.

## Step 1 — ground it in the contract (and brief)

Check `learning/` for this area. If `outputs/prds/[feature]/contract.md` exists, THAT is the spec the prototype implements — the contract, not a fresh reading of the whole PRD. If only a PRD exists, implement what it describes. If only a product brief exists (`drafts/*-product-brief.md`), ground the baseline in its "Starting point / what exists" and Concepts sections — still via primary sources / BASELINE-SOURCES, never by citing the brief as evidence. If checking real product patterns needs a repo, dispatch `code-repo-explorer` only after preflight allows it.

**Required input.** If no Feature Contract, PRD, or brief exists, ask for the flow (screens, the one interaction that matters, what the test needs to learn) before scaffolding. A title is not a spec.

## Step 2 — scaffold to match the type

Every prototype, whatever the type, must include the states that make a test honest — **empty, loading, error, permission-denied** — not just the happy path, plus variants behind a toggle, **visible instrumentation labels** showing which events would fire, and a reset control for repeated sessions.

- **static / loose:** `prototypes/[name]/index.html` (+ optional css/js). README with "open index.html in a browser."
- **web / repo:** a real project (e.g. Vite + React) with `package.json`, lockfile, `src/`, a `.gitignore`, and a README stating the exact run command (`npm install && npm run dev`). `git init` locally. Structure it so imported components have a home (`src/components/`, `src/theme/`).
- **mobile / repo:** an Expo project (`create-expo-app`) with the same README + git treatment, and — importantly — confirm it runs under **`expo start --web`** so it can be QA'd without a simulator. If the interaction truly can't be represented on web, say so and note that QA will be a build check + manual simulator checklist.

If a **component library** is the design source, install/link it and build screens from its real components. If a **style-guide doc** is the source, extract tokens into `src/theme/` (or a `:root` block for static) and apply them. If `_shared` is present, wire it before inventing parallel primitives; then soft-copy any unpromoted catalog rows.

**Catalog update.** When this build creates a reusable piece (shell, shared table pattern, state kit) worth stealing later, append a row to `reference/design/prototype-components.md` (date, name, path, reuse-when, status, notes) in the same run — do not wait for a later cleanup pass. If it belongs in `_shared`, prefer promoting there (ask PM when ≥2 prior copies).

**UX Guardrails preflight (reduce first-pass failures).** Before inventing controls, read `reference/design/ux-guardrails-lessons.md` and apply every **Standing preflight** item that fits. The MCP does not learn across sessions — only this file, `_shared` primitives, and prior QA notes carry fixes forward. After a Guardrails `check` with failures: fix the UX (in `_shared` when the control is shared), then **append a lesson row** in the same run before claiming done.

**Handoff paths (document in README).** (1) **Static** — single `index.html`, open in a browser. (2) **React** — `npm run build` → zip/`preview`; optional `npm run share` (single-file HTML via e.g. `vite-plugin-singlefile`) so stakeholders need not `npm install`. Do not require every concept test to be static.

**Optional — Scenario Guide (evaluator walkthrough).** If the prototype has multiple concepts/personas or a stakeholder demo soon, offer a Guide panel per `.claude/workflows/_scenario-guide.md` / skill `scenario-guide`. Default **off** for single-screen throwaways; when added, import `ScenarioGuide` from `@pm-live/prototype-kit` (if `_shared` exists) or adapt the recipe, and keep **scripts** local to the feature. When the Guide shows quantities, it reads them through the same selectors as the screens (see `_scenario-guide.md`). Do not block the build waiting for a Guide.

**Grounded numbers.** When the prototype shows quantities — counts, money, durations, scores, percentages, inventory levels, ratings, or dates — every displayed number comes from one fixture. Skip this when the screen has no quantities. Apply it on new builds; do not retrofit prototypes that already exist.

- **One fixture of raw records** at `src/data/fixture.js` (static HTML: `data/fixture.json`) with a fixed `asOf` date. Records are whatever the product deals in, such as tasks, tickets, or sessions.
- **Selectors** in `src/data/selectors.js` derive every displayed number. Components import those functions and render them. Mark each displayed quantity with `data-metric="<id>"` on the element that shows it. A genuine constant that is not a product quantity (page size, layout) gets a `quantity-ok` comment on that line or on the nearest preceding non-empty line.
- **Invariants** in `src/data/invariants.js`, run with `node` (exit nonzero on failure): parts sum to the whole (segments, legend, table, and total agree); rates and percentages stay in bounds, and a filtered subset is never larger than its parent; the same metric comes from the same selector everywhere it appears; dates agree with `asOf` (no future events in a past view). Let `assertInvariant` throw — do not catch it.
- **Where the helpers live.** `sum`, `ratio`, `format`, and `assertInvariant` ship in `@pm-live/prototype-kit` (`prototypes/_shared/src/data/numbers.js`), importable as `@pm-live/prototype-kit/numbers` and re-exported from the package index. Use that subpath from `src/data/*` so plain `node` does not load React components. `_shared` is live-only: the kit does not ship it, and `create_live_workspace.py` does not seed it. If `_shared` exists but has no `numbers.js` yet, add the module below, re-export it from `src/index.js`, and add `"./numbers": "./src/data/numbers.js"` to the package `exports` map. If there is no `_shared`, put one copy of the same module at the prototype's `src/data/numbers.js` and import that. Do not copy the helpers into components.

```js
// prototypes/_shared/src/data/numbers.js  (or src/data/numbers.js when _shared is absent)
function toNumber(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

export function sum(rows, pick) {
  if (rows == null) return 0
  const list = typeof pick === 'function' ? Array.from(rows, pick) : Array.from(rows)
  return list.reduce((total, value) => total + toNumber(value), 0)
}

export function ratio(part, whole) {
  const denominator = toNumber(whole)
  if (denominator === 0) return 0
  return toNumber(part) / denominator
}

// kind: count (locale number) | money (USD) | percent (ratio 0–1 → 12.5%) | duration (minutes → 45m or 1h 30m)
export function format(value, kind = 'count') {
  const n = toNumber(value)
  if (kind === 'money') {
    return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
  }
  if (kind === 'percent') {
    const rounded = Math.round(n * 1000) / 10
    const text = Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1)
    return `${text}%`
  }
  if (kind === 'duration') {
    const sign = n < 0 ? '-' : ''
    const total = Math.round(Math.abs(n))
    const hours = Math.floor(total / 60)
    const mins = total % 60
    if (hours && mins) return `${sign}${hours}h ${mins}m`
    if (hours) return `${sign}${hours}h`
    return `${sign}${mins}m`
  }
  return n.toLocaleString('en-US')
}

export function assertInvariant(ok, message) {
  if (!ok) {
    const text = `Invariant failed: ${message}`
    console.error(text)
    throw new Error(text)
  }
}
```

**Checkpoint after scaffold.** Even for loose static: `python3 scripts/prototype_checkpoint.py --path prototypes/[name] --label after-scaffold` (creates local `git init` if missing; never pushes). See Checkpoints below.

**Readiness checklist (non-blocking unless asked):** consult `reference/templates/prototype-readiness-checklist.md`. Note any Red dimensions in RESULT. Do not block the build unless the PM asked for a hard readiness gate.

## Step 3 — QA: actually run it and look (do not skip, do not fake)

This is the step that distinguishes a real prototype from a plausible-looking one. Run the bundled QA harness in `qa/` (see `qa/README.md` for prerequisites — it needs a local browser via Playwright, free/open-source, no API or cost — see note below).

**Baseline source map gate:** if the prototype has a `baseline` variant (toggle/state/route), QA **fails** when `BASELINE-SOURCES.md` is missing or empty. Fix that before treating QA as passed.

**Grounded-numbers check.** When the prototype shows quantities, run `python3 scripts/check_prototype_data.py prototypes/[name]` before the browser harness, and again after a QA auto-fix that touched displayed numbers. Nonzero exit fails QA. The script flags quantity-like literals in `src/**/*.{js,jsx,tsx,html}` outside `src/data/` (and in a root `index.html` when that file exists), runs `node src/data/invariants.js` when that file exists, and flags a `data-metric` rendered in more than one component from different selectors or local copies. A `quantity-ok` comment allows a real constant. If `node` is missing, the script skips only the invariant run and says so — that skip is not a pass of the invariants. Append the script's stdout to `qa-report.md`. Put quantity-bearing static markup under `src/` (a root `index.html` is scanned too) so the check can see it.

**What the harness does, per type:**
- **static:** open the file, walk to every declared state, screenshot each, click every interactive element once, assert the DOM changes and no console error fires, confirm instrumentation labels are actually visible in each state.
- **web:** `npm install`, then `npm run build` (a build failure is a real failure a demo would hit — catch it here), boot the dev server, wait until ready, then run the same state-walk / click / screenshot / console-error pass against `localhost`.
- **mobile (Expo):** `expo start --web`, then the same browser pass against the web render. Note in the report that this is the web render, not a true native simulator.

**Output — always inspectable, never a bare "looks good":** the harness writes `prototypes/[name]/qa-report.md` (which states pass/fail per check, per state) plus `prototypes/[name]/qa-screenshots/`. Show me the report and the key screenshots.

**Checkpoint after a QA pass** (including after a successful QA retry): `python3 scripts/prototype_checkpoint.py --path prototypes/[name] --label after-qa`. Do not checkpoint a failing tip — fix or stop first.

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

Dispatch reviewers from the same set `/build prd-package` uses (`eng-feasibility-reviewer`, `design-ux-reviewer`, `data-instrumentation-reviewer`, `business-revenue-reviewer`, `customer-facing-reviewer`), once, when the prototype is test-ready — **bounded by execution mode: Standard = the 1–2 most relevant (default `design-ux-reviewer` + `eng-feasibility-reviewer`, stated with the reason); the full five only in Deep or on request.** **QA passing is a hard gate for this step** — do not dispatch reviewers against a prototype QA couldn't get to render cleanly; a review of something broken wastes the panel. Give each reviewer the **actual QA screenshots** (`qa-screenshots/*.png`) and the `qa-report.md` verdict, not a text description of the states — their judgment should be grounded in what actually rendered, not a paraphrase of it. Per execution mode: in Standard, do not also fan out elsewhere in the same run.

### Bounded reviewer-revision loop (judgment calls — gated by you, not automatic)

Reviewer flags are judgment calls, not bugs — a flag might be a real product decision, so this loop never runs silently:

1. Reviewers flag concerns → present them to me **batched**, one list, not five separate interruptions.
2. I say which flags to act on (some may be accepted as-is, deferred, or rejected — my call).
3. Agent revises only what I approved → **re-runs QA** (a revision can break something QA already passed — never skip re-verifying this) → if QA passes, **checkpoint** with `--label after-revision-qa`, then **re-dispatch only the reviewer(s) whose specific concern was addressed**, not the full five-person panel again.
4. Repeat at most **once more** after the first revision round. If concerns remain after that, stop and report current state plainly — "still flagged: X, Y — your call on whether to iterate again or ship with known gaps."

This loop terminates by honest reporting, not by deciding on its own that the prototype has become "acceptable" — that threshold is always yours to call, and each additional round costs a real reviewer dispatch, so the cap keeps that cost visible and bounded rather than open-ended.

## Checkpoints (local restore points — not Plans)

Prototypes get **git checkpoints** so a bad revision can be rolled back without inventing Claude Code Plans. Rules:

- Script: `scripts/prototype_checkpoint.py` — commits inside `prototypes/[name]/` only; **never pushes**; refuses paths outside `prototypes/`.
- Label index (survives restore): `logs/prototype-checkpoints/[name].md`.
- Required labels during a build: `after-scaffold`, `after-qa`, and `after-revision-qa` when a reviewer-driven revision re-passes QA. Optional ad-hoc: `--label before-risky-change` before a large experiment.
- Restore when I ask, or when a revision clearly regressed a prior QA pass and I have not asked to keep the new tip: `python3 scripts/prototype_checkpoint.py --path prototypes/[name] --restore after-qa` (add `--force` only if the working tree is dirty and I approved discarding it).
- After restore, say the commit short hash and offer `git switch -c resume-<hash>` if editing continues.
- List: `--list`. Do not invent Claude Code Plans / plan files for prototype work.

## Step 5 — reconcile against upstream (brief or PRD)

If a product brief (`drafts/*-product-brief.md`) **or** `outputs/prds/[feature]/` exists, dispatch `prd-prototype-reconciler` with that upstream. It accepts a brief or a PRD (not PRD-only). When only a brief exists, reconcile against "Starting point / what exists" and Concepts. Explicitly check the `baseline` variant against "what exists today" claims and against `BASELINE-SOURCES.md`. Pass the grounded-numbers check stdout (`python3 scripts/check_prototype_data.py`, the same text appended to `qa-report.md`) in with the prototype so quantity drift is part of reconciliation. Surface discrepancies both directions and let me decide — don't auto-resolve.

## Step 6 — register + repo handoff

Update `registers/initiatives.csv`: stage=prototype, prototype_path, last_updated (create the row if none exists). Then: git is already initialized (Step 2 / checkpoints). **I create the GitHub remote myself; you give me the exact push commands and never push yourself.** Mention that local checkpoints already exist (`--list`) and are separate from any remote. For a repo-complexity prototype, confirm the README's run command matches what the QA harness actually used — that's the command the next person will trust.

## Step 7 — pair with a research package

Auto-generate the matching research package (same logic as `/discover research-package`) so the test plan exists the moment the prototype does. After sessions run, if findings contradict a PRD assumption, flag it and suggest `/build prd-prototype-sync` rather than letting the two drift.
