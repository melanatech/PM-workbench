# Number ledger — sample usage story (fixture)

Artifact: [fixtures/usage-story/sample-story.md](fixtures/usage-story/sample-story.md). All numbers are fictional fixture values. Run from the kit root:

```
python3 scripts/check_number_consistency.py --ledger fixtures/usage-story/sample-story-number-ledger.md fixtures/usage-story/sample-story.md
```

## Gate sources

- fixtures/usage-story/data.md
- fixtures/usage-story/state/usage-history.csv
- reference/pricing/model-prices.csv

## Numbers from data.md (unit named)

| Number | Meaning | Unit / denominator |
|---|---|---|
| 13 | calls in the fixture | calls |
| 5 | sessions; also active days across both weeks | sessions / days |
| 3, 2 | active days, week of 2026-07-06 and week of 2026-07-13 (partial) | days |
| 38% / 44% | named workflows, week of 2026-07-06 | share of calls / share of tokens |
| 40% / 46% | named workflows, week of 2026-07-13 | share of calls / share of tokens |
| 12%, 20% | lookups by week | share of calls |
| 20% | capture, week of 2026-07-13 | share of calls |
| 11, 2 | panel and terminal calls | of 13 calls |
| 4 of 13 (31%) | real correction calls | of all calls |
| 3 of 7 (43%) | corrections, week of 2026-07-06 | of PM messages, not calls |
| 1 of 5 (20%) | corrections, week of 2026-07-13 | of PM messages, not calls |
| 100% | label coverage both weeks | of PM messages |
| 2 | decisions on file | rows |
| 3, 1 | to-dos created; done | rows |

The call-based correction share (31%) and the message-based shares (43%, 20%) are different units; the story names the unit next to each.

## Cost estimate (arithmetic, not a saved result)

Token sums over fixture rows: input 140,000; output 23,000; cache write 50,000; cache read 620,000; total 833,000 tokens

Rates for `claude-sonnet-4-5-20250929` from reference/pricing/model-prices.csv: 3, 15, 3.75, 0.30 (dollars per million tokens).

140,000 × 3 = 0.42; 23,000 × 15 = 0.345; 50,000 × 3.75 = 0.1875; 620,000 × 0.30 = 0.186 (each ÷ 1,000,000). Sum 1.1385, shown as $1.14 (estimate only)
