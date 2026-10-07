# Experimentation methodology (portable)

Topic-split reference for experiment design. Used by `/build experiment-package` and `/report ship-signal`. Plain markdown — no plugin install required.

| File | Topic |
|---|---|
| [sample-size-and-power.md](sample-size-and-power.md) | MDE, power, why you can't size by feel |
| [cohort-and-population-design.md](cohort-and-population-design.md) | Matching comparison construct to how a change ships |
| [guardrail-and-decision-metrics.md](guardrail-and-decision-metrics.md) | Decision metric vs guardrails |
| [pre-registration-and-peeking.md](pre-registration-and-peeking.md) | Peeking inflates false positives |
| [common-pitfalls.md](common-pitfalls.md) | Framing pitfalls (homogeneity, matched windows, proxy vs target, …) |

**Scope:** methodology only — not “does this event fire” or warehouse table contents. Data access stays external (exports into `inbox/` / `outputs/releases/<id>/data/`).
