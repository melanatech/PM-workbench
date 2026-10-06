# BACKLOG.md — defects and improvements for the workbench itself

The system needs its own product management. One line per item; move to EVOLVING.md's changelog when done. Add here whenever a workflow annoys you, breaks, over-asks for approval, or misses something — that friction log is what makes month-3 tuning real instead of guesswork.

## Known open items (from reviews, not yet built)
- [x] First-run live workspace bootstrap (`scripts/create_live_workspace.py` + `NEW-USER-SETUP.md`); scheduled wrapper uses `--permission-mode dontAsk` (Claude Code 2.1+ rejects `--permission-prompts`)
- [ ] Validate an approved browser read path against real chat/dashboard sources (not tested end-to-end yet); use `npx --yes @playwright/mcp@latest` in live `.mcp.json`, not `npm install -g`
- [x] Competitive-scan URL discovery on Bedrock: `scripts/web_search.py` (client-side) — native Claude WebSearch stays unsupported on Bedrock; do not re-open as "ask PM for URLs"
- [ ] Optional: wire the same `web_search.py` fallback into other WebSearch-heavy agents if Bedrock errors show up there
- [x] `extract_document.sh` implemented (textutil + pdftotext/PDFKit); process-inbox prefers it and fails fast on exit 2/3
- [ ] Implement and test the manual-fallback replacements for `log_metrics.py` and `render_template.py` when a real use case warrants them
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
-

- [x] 2026-10-05 process-inbox: unreadable sensitivity-labelled .docx re-exported and processed; extractor now kit-owned (PDFKit path included). Encrypted Office files still need human re-export.
