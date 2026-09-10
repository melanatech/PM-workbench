# Fixture: Lumenly — Manager Scorecards

A small, fictional workspace state you can run any command against and know what the right answer looks like. Same material the training course uses, so the course and the real kit are checkable against each other.

**What's in it**
- `inbox/meetings/2026-07-14-roadmap-review.txt` — a meeting transcript with one decision, one commitment, one secondhand risk
- `inbox/exports/jira-board-export.csv` — four tickets; LUM-423 contradicts the meeting decision; LUM-437 is unassigned and stale
- `inbox/exports/slack-search-export.txt`, `inbox/exports/support-case-8841.txt` — three reports of silent export failures across two accounts
- `inbox/captures/capture-2026-07-16.md` — a hallway estimate (2 → maybe 3 weeks), unconfirmed
- `registers/evidence.csv` (EV-211), `registers/risks.csv` (RISK-008) — two rows already on file
- `roadmap/roadmap.csv`, `reference/context/current-priorities.md`

**Load it** (copies into the live folders; refuses to overwrite non-empty registers unless `--force`):
```
python3 scripts/load_fixture.py lumenly
```

**Then run a command and check the run:**
```
/meeting-closeout inbox/meetings/2026-07-14-roadmap-review.txt
python3 scripts/check_run.py
```

**What a correct `/meeting-closeout` produces** (the expectation, in plain words — not a golden file to diff byte-for-byte):
- one decision row: phase 1 admin-only, per-location deferred to phase 2, made by the team, source = the transcript
- one commitment row: Maya, PRD audience update, due Wed Jul 16
- one risk row: mobile-team deprioritization, marked secondhand/unconfirmed (Priya said "not confirmed") — NOT logged as a fact
- a closeout file in `outputs/daily/` that names the transcript as its source
- a flag that Jira LUM-423 (In Progress, Q3, per-location) contradicts the decision — and no change to Jira
- a run-log line
- nothing that isn't in the transcript: no invented dates, owners, or ticket IDs

Everything the fixture contains is fictional. Names, accounts, and ticket IDs do not refer to real people or companies.
