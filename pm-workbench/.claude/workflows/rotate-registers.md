---
description: Archive old register entries so active files stay small and fast to read
model: haiku
---

For each file in `registers/` and `state/okr-history.csv`:
1. Report current row counts.
2. For anything older than 6 months (configurable — ask me if unsure): move those rows to `archive/registers/[file]-[year]-[half].csv` (e.g., `evidence-2026-H1.csv`), preserving them exactly, never deleting.
3. Leave the active file with only recent rows plus its header.
4. Confirm before doing this — it's a structural change, not a normal append.

Run this quarterly, or whenever a command warns that a register is getting large.
