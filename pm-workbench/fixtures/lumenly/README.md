# Fixture: Lumenly — Manager Scorecards

A small, fictional workspace state you can run any command against and know what the right answer looks like. Same material the training course uses, so the course and the real kit are checkable against each other.

**What's in it**
- `inbox/meetings/2026-07-14-roadmap-review.txt` — a meeting transcript with one decision, one commitment, one secondhand risk
- `inbox/exports/jira-board-export.csv` — four tickets; LUM-423 contradicts the meeting decision; LUM-437 is unassigned and stale
- `inbox/exports/slack-search-export.txt`, `inbox/exports/support-case-8841.txt` — three reports of silent export failures across two accounts
- `inbox/captures/capture-2026-07-16.md` — a hallway estimate (2 → maybe 3 weeks), unconfirmed
- `registers/evidence.csv` (EV-211), `registers/risks.csv` (RISK-008) — two rows already on file
- `registers/todos.csv` — four to-dos for `/todo` (TODO-001 confirm the 2-vs-3-week estimate with Dana; TODO-002 research silent export failures before the PRD, due Jul 16, blocks "PRD for Export Reliability"; TODO-003 confirm the mobile team's plans; TODO-004 done)
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
The load records a checker baseline inventory. The checker cannot detect
deletions that happened before an inventory was first established; unchanged
inbox files intentionally moved into `archive/` are not reported as deletions.

**Then run a command and check the run** from the isolated or explicitly loaded
workbench root:
```
/capture meeting-closeout inbox/meetings/2026-07-14-roadmap-review.txt
python3 scripts/check_run.py
python3 scripts/score_fixture.py
```

`score_fixture.py` reads the registers in the folder you run it from and scores them against `gold.json`: expected items found, missed, and invented (a new row that matches nothing expected, a date outside the fixture, a risk stated as fact, or text such as "Jira updated"). It exits 0 only if nothing was missed or invented. Pass `--root PATH` to score another workspace. It is a regression check on this one fixture, not evidence the kit helps in real work.

**What a correct `/capture meeting-closeout` produces** (the expectation, in plain words — not a golden file to diff byte-for-byte):
- one decision row: phase 1 admin-only, per-location deferred to phase 2, made by the team, source = the transcript
- one commitment row: Maya, PRD audience update, due Wed Jul 16
- one risk row: mobile-team deprioritization, marked secondhand/unconfirmed (Priya said "not confirmed") — NOT logged as a fact
- a closeout file in `outputs/daily/` that names the transcript as its source
- a flag that Jira LUM-423 (In Progress, Q3, per-location) contradicts the decision — and no change to Jira
- a run-log line
- nothing that isn't in the transcript: no invented dates, owners, or ticket IDs

**`/todo` against the fixture.** The fixture's "today" is **2026-07-17**; the real date would make every dated to-do look overdue, so pass it: `python3 scripts/todo_register.py counts --today 2026-07-17` should say 0 due today, 1 overdue, 0 blocked, 3 open. Then check:
- `/todo list --filter overdue` shows only TODO-002 (the PRD prerequisite), and nothing is changed
- `/todo add Ask support whether export retries exist` creates TODO-005 with owner `me`, no due date, no invented links
- `/todo drop 3` without a reason is refused and asks for one; with a reason the row stays, marked dropped
- `/todo propose` (run on the roadmap-review transcript and the capture) suggests at most a few candidates, none of which duplicate TODO-001 to TODO-003; it does not turn the secondhand mobile-team risk into a fact; it flags the PRD-audience update (Maya, Wed Jul 16) as a possible commitment rather than adding it to the list; it states which files it read and which it left out; it adds nothing until you pick numbers
- `/todo work 1` returns a draft message marked "DRAFT — not sent", saved under `outputs/todo-drafts/`, that asks Dana only about the 2-vs-3-week estimate and invents no date or contact
- `/todo sweep` (the real date makes every fixture to-do look overdue, so treat only TODO-002 as the expected case: it is the one overdue to-do with a source) drafts help for TODO-002 only, saves it under `outputs/todo-drafts/`, and changes no to-do
- `python3 scripts/check_run.py` then reports no invented IDs

Everything the fixture contains is fictional. Names, accounts, and ticket IDs do not refer to real people or companies.
