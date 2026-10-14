# Context manifest

Which living-context files the kit expects, how fresh they should be, and which
workflows read them. `scripts/context_health.py` parses the table below.
`/brief context-setup` is how a new workspace fills the blanks.

`freshness_days` is the staleness threshold. `0` means stable: the health
check reports missing or template-empty, and does not flag age. A file is
template-empty when it still says `status: template`, or when every bullet is
still a bracket placeholder.

Personal identity (role, machine, tools) belongs in `.claude/CLAUDE.local.md`
(gitignored), not in tracked `CLAUDE.md`. Company check-in cadences stay in
that local file too. This manifest does not add a second OKR file:
`kr-metric-map.md` is the OKR context.

| id | path | need | freshness_days | workflows | purpose |
|---|---|---|---|---|---|
| current-priorities | reference/context/current-priorities.md | optional | 7 | daily-brief;weekly-update;strategy-refresh;competitive-scan;meeting-closeout;context-reconcile;return-brief | This week's priorities, leadership pressure, and top risks |
| assumptions | reference/context/assumptions-and-open-questions.md | optional | 0 | meeting-closeout;context-reconcile;ripple-check | Open questions and unresolved conflicts. An empty Open section is valid |
| glossary | reference/context/glossary.md | optional | 0 |  | Standing acronyms for chat. Not metric definitions |
| workspace-aliases | reference/context/workspace-aliases.md | optional | 0 |  | Name the PM uses, mapped to a path, before guessing a file |
| people | reference/context/people.md | optional | 30 | meeting-closeout;meeting-prep;context-reconcile;prd-package | People, roles, decision rights, and recurring concerns, with dated sources |
| systems-map | reference/context/systems-map.md | optional | 0 | jira-reconcile;context-setup | Ticket key prefixes, what each project holds, which repo maps to which project, wiki spaces, and chat channels |
| audiences | reference/context/audiences.md | optional | 30 | weekly-update;explore-brief;prd-package;launch-package | Who reads each recurring output, what they care about, format, channel, and which systems they can open |
| writing-style | reference/context/writing-style.md | optional | 0 | weekly-update;context-setup | Two or three real examples of how the PM writes |
| product-areas | reference/context/product-areas.md | optional | 30 | strategy-refresh;explore-brief;prd-package;roadmap-update | Product areas and surfaces with their owners |
| kr-metric-map | reference/metric-definitions/kr-metric-map.md | optional | 30 | okr-refresh;daily-brief;weekly-update;strategy-refresh | Which already-calculated metric each key result uses. The OKR context file |
| identity | .claude/CLAUDE.local.md | optional | 0 | context-setup | Personal role and environment. Missing when the file has not been created |
