# SETUP.md — the one genuinely one-time piece (browser access, ~15 min) plus optional accelerators

Nothing here gates using the system. Commands run day one on paste-ins and clipboard capture; do Part 0 first because it's the highest-leverage ten minutes available (it's *why* outputs sound like your team instead of generic), then Part 1 when you first want a command to browse for you, and the rest whenever convenient.

## Part 0: Give it context (do this first — ~10 minutes)

This matters more than anything technical below it. A command working perfectly against zero context still produces a generic-sounding draft; a few minutes of real context is what makes the first output sound like your team wrote it.

1. **Open `CLAUDE.md` and fill in the brackets** in "Who I am" — company, area, leadership chain, writing style, decision philosophy. Don't overthink it; a rough first pass beats a perfect one you never get to.
2. **Seed `reference/links.csv`** with 3-5 links you reference constantly: your team's PRD template, your Jira conventions doc, your team wiki home, a recurring dashboard. Two minutes each, and every command that needs one of these stops guessing.
3. **Drop 1-2 real past PRDs or updates** into `reference/templates/` if you have them handy — this is what future drafts match against instead of a generic structure. Skip it if you don't have anything handy yet; commands will ask for one the first time they need it.

That's it — not a checklist to finish, just the fastest way to make week-one output feel calibrated instead of generic.

## Part 1: Browser access — try the simple thing first

**Option A — `claude --chrome` (test this first, 2 minutes).**
Claude Code has built-in Chrome integration: run `claude --chrome` and Claude works through visible tabs in your real browser — your logins, no extra install. **Caveat:** this uses the Claude in Chrome extension, which Enterprise admins can disable org-wide, same lever as the connectors. So: test, don't assume.

```
claude --chrome
```
Then: *"In read-only mode, tell me what's on my currently open tab. Do not click or type anything."*

Works → skip to Part 2. Blocked → Option B.

**Option B — Playwright MCP + CDP debug profile (the no-admin fallback you fully control).**
Same CDP mechanism as your dashboard-builder extension. Install:
```
npm install -g @playwright/mcp
```
Launch a dedicated automation Chrome profile (save as a shortcut — this window open = Claude has browser hands):
```
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-claude-profile"
```
Log into everything once in that window (Slack, QuickSight, FullStory, Outlook web, experiment tool, internal chat tool). Sessions persist until normal SSO timeout.

Register in this project's `.mcp.json`:
```json
{
  "mcpServers": {
    "browser-bridge": {
      "command": "npx",
      "args": ["@playwright/mcp@latest", "--cdp-endpoint", "http://localhost:9222"]
    }
  }
}
```
Test: `claude` in this folder → *"Using browser-bridge, list my open tabs, then read the text of one."*

If Claude Code's bundled Playwright plugin fights the CDP config (known issue on some setups), swap in Google's `chrome-devtools-mcp` — same endpoint, drop-in.

**Option C — zero-install capture (the floor if both above are blocked).**
`Capture-Clipboard.command` in this folder: copy text anywhere → double-click → choose a category → timestamped Markdown lands in the right `inbox/` subfolder with source metadata. Manual capture, automated everything-after.

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
      "Edit(./outputs/**)",
      "Edit(./registers/**)",
      "Bash(python3 scripts/*)",
      "Bash(ls*)", "Bash(cat*)", "Bash(mkdir*)", "Bash(mv ./inbox*)",
      "WebSearch",
      "mcp__browser-bridge__browser_snapshot",
      "mcp__browser-bridge__browser_navigate",
      "mcp__browser-bridge__browser_tab_list"
    ],
    "deny": [
      "mcp__browser-bridge__browser_click",
      "mcp__browser-bridge__browser_type",
      "mcp__browser-bridge__browser_file_upload"
    ]
  }
}
```

Read/navigate/snapshot: pre-approved. Click/type: **denied in headless runs** — so a scheduled job physically cannot submit anything, even by mistake. When you run interactively and want Claude to pre-fill a form, you'll get the normal permission prompt and approve it live. That's the gate working as designed.

## Part 3: Bookmarked views (30 min, pays off forever)

Automation should hit **saved, filtered views**, not wander whole apps. In your automation browser profile, bookmark:
- Slack searches for your area: feature names, product terms, "broken / can't / workaround / confusing" + your area
- The Jira/Confluence support-case views you already use
- Each QuickSight dashboard behind an OKR metric (with filters applied)
- FullStory saved segments for your area
- Your experiment tool's active-experiments view
- Your Jira board's filtered active view

Paste each URL into the matching bracket in the command files. Narrow saved searches beat "read the whole channel" — infinite scroll makes channel-scale ingestion unreliable and noisy.

## Part 5: Internal documents (SharePoint, other Confluence pages, the file browser)

Two access paths, use whichever is real for you:

**If SharePoint/OneDrive syncs to your Mac** (common in Microsoft-365 orgs): the files already sit in Finder somewhere like `~/OneDrive - [Company]/`. Claude can read these directly with no browser step at all — just tell it the folder, or drop specific files into `inbox/documents/`.

**If it doesn't sync, or the doc is Confluence-hosted beyond your Jira/support views:** the browser bridge reaches it the same way it reaches Slack/QuickSight — open it in the automation Chrome profile, and `internal-docs-reader` can navigate and read it.

**Binary formats** (.docx, .pptx, .xlsx) don't extract cleanly through a plain text read. `scripts/extract_document.sh` handles the conversion (macOS's built-in `textutil` for Word docs, `pdftotext` for PDFs — `brew install poppler` if you don't have it). It's a stub Cursor fills in once you have a real file to test against.

Drop anything durable-but-unprocessed into `inbox/documents/`; `/process-inbox` indexes it into `reference/user-research/` (for research) or the right register/learning file (for everything else), then archives the original.

## Part 6: Verify the loop
```
claude -p "/process-inbox" 
```
with one test file in `inbox/discovery/`. If it processes, files to archive, and updates the evidence register, the machine works.
