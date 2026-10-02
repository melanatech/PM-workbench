# SETUP.md — optional setup for local capture, browser reads, and templates

Start with fictional data and pasted/local inputs; do not connect real sources
until you have checked company policy and verified the access path. Part 0 is
optional context calibration. Browser access, hooks, scheduling, and template
conversion are separate setup items, not verified capabilities.

## Part 0: Give it context (do this first — ~10 minutes)

This is optional context calibration. Do not add raw or sensitive company
documents, internal links, or past deliverables to a version-controlled folder
unless company policy explicitly permits it; use redacted/approved examples.

1. **Open `CLAUDE.md` and fill only the brackets approved for this repository** in "Who I am." It is version-controlled; put sensitive or private details in the ignored `.claude/CLAUDE.local.md` file instead.
2. **Seed `reference/links.csv`** with a few approved links you reference constantly. Internal URLs may themselves be sensitive; keep them out of version control unless permitted.
3. **Add approved or redacted past PRDs/updates** to `reference/templates/` only if policy permits. Otherwise skip this; use a sanitized example or paste content for an individual session.

That's it — not a checklist to finish, just the fastest way to make week-one output feel calibrated instead of generic.

## Part 1: Browser access — three jobs, three tools, in this order

Your organization may restrict extensions, browser automation, package
installation, or access to company systems. Follow its approval process. This
kit does not establish or verify approval for any integration.

**Job A — optional manual capture.** If permitted, install the included **Workbench Clipper** from `tools/workbench-clipper/`, then test it with non-sensitive content and verify where the file is saved. It is intended to store page text, URL, title, and timestamp in `Downloads/pm-workbench-inbox/`; `/capture process-inbox` is a prompt, not an automatic importer unless its local workflow is run. If extensions are unavailable, `Capture Clipboard.command` or pasting into the chat are alternatives; review the resulting files because captures may contain sensitive information.

**Job B — letting Claude read pages for you (discovery scans, OKR pulls, Jira views).** If permitted, test Anthropic's **Claude in Chrome** integration by following its current installation instructions, then ask Claude Code to read the open tab without interacting with it. Availability, supported browsers, account requirements, and organizational policy can change; verify these before use. This workbench has not tested this path against a real company source.

**Job C — optional fallback: Playwright MCP over a debug Chrome profile.** This path adds plumbing (a Chrome profile that must be open, an SSO that expires, and a deny list you keep current). Use it only if permitted and after reviewing the risks.
```
npm install -g @playwright/mcp        # needs Node.js
```
Launch a dedicated automation Chrome profile (save as a shortcut — this window open = Claude can read):
```
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222 --user-data-dir="$HOME/chrome-claude-profile"
# Windows (PowerShell)
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="$env:USERPROFILE\chrome-claude-profile"
```
Log into your tools once in that window. Register in this project's `.mcp.json`:
```json
{ "mcpServers": { "browser-bridge": { "command": "npx", "args": ["@playwright/mcp@latest", "--cdp-endpoint", "http://localhost:9222"] } } }
```
Test: *"using the browser-bridge, list my open tabs."* The deny list in `.claude/settings.json` (Part 2) applies to this bridge.

**No browser at all** is fine for workflows that can use exports, files, or pasted text. Label those sources accurately; commands that require a live view remain incomplete until an approved access path is configured.

## Part 2: Permission configuration example (not a security guarantee)

Scheduled/headless runs may not pause to ask permission per tool. This
`.claude/settings.json` example narrows the configured operations, but does not
guarantee that the installed client loaded these settings or that every command
is safe:

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Write(./outputs/**)",
      "Write(./registers/**)",
      "Write(./state/**)",
      "Write(./logs/**)",
      "Write(./learning/**)",
      "Write(./reference/user-research/**)",
      "Write(./reference/metric-definitions/**)",
      "Edit(./outputs/**)",
      "Edit(./registers/**)",
      "Bash(python3 scripts/:*)",
      "Bash(bash scripts/:*)",
      "Bash(ls:*)",
      "Bash(cat:*)",
      "Bash(mkdir:*)",
      "Bash(mv inbox:*)",
      "Bash(mv ./inbox:*)",
      "WebSearch",
      "WebFetch",
      "mcp__browser-bridge__browser_snapshot",
      "mcp__browser-bridge__browser_navigate",
      "mcp__browser-bridge__browser_navigate_back",
      "mcp__browser-bridge__browser_tabs",
      "mcp__browser-bridge__browser_take_screenshot",
      "mcp__browser-bridge__browser_wait_for",
      "mcp__browser-bridge__browser_console_messages"
    ],
    "deny": [
      "mcp__browser-bridge__browser_click",
      "mcp__browser-bridge__browser_type",
      "mcp__browser-bridge__browser_fill_form",
      "mcp__browser-bridge__browser_select_option",
      "mcp__browser-bridge__browser_press_key",
      "mcp__browser-bridge__browser_drag",
      "mcp__browser-bridge__browser_hover",
      "mcp__browser-bridge__browser_file_upload",
      "mcp__browser-bridge__browser_evaluate",
      "mcp__browser-bridge__browser_run_code",
      "mcp__browser-bridge__browser_handle_dialog",
      "mcp__browser-bridge__browser_install",
      "Bash(git push:*)",
      "Bash(rm -rf:*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "PY=$(command -v python3 || command -v python); \"$PY\" \"$CLAUDE_PROJECT_DIR/.claude/hooks/validate_register_write.py\"",
            "timeout": 20
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "PY=$(command -v python3 || command -v python); \"$PY\" \"$CLAUDE_PROJECT_DIR/.claude/hooks/check_output_provenance.py\"",
            "timeout": 20
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "PY=$(command -v python3 || command -v python); \"$PY\" \"$CLAUDE_PROJECT_DIR/.claude/hooks/log_run.py\"",
            "timeout": 20
          }
        ]
      }
    ]
  }
}
```

This file is a project configuration example, not proof that Claude Code applied
the rules or that a browser connection works. Read the effective settings in
your installed version, verify the current tool names and permissions, and test
read-only behavior before relying on it. In headless runs, unlisted tools may be
refused rather than prompted; do not treat an allow-list as a physical
guarantee. Never enable or use an external write without approval in the moment.

## Part 3: Bookmarked views (30 min, pays off forever)

Automation should hit **saved, filtered views**, not wander whole apps. In your automation browser profile, bookmark:
- Slack searches for your area: feature names, product terms, "broken / can't / workaround / confusing" + your area
- The Jira/Confluence support-case views you already use
- Each dashboard behind an OKR metric (with filters applied)
- Behavior-analytics saved segments for your area
- Your experiment tool's active-experiments view
- Your Jira board's filtered active view

Paste each URL into the matching bracket in the command files. Narrow saved searches beat "read the whole channel" — infinite scroll makes channel-scale ingestion unreliable and noisy.

## Part 4: The three hooks (configured in this folder; verify locally)

`.claude/settings.json` registers three scripts in `.claude/hooks/`. Confirm
your Claude Code version runs them before relying on them. Their fail-open
behavior means a hook error warns but does not stop the work:

| Hook | When it fires | What it does for you |
|---|---|---|
| `validate_register_write.py` | before any write to `registers/*.csv` | checks field count, line breaks, duplicate IDs, and headers; preserves decision/evidence/participant history rows, while allowing same-ID updates to commitments/risks/initiatives/todos (rule 7, rule 14). It only sees Write/Edit tool calls, so `scripts/todo_register.py` re-checks the same rules itself |
| `check_output_provenance.py` | after any write to `outputs/`, `drafts/`, `learning/` | intends to flag a `DEC-`/`EV-`/`RISK-`/`TODO-` id not found in a register or a ticket key not found in an export (rule 3, rule 21); also records a hash of each file written to `outputs/` or `drafts/` in `state/output-hashes.csv` so the monthly review can count edits you made afterward |
| `log_run.py` | when a turn ends | intends to append the run-log line for a `/command` turn (rule 19) |

Every hook fails **open**: if one crashes, it prints a one-line warning and lets the work continue. They need Python 3 on your PATH (`python3` on macOS, `python` on Windows — the command tries both). To turn one off, delete its entry from `settings.json`. The independent checker cannot prove that Claude Code invoked these hooks.

After a run, `python3 scripts/check_run.py` checks local file changes, register
shape, selected provenance patterns, run-log activity, write scope, and
completion-claim wording. It detects deleted files using a path/content
inventory in `state/.last-check`; an unchanged inbox file moved into `archive/`
is treated as a move. Deletions before the first successful check or fixture
load establishes an inventory (including on older installations without one)
cannot be detected. Edits that preserve or predate their mtime can still escape
the changed-file checks. A failed check retains its successful baseline so the
same findings are checked again. See the checker docstring and
`fixtures/lumenly/README.md`.

## Part 5: Internal documents (shared drive, other wiki pages, the file browser)

Two access paths, use whichever is real for you:

**If your approved shared drive syncs to your machine:** provide the local folder or an approved file in `inbox/documents/`. Claude may be able to read it directly, subject to local permissions; verify on a non-sensitive test document first.

**If it doesn't sync, or the doc is Confluence-hosted beyond your Jira/support views:** use an approved browser path only after it has been configured and tested. The browser bridge and `internal-docs-reader` are not connected or verified by default.

**Binary formats** (.docx, .pptx, .xlsx) don't extract cleanly through a plain text read. `scripts/extract_document.sh` is currently a stub; it does not perform conversion yet. Use an approved export to plain text/CSV or paste relevant content until a specific format implementation has been tested.

Drop anything durable-but-unprocessed into `inbox/documents/`; `/capture process-inbox`
is a prompt workflow that may index it into `reference/user-research/` or the
appropriate local file and then archive the original. Review its proposed file
changes. Binary extraction is not available until the stub is implemented.

## Part 6: Verify the local loop

Use the fictional isolated fixture described in `START HERE.md`. Run the
repeatable safety/checker tests with:
```
python3 -m unittest discover -s tests -v
```
These tests verify file-copy protection, checker success/failure behavior, and
register-hook history rules. They do not verify Claude Code command execution,
browser access, external systems, or scheduled runs.
