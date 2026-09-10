# BACKLOG.md — defects and improvements for the workbench itself

The system needs its own product management. One line per item; move to EVOLVING.md's changelog when done. Add here whenever a workflow annoys you, breaks, over-asks for approval, or misses something — that friction log is what makes month-3 tuning real instead of guesswork.

## Known open items (from reviews, not yet built)
- [ ] Validate the browser bridge against real real chat/dashboard sources (nothing tested end-to-end yet)
- [ ] Implement log_metrics.py and extract_document.sh past stub state
- [ ] Decide backup home for registers/ (approved company storage — NOT git; see .gitignore)
- [ ] Design first formatted template (likely the leadership one-pager) in Word with Jinja2 tags -> reference/templates/formatted/ (~30 min, unlocks branded output for that deliverable)
- [ ] Run one real week of work with the hooks on; then `/workbench-health` and prune. (Fixture + checker now exist: `python3 scripts/load_fixture.py lumenly`, run a command, `python3 scripts/check_run.py`.)
- [ ] Verify `skillOverrides: name-only` applies to `.claude/commands/` files in your Claude Code version (docs describe it for skills; commands are merged into skills). If not, the core-six profile is harmless but inert — use `settings.core.json` instead.
- [ ] Baseline instrumentation: after ~3 weeks of run-log data, compare against pre-system time estimates

## Friction log (add as you go)
-
