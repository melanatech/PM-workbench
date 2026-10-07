---
name: ship-signal
description: >
  Use when the PM asks about ship signal, release readout, did this release move
  the needle, advance the release loop, post-ship measurement, or DATA GAP on a
  release. Runs /report ship-signal — typed stages with data-request GATE; never
  invent warehouse numbers.
---

# Ship→Signal (plain-language entry)

Run `/report ship-signal` (workflow `.claude/workflows/ship-signal.md`). One stage per pass. Artifacts under `outputs/releases/<id>/`. Templates in `reference/templates/ship-signal/`.
