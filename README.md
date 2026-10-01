# PM Workbench

An AI-assisted product management toolkit and interactive course for turning
meetings, evidence, and decisions into traceable work—not just more documents.

**[Take the course](https://melanatech.github.io/PM-workbench/)** ·
**[Read the essay](https://melanatech.github.io/PM-workbench/blog/ai-system-worked/)** ·
**[Start with the toolkit](pm-workbench/START%20HERE.md)**

## What this project is

PM Workbench is for product managers who need to keep source material, decisions,
commitments, risks, and deliverables consistent as work changes.

This repository contains two related but separate experiences:

| Experience | Use it for | What it does |
| --- | --- | --- |
| **Browser course** | Learn and practice without installing anything | Simulates workflows using the fictional Lumenly workspace, inspectable sources, outputs, and exercises. |
| **Claude Code toolkit** | Adapt the workflows to your own approved workspace | Provides command prompts, review agents, local scripts, templates, and operating guidance. It requires your own configuration and review. |

**Course actions are simulations.** They do not run Claude Code, access your
computer, or connect to Jira, Slack, dashboards, or other company systems. The
toolkit is not a preconfigured integration platform, and its prompts are not
proof that a workflow is reliable.

## Choose your starting point

### 1. Learn in the browser

Open the **[interactive course](https://melanatech.github.io/PM-workbench/)**.
No installation or company-system access is needed.

For the story behind the project, read
**[The AI System Worked Until I Took Myself Out of It](https://melanatech.github.io/PM-workbench/blog/ai-system-worked/)**.

### 2. Try the toolkit with fictional data

Start with a disposable workspace before using real material.

**Prerequisites**

- A local clone or downloaded copy of this repository.
- Python 3 for the helper scripts and safety tests; those use the standard library
  and require no additional Python packages.
- Claude Code for running the command prompts. Verify that your installed
  version recognizes the workbench's `.claude/commands/` and settings.

If you have Git installed, get a local copy with:

```sh
git clone https://github.com/melanatech/PM-workbench.git
cd PM-workbench
```

Alternatively, download and extract the repository ZIP from GitHub's **Code**
menu.

From the **repository root**, run the local safety tests:

```sh
python3 -m unittest discover -s pm-workbench/tests -v
```

Then create an isolated copy containing the fictional fixture:

```sh
python3 pm-workbench/scripts/load_fixture.py lumenly --isolate /tmp/pm-workbench-lumenly
cd /tmp/pm-workbench-lumenly
```

These examples use a macOS/Linux shell. On Windows, use your Python 3 launcher
(`python` or `py`) and choose a fresh absolute destination path instead of
`/tmp/pm-workbench-lumenly`.

The loader leaves the source workbench unchanged and refuses a non-empty
isolation destination. Open the **isolated folder** in Claude Code and run:

```text
/meeting-closeout inbox/meetings/2026-07-14-roadmap-review.txt
```

After reviewing the generated files, run this in a terminal from that same folder:

```sh
python3 scripts/check_run.py
```

Compare the result with the
[fixture's expected outcomes](pm-workbench/fixtures/lumenly/README.md).
The checker is a local heuristic, not a guarantee that every fact is correct.
When finished, remove only the isolated folder you selected after confirming its
exact path. Do not use fixture overwrite options against real work.

Continue with [START HERE](pm-workbench/START%20HERE.md) and
[SETUP](pm-workbench/SETUP.md) before adapting the toolkit.

## What is ready—and what is not

| Status | Scope |
| --- | --- |
| **Available now** | Static course and essay; local fixture loader, run checker, and safety tests; command and agent prompt files. |
| **Needs configuration and review** | Company context, templates, capture tools, external read paths, permissions, and scheduling. No real company systems are connected by default. |
| **Known stubs** | `log_metrics.py`, `extract_document.sh`, and `render_template.py`. Use the documented manual or Markdown fallbacks until the needed implementation is tested. |
| **Not verified end-to-end** | Browser reads against real sources, hooks in your Claude Code installation, scheduled workflows, and external-system writes. |

See the [readiness guidance](pm-workbench/START%20HERE.md#what-is-ready-configurable-and-still-a-stub)
and [known gaps](pm-workbench/BACKLOG.md). Passing the local tests does not verify
Claude Code execution or external integrations.

## Repository map

```text
docs/                         Published static course and essay
  index.html                  Interactive course
  blog/ai-system-worked/       Standalone essay page
  assets/                     Course images
pm-workbench/                 Companion toolkit; open this folder for real use
  .claude/                    Commands, agents, hooks, settings, and skills
  fixtures/lumenly/           Fictional example inputs and expected outcomes
  reference/                  Context, source links, and template guidance
  scripts/                    Local utilities and clearly identified stubs
  tests/                      First-run safety and checker tests
index.html                    Repository-root entry page linking to the course
```

The GitHub Pages site is served from `docs/`; the toolkit is not the website.
There is no application build step for the static site.

## Preview the site locally

From the repository root:

```sh
python3 -m http.server 8000 --directory docs
```

Open `http://localhost:8000/` for the course or
`http://localhost:8000/blog/ai-system-worked/` for the essay. Stop the server with
Ctrl+C when finished.

## Use real data responsibly

- Follow your organization's rules for AI tools, browser access, extensions,
  storage, and customer data before connecting real sources.
- Do not commit credentials, raw captures, exports, registers, or sensitive
  company context. Some reference files are version-controlled; review
  `git status` and the proposed diff before every commit.
- Keep private local context in the ignored
  `pm-workbench/.claude/CLAUDE.local.md`, not in tracked instructions.
- Review sources and outputs. Require explicit approval before external writes;
  prompts, permission examples, and hooks are not security guarantees.
- Do not schedule a workflow until it has completed several reviewed manual
  runs. Hooks can fail open, so confirm the run log actually exists.
- Leave backups unconfigured until you have an approved, access-controlled,
  non-Git destination. See [backup and retention guidance](pm-workbench/STATE-BACKUP.md).

## Documentation

| Topic | Guide |
| --- | --- |
| Onboarding and workflow menu | [START HERE](pm-workbench/START%20HERE.md) |
| Context, capture, permissions, and hooks | [SETUP](pm-workbench/SETUP.md) |
| Operating rules | [CLAUDE.md](pm-workbench/CLAUDE.md) |
| Resolving conflicting sources | [SOURCE-POLICY](pm-workbench/SOURCE-POLICY.md) |
| How workflows share state | [CONNECTIONS](pm-workbench/CONNECTIONS.md) |
| Optional scheduling | [SCHEDULING](pm-workbench/SCHEDULING.md) |
| Design decisions and known gaps | [EVOLVING](pm-workbench/EVOLVING.md) · [BACKLOG](pm-workbench/BACKLOG.md) |

## Reporting issues and contributing

[Open a GitHub issue](https://github.com/melanatech/PM-workbench/issues) for a bug
or improvement. Include the relevant workflow, expected and actual behavior, and
steps to reproduce. Use fictional or redacted examples—never attach credentials
or sensitive working data.

For changes, keep pull requests focused, update the affected documentation, and
run the safety tests above. If changing the course, also check its links,
keyboard navigation, and mobile layout.

**License:** No license file is currently included. Ask the repository owner about
reuse or redistribution permissions rather than assuming a license.
