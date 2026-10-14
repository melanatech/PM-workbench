---
name: roadmap-build
description: >
  Use when the PM says build a roadmap or draft a roadmap from scratch.
  Runs /report roadmap-build (Standard; sonnet). Deep upgrades the runner to opus
  after a usage estimate. Discovery phase first. Not "the roadmap changed"
  (that is /sync roadmap-update).
---

# roadmap-build

Plain-language entry for **`/report roadmap-build`**.

1. Read `.claude/workflows/_plain-language.md` (do not improvise a lighter path).
2. Execute `.claude/workflows/roadmap-build.md` in full (same gates as the slash command). Prefer dispatching via the `/report` router / `workflow-runner` when in a cluster session; otherwise run the workflow inline.
3. Keep every Step 0 / discovery / cold-start / red-team requirement in that file.

Forbidden: inventing an ad-hoc shortcut because the user did not type a slash command. Forbidden: sequencing Now / Next / Later before a yes when priorities or the OKR map are missing or stale.
