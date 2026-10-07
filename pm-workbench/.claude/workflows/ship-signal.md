---
description: Advance one stage of the Ship→Signal release measurement loop (notes → metrics → data request → readout → report)
---

Execution mode: **fast** (fast=0 reviewers, standard=1–2, deep=full panel — see CLAUDE.md). Override inline if I say so.

Ship→Signal for: $ARGUMENTS

**Purpose.** Typed post-ship measurement loop. One stage per pass. Never invent warehouse queries — emit a data-request, HALT for human fulfillment, then read exports. Verdicts are pre-registered and non-causal for pre/post.

**Artifact root (live):** `outputs/releases/<release-id>/`. Create the folder when starting a release. Templates: `reference/templates/ship-signal/`. Methodology: `reference/methodology/experimentation/`.

## State table (match top to bottom; first match wins)

| Observed state | Next action |
|---|---|
| no release dir / empty | Ask for release-id (or use $ARGUMENTS); create dir; draft `shipped-changes.md` from git notes / pasted changelog / inbox — GATE: human confirms notes before metrics |
| `shipped-changes.md` present, no `metric-proposals.md` | GATE: confirm notes → draft `metric-proposals.md` + `data-request.md` (status: open) |
| proposals present, any data-request still `open` | **HALT:** list open requests; point at fulfillment (drop CSV/export under `outputs/releases/<id>/data/` and set request status `fulfilled`). Do not invent numbers. |
| requests fulfilled, no `baseline.md` | GATE → write `baseline.md` from cited `data/*` files only |
| `baseline.md` present, no `readout.md` | Write `readout.md` with per-metric `**VERDICT: MOVED|FLAT|INCONCLUSIVE|DATA GAP**`, pre-registered direction line, causal note |
| `readout.md` present, no `report.md` | GATE: human read readout → write `report.md` (summarize only — **no new analysis**) |
| all present | Report loop complete; one-line verdict per metric |

**Hard rules**
- Never skip a GATE. Never run two stages in one pass.
- State = file existence + `status:` fields — not chat memory.
- Missing export → `**VERDICT: DATA GAP**` (or leave request open and HALT). Do not fabricate metrics from training data.
- Experiment design for INCONCLUSIVE → offer `/build experiment-package` (do not reimplement that workflow here).
- Cite every number as `(data/<file>)`.

## Verdict vocabulary (readout)

Exact line form (alone on its line):

```
**VERDICT: MOVED**
**VERDICT: FLAT**
**VERDICT: INCONCLUSIVE**
**VERDICT: DATA GAP**
```

Plus: `Pre-registered direction: …` and `Causal note: …` per `reference/templates/ship-signal/readout.md`.

## RESULT

Name release-id, which state row matched, what was written (paths), open GATEs/HALTs, Surfaces if any fan-out to INIT-/learning. Link artifacts under `outputs/releases/…`.
