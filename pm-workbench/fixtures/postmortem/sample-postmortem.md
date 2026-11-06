# Weekly update layout post-mortem — sample fixture

> **Sample fixture, not a real review.** This is an example of the file the workbench-health workflow writes on its own when a job fails (`.claude/workflows/workbench-health.md`, Postmortem). The job, the sessions, the quotes, and the fixes are fictional. A real postmortem is written to `outputs/monthly/[date]-[slug]-postmortem.md` in the live workspace and stays there.

**Date:** 2026-07-27
**Reviewed:** the weekly update sessions for the weeks of 2026-07-06, 2026-07-13, and 2026-07-20 (fictional transcripts)
**Trigger:** the template-drift correction theme in [fixtures/usage-story/sample-story.md](fixtures/usage-story/sample-story.md), which kept the weekly update from landing
**Primary satisfaction signal:** the PM said the update "keeps coming back in the old layout" and that fixing it by hand costs more than writing it.

---

## Executive verdict

**Fail on layout, pass on content.** The facts in each weekly update were right and sourced. The layout was wrong every week: the agent rebuilt the update from the original template instead of last week's sent version, so the PM's layout changes never stuck. The PM restored the layout by hand each time before sending.

---

## Intended job and success criteria

Frozen before judging the run.

| Criterion | Pass bar |
|---|---|
| Accurate update | Every status and date traces to a register row or a named source |
| Keeps the approved layout | Same sections, order, and length as the last update the PM sent |
| Low supervision | The PM sends it without restructuring it |

---

## Lean progression

| Phase | Goal | Output | PM reaction / end state |
|---|---|---|---|
| First week | Draft the update | Update from the template | PM moved risks above wins and cut the metrics table. **Accepted after PM rework** |
| Second week | Draft the update | Update from the template again | Risks back below wins; metrics table back. PM: "same fix as last week." **Accepted after PM rework** |
| Third week | Draft the update | Update from the template again | Same layout. PM asked why the change keeps undoing itself. **Stopped for this review** |

**Requirements that stayed active and were never removed:** risks above wins; no metrics table; one screen long.

---

## Artifact lineage and quality retention

Each version is scored against the requirements as they stood when it was written: **kept**, **partly**, or **lost**.

| Version | Retention | Correction uptake | Durability | Audience fit | PM repair |
|---|---|---|---|---|---|
| First week | partly | n/a | n/a | partly | Medium |
| Second week | lost | lost | lost | partly | Medium |
| Third week | lost | lost | lost | partly | High |

**Reading:** content held every week. Layout corrections never carried forward, because each draft started from the same template.

---

## What went well

- Every status and date in the updates traced to a register row.
- The agent asked no questions the registers already answered.

## What went wrong

- **The draft started from the template, not from last week's sent update.**
- **The PM's layout correction lived only in chat.** Nothing wrote it down where the next run would read it.
- **The check passed a draft the PM rejected.** It tested that each section existed, not their order or length.

---

## Root causes

The "PM raised it" column separates the PM's diagnosis from causes found only by reading the transcripts and the workflow.

| # | Layer | Root cause | Evidence | Quality effect | Smallest fix | Kit or session | PM raised it |
|---|---|---|---|---|---|---|---|
| RC1 | Instructions | The workflow says to start from the template. | The weekly update workflow's first step; each week's draft matches the template, not the last sent file | Layout resets every week | Start from the last sent update when one exists; fall back to the template | Kit | Yes |
| RC2 | Memory | A layout correction is not saved anywhere the next run reads. | Template-drift theme in the usage story; the second-week transcript turn "same fix as last week" | The PM re-teaches it every week | Save the approved update as the baseline the next run starts from | Kit | Yes |
| RC3 | Verification | The check grades section presence, not layout. | The run log shows the check passing each draft the PM then restructured | A false "ready" signal | Compare section order and length against the baseline | Kit | No |

---

## Lessons

1. **The last approved file is the template.** A starter template is only for the first run.
2. **A correction that lives only in chat is lost by the next run.**
3. **A check that grades shape can pass the wrong shape.** Compare against what the PM approved.

---

## Prioritized improvements (propose only)

| # | P | Failure → mechanism | Expected behavior | Next-run check | Confidence |
|---|---|---|---|---|---|
| I1 | P0 | RC1 → start from the last sent update | Layout carries forward | The PM does not restructure the next update | High |
| I2 | P0 | RC2 → save the sent update as the baseline | The correction survives the next run | No repeat of a layout correction | High |
| I3 | P1 | RC3 → layout comparison in the check | No "ready" on a reset layout | The check fails a draft whose order differs from the baseline | Medium |

**What not to change:** the sourcing rule for statuses and dates. It held every week.

---

## Proposed next test

**Job:** the next weekly update, after I1 and I2.

**Pass bar, judged by the PM, not by the check:**

1. The PM sends it without restructuring it.
2. No layout correction is repeated.

---

## Sources and limitations

- Transcripts for the three weekly update sessions (fictional). PM turns were read by hand and sorted into repair or new direction; another reader could sort a turn differently.
- The workflow step text and the check, read at the time of the review.
- **What this cannot claim:** that the layout cost the PM a measured amount of time, or that any earlier kit change caused or prevented the reset. No time was measured, and any line-up against a kit change is association, not causation.
- Not audited: tool traces beyond the drafts themselves.

---

## Review gate (calibration)

1. Which root causes feel accurate, overstated, or missing?
2. Approve I1 and I2 for the kit? Nothing changes until you say so.
3. Approve a line for `logs/review-notes.csv`? Nothing is written there until you approve.
