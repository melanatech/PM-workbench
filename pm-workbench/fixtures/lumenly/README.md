# Fixture: Lumenly — Manager Scorecards

A small, fictional workspace state you can run any command against and know what the right answer looks like. Same material the training course uses, so the course and the real kit are checkable against each other.

**What's in it**
- `inbox/meetings/2026-07-14-roadmap-review.txt` — a meeting transcript with one decision, one commitment, one secondhand risk
- `inbox/exports/jira-board-export.csv` — four tickets; LUM-423 contradicts the meeting decision; LUM-437 is unassigned and stale
- `inbox/exports/slack-search-export.txt`, `inbox/exports/support-case-8841.txt` — three reports of silent export failures across two accounts
- `inbox/captures/capture-2026-07-16.md` — a hallway estimate (2 → maybe 3 weeks), unconfirmed
- `registers/evidence.csv` (EV-211), `registers/risks.csv` (RISK-008) — two rows already on file
- `roadmap/roadmap.csv`, `reference/context/current-priorities.md`

**Safest: load it into a separate workbench copy.** This copies the kit's
versioned logic, excludes root-level working data/raw captures, and loads the
fictional fixture in the new folder:
```
python3 scripts/load_fixture.py lumenly --isolate /tmp/pm-workbench-lumenly
cd /tmp/pm-workbench-lumenly
```
Open that folder in Claude Code before running any slash command. The source
workbench is not modified. When finished, remove only the isolated directory
you selected, after confirming its exact path; the loader does not clean it up.

Loading directly into the current workbench is also supported, but is
all-or-nothing: the loader first checks every fixture target, then refuses the
entire load if any existing file differs. Preview with
`python3 scripts/load_fixture.py lumenly --dry-run`. `--overwrite` replaces
conflicting target files and is intended only for disposable/fictitious data;
it can replace an inbox file or context file, so do not use it against real
work.

**Then run a command and check the run** from the isolated or explicitly loaded
workbench root:
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
