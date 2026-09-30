# BACKLOG.md — defects and improvements for the workbench itself

The system needs its own product management. One line per item; move to EVOLVING.md's changelog when done. Add here whenever a workflow annoys you, breaks, over-asks for approval, or misses something — that friction log is what makes month-3 tuning real instead of guesswork.

## Known open items (from reviews, not yet built)
- [ ] Validate an approved browser read path against real chat/dashboard sources (not tested end-to-end yet)
- [ ] Implement and test the manual-fallback replacements for `log_metrics.py`, `extract_document.sh`, and `render_template.py` when a real use case warrants them
- [ ] Confirm an approved, access-controlled company backup destination for registers/context/logs; until then leave snapshots unconfigured (never Git)
- [ ] Design first formatted template (likely the leadership one-pager) in Word with Jinja2 tags -> reference/templates/formatted/ (~30 min, unlocks branded output for that deliverable)
- [ ] After the local fixture and safety tests pass, run one reviewed real week with approved inputs and verified hooks; then `/workbench-health` and prune. Browser reads and scheduled runs remain unverified.
- [ ] Verify `skillOverrides: name-only` applies to `.claude/commands/` files in your Claude Code version (docs describe it for skills; commands are merged into skills). If not, the core-six profile is harmless but inert — use `settings.core.json` instead.
- [ ] Baseline instrumentation: after ~3 weeks of run-log data, compare against pre-system time estimates

## Friction log (add as you go)
-
