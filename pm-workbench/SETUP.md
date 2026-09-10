# SETUP.md — the one genuinely one-time piece (browser access, ~15 min) plus optional accelerators

Nothing here gates using the system. Commands run day one on paste-ins and clipboard capture; do Part 0 first because it's the highest-leverage ten minutes available (it's *why* outputs sound like your team instead of generic), then Part 1 when you first want a command to browse for you, and the rest whenever convenient.

## Part 0: Give it context (do this first — ~10 minutes)

This matters more than anything technical below it. A command working perfectly against zero context still produces a generic-sounding draft; a few minutes of real context is what makes the first output sound like your team wrote it.

1. **Open `CLAUDE.md` and fill in the brackets** in "Who I am" — company, area, leadership chain, writing style, decision philosophy. Don't overthink it; a rough first pass beats a perfect one you never get to.
2. **Seed `reference/links.csv`** with 3-5 links you reference constantly: your team's PRD template, your Jira conventions doc, your team wiki home, a recurring dashboard. Two minutes each, and every command that needs one of these stops guessing.
3. **Drop 1-2 real past PRDs or updates** into `reference/templates/` if you have them handy — this is what future drafts match against instead of a generic structure. Skip it if you don't have anything handy yet; commands will ask for one the first time they need it.

That's it — not a checklist to finish, just the fastest way to make week-one output feel calibrated instead of generic.

## Part 1: Browser access — three jobs, three tools, in this order

None of this needs admin approval. Extensions are yours to install; connectors and MCP servers are not, so this kit never depends on them.

**Job A — capturing what you're looking at (most days, most value).** Install the **Workbench Clipper** from `tools/workbench-clipper/` (2 minutes, `chrome://extensions` → Developer mode → Load unpacked → that folder). Right-click any page or selection → *Send to PM Workbench* → it lands in `Downloads/pm-workbench-inbox/` with URL, title and timestamp in the frontmatter; `/process-inbox` pulls it in. A human clicked, so there is no automation to govern. If developer-mode extensions are blocked on your machine, `Capture Clipboard.command` or pasting into the chat does the same with one more step.

**Job B — letting Claude read pages for you (discovery scans, OKR pulls, Jira views).** Try Anthropic's own integration first: install the **Claude in Chrome** extension from the Chrome Web Store, sign in, then in Claude Code type `/chrome` (or launch `claude --chrome`). Test with: *"In read-only mode, tell me what's on my currently open tab. Do not click or type anything."* Beta; Chrome and Edge only; needs a claude.ai login (not available through Bedrock/Vertex/Foundry access); an org can disable the extension, in which case fall through to Job C. This is maintained by Anthropic and has its own permission model — prefer it over anything you'd maintain yourself.

**Job C — fallback only: Playwright MCP over a debug Chrome profile.** Same reads, but you own the plumbing (a Chrome profile that must be open, an SSO that expires, a deny list you keep current). Use it only if Job B is blocked.
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

**No browser at all** is also fine: every command runs on exports and pastes, labeled as such (rule 11's fallback ladder).

## Part 2: Scoped permissions (replaces the dangerous flag)

Scheduled/headless runs can't pause to ask permission per tool. Instead of disabling permissions entirely, `.claude/settings.json` in this folder pre-approves only safe operations:

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

Read/navigate/snapshot/tabs/screenshot: pre-approved. Every Playwright interaction tool (click, type, fill, select, key, drag, hover, upload, evaluate, run-code, dialog): **denied**. In headless `-p` runs an unlisted tool is refused rather than prompted. This is an allow-list you can read and should re-check when `@playwright/mcp` adds tools — not a physical guarantee. When you run interactively and want Claude to pre-fill a form, you'll get the normal permission prompt and approve it live. That's the gate working as designed.

## Part 3: Bookmarked views (30 min, pays off forever)

Automation should hit **saved, filtered views**, not wander whole apps. In your automation browser profile, bookmark:
- Slack searches for your area: feature names, product terms, "broken / can't / workaround / confusing" + your area
- The Jira/Confluence support-case views you already use
- Each dashboard behind an OKR metric (with filters applied)
- Behavior-analytics saved segments for your area
- Your experiment tool's active-experiments view
- Your Jira board's filtered active view

Paste each URL into the matching bracket in the command files. Narrow saved searches beat "read the whole channel" — infinite scroll makes channel-scale ingestion unreliable and noisy.

## Part 4: The three hooks (already on — nothing to install)

`.claude/settings.json` also registers three small scripts in `.claude/hooks/` that Claude Code runs by itself. You never invoke them; you notice them only when they catch something:

| Hook | When it fires | What it does for you |
|---|---|---|
| `validate_register_write.py` | before any write to `registers/*.csv` | rejects a row with the wrong field count, an unquoted comma, a line break in a cell, a duplicate id, or a changed header — and tells Claude exactly what to fix (rule 14, rule 7) |
| `check_output_provenance.py` | after any write to `outputs/`, `drafts/`, `learning/` | if the file cites a `DEC-`/`EV-`/`RISK-` id that no register holds, or a ticket key that appears in no export, Claude is told to fix it in the same turn (rule 3, rule 21) |
| `log_run.py` | when a turn ends | appends the run-log line for any `/command` turn (rule 19) — so the log fills itself in |

Every hook fails **open**: if one crashes, it prints a one-line warning and lets the work continue. They need Python 3 on your PATH (`python3` on macOS, `python` on Windows — the command tries both). To turn one off, delete its entry from `settings.json`.

After a run, `python3 scripts/check_run.py` re-checks everything the hooks check plus dates, figures and quotes against your inputs — see `fixtures/lumenly/README.md`.

## Part 5: Internal documents (shared drive, other wiki pages, the file browser)

Two access paths, use whichever is real for you:

**If your shared drive syncs to your machine** (OneDrive, Google Drive, Dropbox): the files already sit in Finder somewhere like `~/OneDrive - [Company]/` or `~/Google Drive/`. Claude can read these directly with no browser step at all — just tell it the folder, or drop specific files into `inbox/documents/`.

**If it doesn't sync, or the doc is Confluence-hosted beyond your Jira/support views:** the browser bridge reaches it the same way it reaches chat or dashboards — open it in the automation Chrome profile, and `internal-docs-reader` can navigate and read it.

**Binary formats** (.docx, .pptx, .xlsx) don't extract cleanly through a plain text read. `scripts/extract_document.sh` handles the conversion (macOS's built-in `textutil` for Word docs, `pdftotext` for PDFs — `brew install poppler` if you don't have it). It's a stub Cursor fills in once you have a real file to test against.

Drop anything durable-but-unprocessed into `inbox/documents/`; `/process-inbox` indexes it into `reference/user-research/` (for research) or the right register/learning file (for everything else), then archives the original.

## Part 6: Verify the loop
```
claude -p "/process-inbox" 
```
with one test file in `inbox/discovery/`. If it processes, files to archive, and updates the evidence register, the machine works.
