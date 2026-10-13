---
description: "Understand a feature at code level via read-only GitHub clones"
argument-hint: "[feature/area] [repo if known]"
---

Execution mode: **standard** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Code-level understanding of: $ARGUMENTS

0. **Preflight:** `python3 scripts/context_preflight.py --root <live> --topic "$ARGUMENTS"`. Reuse dated code-dive / learning hits when recommendation is `reuse`. Prefer `reference/repo-map.md` / preflight `repo_map` rows to pick the repo (product over mock on overlapping surfaces). Only open `repos/` when `allow_repos` is true (re-run with `--allow-repos` or `--verify` if needed).
1. Clone the repo into `repos/` if absent (READ-ONLY — never push to company repos). If `repos/<name>` already exists — including a **symlink** to a clone outside the live tree (NEW-USER-SETUP §2a) — do **not** clone or `rm` over it; explore through that path. After clone/symlink, run `python3 scripts/repo_profile.py --root <live>` so the surface map stays current.
2. Dispatch exploration to the `code-repo-explorer` subagent — reading a whole repo's file tree has no reason to live in this session; it returns only the distilled findings (entry points, main flow, data models, feature flags, hard-coded limits).
3. Cross-check its findings against `learning/` for this area — where the code contradicts docs or the UI walkthrough, flag it prominently; those contradictions are the gold.
4. Also append anything architectural (services, APIs, data models, feature flags, ownership, cross-repo dependencies) to `reference/product-knowledge/architecture.md` — this file compounds across every code-dive into a product-wide technical map, which is what makes you faster at every FUTURE feature, not just this one. Then append the feature-specific findings to `learning/[area]/code-findings.md`: how it actually works in product terms; constraints the code reveals; tech-debt/bottleneck smells worth raising with engineering. Pitch: technical-ish PM — enough specifics to hold my own with engineering counterparts, framed as "what this means for product decisions."
5. **Index:** `python3 scripts/analysis_index.py append --root <live> --topic-key "<tokens>" --path learning/[area]/code-findings.md --kind code-dive --as-of <today> --one-line "<summary>" --primary-sources "repos/<name>@<commit>" --source-workflow code-dive`

**If the repo is ambiguous or unknown:** use repo-map / preflight rankings first; otherwise list plausible candidates from `repos/` (or ask which repo to clone) rather than picking one silently.
