---
description: "Understand a feature at code level via read-only GitHub clones"
argument-hint: "[feature/area] [repo if known]"
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Code-level understanding of: $ARGUMENTS

1. Clone the repo into `repos/` if absent (READ-ONLY — never push to company repos).
2. Dispatch exploration to the `code-repo-explorer` subagent — reading a whole repo's file tree has no reason to live in this session; it returns only the distilled findings (entry points, main flow, data models, feature flags, hard-coded limits).
3. Cross-check its findings against `learning/` for this area — where the code contradicts docs or the UI walkthrough, flag it prominently; those contradictions are the gold.
4. Also append anything architectural (services, APIs, data models, feature flags, ownership, cross-repo dependencies) to `reference/product-knowledge/architecture.md` — this file compounds across every code-dive into a product-wide technical map, which is what makes you faster at every FUTURE feature, not just this one. Then append the feature-specific findings to `learning/[area]/code-findings.md`: how it actually works in product terms; constraints the code reveals; tech-debt/bottleneck smells worth raising with engineering. Pitch: technical-ish PM — enough specifics to hold my own with engineering counterparts, framed as "what this means for product decisions."

**If the repo is ambiguous or unknown:** list plausible candidates from `repos/` (or ask which repo to clone) rather than picking one silently.
