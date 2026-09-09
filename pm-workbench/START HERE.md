# START HERE — PM Workbench

One system, three moving parts: **capture** (browser automation, one-click clipboard, or dropped documents) → **process** (Claude turns raw material into structured registers and durable research summaries) → **generate** (updates, PRDs, reports produced from maintained state instead of your memory). The registers — decisions, commitments, risks, evidence, participants — are the connective tissue; meetings feed them, and everything you publish reads from them. **Internal documents** (SharePoint, other Confluence pages, Teams/Copilot meeting summaries, anything in the file browser) are a fourth input alongside Slack/Jira/QuickSight/FullStory — see SETUP.md and `reference/user-research/`. For anything durable-but-fetchable (templates, policy docs, dashboards), `reference/links.csv` is usually faster than saving a copy. And plenty of value needs no command at all — you can just ask questions directly ("what did we decide about X") and get answers read straight from the registers.

## Files to read, in order
1. **SETUP.md** — browser access (test `claude --chrome` first; Playwright fallback; clipboard-capture floor) + scoped permissions + bookmarked views
2. **CLAUDE.md** — fill in every bracket; the rules, context, AND the command menu (so plain-language requests route to the right workflow) every session inherits
3. **SCHEDULING.md** — after 2-3 manual cycles per workflow
4. **SKILLS.md** — the later upgrade path
5. **AGENTS.md** — where and why subagents are used (isolated review panels + heavy-read isolation), and which commands deliberately stay plain
6. **CONNECTIONS.md** — the full write/read map: what every command feeds and cross-checks against
7. **SOURCE-POLICY.md** — who wins when Jira, Confluence, Slack, and code disagree (short; worth reading early)
8. **EVOLVING.md** + **BACKLOG.md** — read before adding or changing anything; the system's own changelog and friction log

## Daily use — pick your interface (no terminal required)
**Recommended: Cursor as your cockpit.** Open the PM Workbench folder in Cursor and install the Claude Code extension (Extensions → "Claude Code", or run `claude` once in Cursor's built-in terminal and accept its offer to install). You get a chat panel in the sidebar: type `/meeting-closeout` or `/okr-refresh` like a chat message, watch it work, review changes as visual diffs, and click any output file in the file tree to read it. Everything in this kit works identically there, because the commands and rules live in the folder — not in any particular window.

Also available:
- **"Run PM Workflow.command"** — double-click, pick a number, done. (First open: right-click → Open to pass Gatekeeper.)
- **"Capture Clipboard.command"** — copy anything in Slack desktop/Outlook/wherever, double-click, pick a category. It's filed with a timestamp and processed at the nightly inbox run.
- **Scheduled runs** — no interface at all; results land in `outputs/` for you to read in Cursor like documents.

The command line only appears twice in your life: the one-time SETUP.md steps and the one-time SCHEDULING.md crontab paste — and for both, you can open the file in Cursor and ask the chat panel to run the steps for you.

## Every duty → its workflow
| Duty | Workflow(s) |
|---|---|
| Learning platform/flows/data | `/learn-product-flow` + `/code-dive` |
| Discovery → documented strategy input | `/discovery` (Slack/support/FullStory + user research docs, in parallel) |
| Finding & recruiting users | `/research-plan` (QuickSight/FullStory/Jira + existing persona/research docs — no CRM) |
| PRDs + leadership/tech buy-in | `/prd-package` (grounded context → readiness gate → draft → 5-angle stakeholder pre-review → prototype reconciliation) |
| Prototypes + testing | `/prototype-build` (same 5-angle review + PRD reconciliation) + `/research-package`; `/prd-prototype-sync` anytime the two need a manual re-check |
| OKR gathering/monitoring/reporting | `/okr-refresh` (retrieves already-calculated dashboard values, logs and validates freshness, drafts 3 destinations — never recomputes a metric itself) |
| Docs, release notes, launch coordination | `/launch-package` (drift report first, then all audience docs) |
| Experiments | `/experiment-package` (adversarial gate) + `/experiment-analyze` |
| Meeting summaries | `/meeting-closeout` (feeds the registers — the keystone habit) |
| Competitive intelligence | `/competitive-scan` (dated diffs, monthly) |
| Weekly leadership updates | `/weekly-update` (generated from registers) |
| Strategy/innovation/revenue docs | `/strategy-refresh` (change report first; revenue ideas get real models) |
| Week one back | `/return-brief` (one-time) |

## Day one: everything works. Setup happens while you work.

There is no ramp-up phase and nothing is deferred. All 22 commands are live the moment you install Claude Code and open this folder — use whichever one the day demands. What makes that possible: **every command self-configures on first use** (CLAUDE.md rule 17). The first time a command needs a dashboard URL, a Slack search, or a template it doesn't have, it asks you inline, finishes the real work with your answer, and saves it so it never asks again. Setup isn't a phase you complete before using the system — it's a side effect of the first week of actually using it.

**The only true one-time step:** the browser bridge test in SETUP.md (~15 min). Do it when you first need a command that browses (discovery, OKR, Jira views). Until then, every command runs on paste-ins and the clipboard capture — a labeled fallback, not a blocker.

**What "first run" looks like in practice:**
- `/weekly-update`, Friday of week one: registers are sparse, so it drafts from what exists, asks for the two things it's missing, and marks anything you skip as incomplete. Real update, out the door.
- `/okr-refresh`, first month-end: no metric YAMLs yet — it asks which metrics and where they live, does the run with your answers, and writes the YAMLs itself. Second run is automatic.
- `/prd-package`, whenever the first PRD is due: empty templates folder → it asks for one past PRD to match, uses it, saves it.
- `/quick-close` and `/meeting-closeout`: nothing to configure, ever.

**Tinker as you go** (this is where your "tweak and tinker" time goes, whenever it exists): fill CLAUDE.md brackets as you notice a wrong assumption, drop past PRDs/updates into templates when convenient, wire SCHEDULING.md once a command has run manually enough times to be boring, and log every annoyance in BACKLOG.md — that friction log is what makes the tinkering targeted instead of guesswork. None of it gates anything.

## The receipts log (do not skip this)
Keep `outputs/receipts.md`, one entry per week: outcomes influenced, decisions accelerated, risks surfaced before impact, insights generated, hours of recurring work eliminated, and the acceptance rate of Claude's proposed changes (how often you accept vs. correct — it's both your quality check on the system and your evidence that your judgment is the driver). This is your performance-review evidence, framed as business impact rather than "I used AI a lot." And say it out loud in your first 1:1 back: the always-current board and on-time updates are a system you built. Don't let it be invisible.

## What Claude will never do here
Send, submit, publish, or change any external system without your explicit approval in the moment. Scheduled runs are mechanically blocked from clicking/typing in the browser at all. OKR metric values are retrieved from what the dashboard already calculated, logged and freshness-checked — never recomputed by the model. Raw captures are never edited. Sources are always cited. When something fails (SSO expired, Chrome closed), it says so plainly instead of improvising.
