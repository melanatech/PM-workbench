# START HERE — PM Workbench

PM Workbench is a set of Claude Code prompts, local scripts, and operating
guidance for capturing inputs, maintaining registers, and drafting work
products. The included command files are scaffolding; they do not connect to
company tools or prove that a workflow is reliable. Start with the fictional
fixture below, then use pasted or exported material until any real access path
has been approved and tested. See the readiness table before relying on a
workflow.

## First run: verify the kit with fictional data

The fixture is fictional. Keep it separate from real work: this command creates
a code-only copy in the path you choose, loads the fixture there, and leaves the
source workbench unchanged.
```
python3 scripts/load_fixture.py lumenly --isolate /tmp/pm-workbench-lumenly
cd /tmp/pm-workbench-lumenly
```
Open that isolated folder in Claude Code, then run:
```
/meeting-closeout inbox/meetings/2026-07-14-roadmap-review.txt
python3 scripts/check_run.py
```
`fixtures/lumenly/README.md` describes expected results. To discard the test,
remove only the isolated directory after checking its exact path. The checker
is a local heuristic, not proof that every fact is correct; its coverage and
limits are documented in `scripts/check_run.py`.

To exercise the safety checks without Claude Code or any external account:
```
python3 -m unittest discover -s tests -v
```

## What is ready, configurable, and still a stub

| Status | What this means |
|---|---|
| **Ready to try locally** | `scripts/load_fixture.py`, `scripts/check_run.py`, and the safety tests are runnable local tools. `/quick-close` and `/meeting-closeout` are prompts for pasted notes or local files; they still require Claude Code and have not been verified end-to-end against a real workspace. The other command prompts and `prototype-build` skill are present, but many depend on populated data or external sources. |
| **Needs your configuration** | Real company context, templates, saved views, browser access, and scheduled runs require your tools, URLs, permissions, and policy review. Nothing here is connected to a real company system by default. Browser paths described in SETUP.md are options to test, not verified integrations. |
| **Requires an approved destination** | `scripts/snapshot-state.sh` creates a local copy only after `PM_STATE_BACKUP` is set to an approved, access-controlled, non-Git location. It does not encrypt or upload the snapshot. |
| **Known script stubs** | `scripts/log_metrics.py`, `scripts/extract_document.sh`, and `scripts/render_template.py` intentionally exit as stubs. Use the documented manual/markdown fallbacks until each needed implementation is tested. |
| **Not yet verified** | Browser reads, hook behavior in your Claude Code version, scheduled runs, and any external-system write path. Do not treat examples or allow-lists as evidence that an integration works or is approved. |

`Run PM Workflow.command`, `Capture Clipboard.command`, and scheduling are
optional convenience paths; test them locally before relying on them. See
SETUP.md and SCHEDULING.md for prerequisites and limitations.

## Files to read, in order
1. **SETUP.md** — optional local capture and external-access paths, permission examples, hooks, and their verification limits
2. **CLAUDE.md** — fill only brackets approved for this repository; keep private details in the ignored `.claude/CLAUDE.local.md`; review the rules and command menu
3. **SCHEDULING.md** — after 2-3 manual cycles per workflow
4. **SKILLS.md** — the later upgrade path
5. **AGENTS.md** — where and why subagents are used (isolated review panels + heavy-read isolation), and which commands deliberately stay plain
6. **CONNECTIONS.md** — the full write/read map: what every command feeds and cross-checks against
7. **SOURCE-POLICY.md** — who wins when Jira, Confluence, Slack, and code disagree (short; worth reading early)
8. **EVOLVING.md** + **BACKLOG.md** — read before adding or changing anything; the system's own changelog and friction log

## Using the prompt kit
Open the folder in a Claude Code-supported environment after verifying that
your installed version recognizes the project's `.claude/commands/` and
settings. Cursor is one possible interface; its extension and command behavior
are not verified by this kit. Review proposed local changes before using them.

Also available:
- **"Run PM Workflow.command"** and **"Capture Clipboard.command"** — optional scripts; verify on your OS and review where they write before use.
- **Scheduled runs** — an optional future setup. Scheduling is not configured or verified; see `SCHEDULING.md` and BACKLOG.md before considering it.

## Every duty → its workflow
| Duty | Workflow(s) |
|---|---|
| Learning platform/flows/data | `/learn-product-flow` + `/code-dive` |
| Discovery → documented strategy input | `/discovery` (chat/support/behavior-analytics + user research docs, in parallel) |
| Finding & recruiting users | `/research-plan` (dashboards/behavior analytics/Jira + existing persona/research docs — produces criteria and questions, never a list of people) |
| PRDs + leadership/tech buy-in | `/prd-package` (grounded context → readiness gate → draft → bounded stakeholder pre-review: 1–2 angles in Standard, all five in Deep → prototype reconciliation) |
| Prototypes + testing | `/prototype-build` (same bounded review + real browser QA + PRD reconciliation) + `/research-package`; `/prd-prototype-sync` anytime the two need a manual re-check |
| OKR gathering/monitoring/reporting | `/okr-refresh` (retrieves already-calculated dashboard values, logs and validates freshness, drafts 3 destinations — never recomputes a metric itself) |
| Docs, release notes, launch coordination | `/launch-package` (drift report first, then all audience docs) |
| Experiments | `/experiment-package` (adversarial gate) + `/experiment-analyze` |
| Meeting summaries | `/meeting-closeout` (feeds the registers — the keystone habit) |
| Competitive intelligence | `/competitive-scan` (dated diffs, monthly) |
| Weekly leadership updates | `/weekly-update` (generated from registers) |
| Strategy/innovation/revenue docs | `/strategy-refresh` (change report first; revenue ideas get real models) |
| Week one back | `/return-brief` (one-time) |
| Is the system itself working for me | `/workbench-health` (reads the run log; proposes pruning) |

## Before using real data

The command files are workflow prompts, not tested integrations. Read
`CLAUDE.md`; add only information approved for this repository. It is
version-controlled. Keep sensitive local context in the ignored
`.claude/CLAUDE.local.md` file. Use pasted or exported material until each
external read path has been tested and approved. A prompt may ask
for missing information, but that does not make its browser, dashboard,
document-extraction, metric-logging, or scheduled path operational. Use
`BACKLOG.md` for known gaps and unverified behavior. Do not schedule workflows
until they have completed several reviewed manual runs on approved sources.

## Evidence and run logging
The `log_run.py` hook is configured to append a run-log row, but hooks fail open
and are not verified in your Claude Code installation. Check `logs/run-log.csv`
after a run; if the row is missing, log it manually or investigate the hook.
Use `outputs/receipts.md` only if useful for recording outcomes and review
effort; do not treat incomplete logs as measured reliability or time saved.

## Operating policy and limits
The intended policy is to require approval before external writes, avoid editing
raw captures, and cite sources. These are instructions, not technical
guarantees; verify the effective settings and review actions. Browser reads,
scheduled runs, metric logging, and document extraction are not verified
integrations. The checker and hooks are fallible and may fail open.
