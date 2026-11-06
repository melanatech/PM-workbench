# Fixture: sample usage story

A fictional two-week usage story you can copy as the shape for `outputs/usage/[date]-story.md` (the monthly usage story in `.claude/workflows/workbench-health.md`). Every number is fictional and comes from the files in this folder. None of it is measured usage.

**What's in it**
- `state/usage-history.csv` — 13 fictional usage rows in the `session_usage.py` column layout, one of them a subagent result
- `registers/decisions.csv`, `registers/todos.csv` — fictional outcome rows
- `state/kit-changes.csv` — two fictional kit changes
- `data.md` — saved output of `usage_story.py data` on this folder
- `sample-story.md` — the story, with the headings in workflow step 6
- `sample-story-number-ledger.md` — the number ledger; the cost section is a price-table estimate from `reference/pricing/model-prices.csv`

**Regenerate and check** (from the kit root):
```
python3 scripts/usage_story.py data --root fixtures/usage-story --since 2026-07-06 > fixtures/usage-story/data.md
python3 scripts/usage_story.py check --root fixtures/usage-story sample-story.md
python3 scripts/check_number_consistency.py --ledger fixtures/usage-story/sample-story-number-ledger.md fixtures/usage-story/sample-story.md
```

A live story uses the PM's own rows and may use the internal cost dashboard. Those figures and that link stay in the live workspace and are never copied here.
