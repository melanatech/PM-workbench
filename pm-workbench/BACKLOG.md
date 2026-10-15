# BACKLOG.md — defects and improvements for the workbench itself

The system needs its own product management. One line per item; move to EVOLVING.md's changelog when done. Add here whenever a workflow annoys you, breaks, over-asks for approval, or misses something — that friction log is what makes month-3 tuning real instead of guesswork.

## Known open items (from reviews, not yet built)
- [x] **Plan 8:** Lumenly isolate smoke of `/brief daily-brief` and `/capture meeting-closeout` against the lean CLAUDE.md. Completed 2026-10-14 (fixture score found 1, missed 0, invented 0).
- [x] **Session token usage mining (phase 1):** `scripts/session_usage.py` L0–L2a `--backfill` → `state/usage-history.csv`; `workbench_metrics` Session tokens info rows; docs in `workbench-metrics.md`; monthly-review surfaces them. Claude Code / pm-live only.
- [ ] **Session usage L2b polish:** exercise `--classify` once via `claude -p` (existing login); optional scheduled `--backfill` (no classify) after a week of use. Still never invent "tokens saved."
- [x] **Shared prototype package** (`prototypes/_shared/` + npm `file:` deps): convention in `reference/design/shared-prototype-package.md`; soft catalog keeps unpromoted pieces. Live package is created in `~/pm-live` (not kit git).
- [x] First-run live workspace bootstrap (`scripts/create_live_workspace.py` + `NEW-USER-SETUP.md`); scheduled wrapper uses `--permission-mode dontAsk` (Claude Code 2.1+ rejects `--permission-prompts`)
- [ ] Validate an approved browser read path against real chat/dashboard sources (not tested end-to-end yet); use `npx --yes @playwright/mcp@latest` in live `.mcp.json`, not `npm install -g`
- [x] Competitive-scan URL discovery on Bedrock: `scripts/web_search.py` (client-side) — native Claude WebSearch stays unsupported on Bedrock; do not re-open as "ask PM for URLs"
- [x] First-class web search: `_web-search.md` recipe, `state/web-search/`, fan-out + `web-search` index kind, skill; explore-brief / prd-package search problems · market/category · users · solutions
- [x] `extract_document.sh` implemented (textutil + pdftotext/PDFKit + `.xlsx`/`.xlsm` via `extract_xlsx.py`); process-inbox prefers it and fails fast on exit 2/3
- [x] `render_template.py` writes HTML and Word (`.docx`) with the standard library (2026-10-14). Excel and PowerPoint still exit with a message; a branded Word template in `reference/templates/formatted/` stays optional
- [ ] `log_metrics.py` is still a stub — append `state/okr-history.csv` by hand until a real use case warrants the script
- [ ] Confirm an approved, access-controlled company backup destination for registers/context/logs; until then leave snapshots unconfigured (never Git)
- [ ] Verify slash commands end-to-end in the Claude Code panel from `~/pm-live` after `/login` (Cursor Agent shell proxy can block `claude -p` even when the panel works)
- [ ] Design first formatted template (likely the leadership one-pager) in Word with Jinja2 tags -> reference/templates/formatted/ (~30 min, unlocks branded output for that deliverable)
- [ ] After the local fixture and safety tests pass, run one reviewed real week with approved inputs and verified hooks; then `/report workbench-health` and prune. Browser reads and scheduled runs remain unverified.
- [ ] Verify `skillOverrides: name-only` applies to `.claude/commands/` files in your Claude Code version (docs describe it for skills; commands are merged into skills). If not, the core-six profile is harmless but inert — use `settings.core.json` instead.
- [ ] Verify `/todo` in a live Claude Code session: the name does not collide with a built-in; the sonnet `todo-worker` subagent runs on sonnet (frontmatter `model:` honored) while `/todo` runs on haiku; `name-only` works on commands; run the Lumenly `/todo` checks in the fixture README.
- [ ] `/sync rotate-registers` conflicts with the register hook: it archives rows out of current-state registers, but the hook blocks any write that loses rows (CLAUDE.md rule 7). Decide: allow rotation for specific registers, or make rotation a script that runs outside the hook. Check before rotating `todos.csv`.
- [ ] Verify `/insights` exists in your Claude Code version before planning the evaluation work (Plan C) around it.
- [ ] Plan D first-run checks: `python3 scripts/run_scheduled.py daily-brief` by hand. Confirm `claude -p` expands the slash command, the router hands work to the `workflow-runner` subagent, the run log and `logs/scheduled-runs.csv` get rows, and nothing is denied that should not be (add exactly that tool to `ALLOWED_TOOLS` or `.claude/settings.json`). Then try `inbox-watch --if-new-inbox`, `todo-sweep`, and `state/PAUSE`.
- [ ] In an open session, run `/loop 20m` once and confirm it can invoke `/capture` and `/todo` (they are name-only in settings.json); if not, name the workflows in `.claude/loop.md`.
- [ ] After a week of scheduled runs, read `logs/scheduled-runs.csv` and the sweep drafts: keep only the routines you actually read.
- [ ] After the first scheduled monthly review: confirm `/report monthly-review` runs unattended, fill `logs/review-notes.csv` once by hand (date,metric,value,note), and decide whether any metric is noise and should go.
- [ ] Run `python3 scripts/score_fixture.py --root <isolated workspace>` after a real `/capture meeting-closeout` fixture run and record the result.
- [ ] Baseline instrumentation: after ~3 weeks of run-log data, compare against pre-system time estimates

## Friction log (add as you go)

- [x] 2026-10-05 process-inbox: unreadable sensitivity-labelled .docx re-exported and processed; extractor now kit-owned (PDFKit path included). Encrypted Office files still need human re-export.
- [ ] 2026-10-15 process-inbox: scripts/extract_document.sh exits 0 but returns almost nothing for JS-rendered HTML (data held in an inline script; Commerce 2027 OKRs Oct12). Consider extracting inline-script data or warning on near-empty output.
- [x] 2026-10-15 kit: company OKRs skipped as "business-level" — fixed via `strategy-frame` + `_source-triage.md`; guarded by `tests/test_source_triage_rules.py::test_business_level_is_forbidden_skip_reason` and `tests/test_fanout_route.py` strategy-frame routes.
- [x] 2026-10-15 kit: definitions / semantic work only routable as glossary terms — fixed via `semantic-definition` type; guarded by fanout route + triage rules tests.
- [x] 2026-10-15 kit: exploratory "things to think about" logged as EV-107..110 and triggered owner/decision questions — fixed via exploratory-thinking hold (no EV/DEC/COM); guarded by `test_exploratory_thinking_forbids_ev_and_owner_questions` and `test_parked_marker_honored`.
- [x] 2026-10-15 kit: ordinary phrases ("end-to-end evals", "Airo supported features matrix") added to glossary — fixed via acronyms-only rule; guarded by `test_glossary_limited_to_acronyms`.
- [x] 2026-10-15 kit: process-inbox / propose queued "confirm/decide/what does X mean" as to-dos — fixed via action-only filter in `todo-worker` propose + meeting-closeout / process-inbox / context-reconcile; guarded by `tests/test_todo_propose_rules.py`.

