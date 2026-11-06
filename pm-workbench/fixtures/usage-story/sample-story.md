# Usage story — sample fixture (fictional, two weeks)

> **Sample fixture, not measured usage.** Every number below comes from the fictional rows in [fixtures/usage-story/state/usage-history.csv](fixtures/usage-story/state/usage-history.csv) and registers in this folder, run through `python3 scripts/usage_story.py data --root fixtures/usage-story --since 2026-07-06` (saved as [fixtures/usage-story/data.md](fixtures/usage-story/data.md)). Copy the shape, not the numbers. Ledger: [fixtures/usage-story/sample-story-number-ledger.md](fixtures/usage-story/sample-story-number-ledger.md).

## Executive summary

Most of my AI time went into named workbench workflows, not open-ended chat: 38% of calls in the first week and 40% in the second. Corrections fell from 3 of 7 PM messages in the week of 2026-07-06 (3 active days) to 1 of 5 in the week of 2026-07-13 (2 active days, partial). The corrections were about missed sources, one overstated fact, and one template drift. The work produced 2 decisions and 3 to-dos on file, 1 of them done. One kit change landed between the two weeks, so the second week is a short after period for it; the other has no after period yet. Cost was small and is a price-table estimate, not a billed figure.

## So what

1. Keep process-inbox and meeting-closeout as the daily loop; they carried most of the workflow calls in both weeks.
2. Make "list every source you read and skipped" the default output of any capture workflow, since missed sources were the largest correction theme.
3. Run this story again after a full week so the second week is not partial.
4. Keep the secondhand-risk change and check whether that correction stays gone.

## What changed in how I use AI

Named workflows were 38% of calls (44% of tokens) in the week of 2026-07-06 and 40% of calls (46% of tokens) in the week of 2026-07-13. Lookups went from 12% to 20% of calls, and the second week added capture at 20%. The first week used process-inbox, meeting-closeout, and weekly-update once each; the second used meeting-closeout and process-inbox once each. Calls came mostly from the editor panel (11 of 13), with 2 from the terminal.

## Where the effort went: corrections

Real correction calls: 4 of 13 calls (31%) from 4 distinct turns. One more labeled correction was a subagent result returning to the session, which is not my correction and is excluded. Per PM message: 3 of 7 (43%) in the week of 2026-07-06 and 1 of 5 (20%) in the week of 2026-07-13; coverage was 100% both weeks, so every message carried a label.

Themes:

- **Missed source** (2 turns): an export and a capture file left out of a pass.
- **Fact stated too strongly** (1 turn): a secondhand risk written as a fact.
- **Template drift** (1 turn): a weekly update that did not keep last week's layout.

## What it produced

- Decisions: 2 on file, one per week.
- To-dos created: 3 (2 in the first week, 1 in the second); 1 of 3 done.
- Commitments, evidence, and initiatives: no rows in this fixture.

## What the kit changed in response

From [fixtures/usage-story/state/kit-changes.csv](fixtures/usage-story/state/kit-changes.csv):

- 2026-07-10: closeout marks a secondhand risk as unconfirmed. The week of 2026-07-13 had no "stated too strongly" correction. That is association, not causation, over 2 active days.
- 2026-07-15: process-inbox lists every inbox file it read and skipped. No after period yet; the missed-source correction on 2026-07-14 came before it.

## Cost

**Estimate from the price table, not billed spend.** The fixture's 13 calls used 833,000 tokens on one model. At the list rates in [reference/pricing/model-prices.csv](reference/pricing/model-prices.csv) for `claude-sonnet-4-5-20250929` (read as dollars per million tokens), the estimate is about $1.14 for both weeks. A live story replaces this with the displayed figure from the PM's internal cost dashboard, and that figure stays in the live workspace.

## What we cannot claim yet

- That the kit changes caused the drop in corrections: 2 active days in a partial week is too short, and the change in the 2026-07-15 row has no after period.
- Anything about time saved: the rows carry tokens and timestamps, not effort.
- That the to-dos and decisions came from AI work alone: the registers do not record which session wrote a row.

## Next run should check

- A full week after the 2026-07-15 change: does the missed-source theme shrink?
- Whether lookups keep rising and what they are for.
- Whether coverage stays at 100% as the row count grows.

## Sources

- [fixtures/usage-story/data.md](fixtures/usage-story/data.md) — saved output of `usage_story.py data` on this fixture
- [fixtures/usage-story/state/usage-history.csv](fixtures/usage-story/state/usage-history.csv) — fictional usage rows
- [fixtures/usage-story/registers/decisions.csv](fixtures/usage-story/registers/decisions.csv), [fixtures/usage-story/registers/todos.csv](fixtures/usage-story/registers/todos.csv) — fictional registers
- [fixtures/usage-story/state/kit-changes.csv](fixtures/usage-story/state/kit-changes.csv) — fictional kit changes
- [reference/pricing/model-prices.csv](reference/pricing/model-prices.csv) — public list prices used for the cost estimate
