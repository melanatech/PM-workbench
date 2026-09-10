# PM Workbench Clipper (Chrome extension, ~2 minutes to install, no admin)

**What it does:** right-click a page or a selected passage in Chrome → *Send to PM Workbench* → pick a category → a markdown file with the URL, title, timestamp and access path in its frontmatter lands in `~/Downloads/pm-workbench-inbox/<category>/`. That is the whole extension. It never clicks, types, submits, or talks to the network.

**Why this and not automation:** capture is a human act — you are looking at a Slack thread, a support case, a competitor page — and the only thing the system needs is the text plus its provenance. A click by you needs no automation policy, no debug port, no bridge. Reading pages *without* you is a different job; see SETUP.md Part 1.

## Install (Chrome or Edge, macOS or Windows)
1. Open `chrome://extensions` (Edge: `edge://extensions`).
2. Turn on **Developer mode** (top right).
3. **Load unpacked** → choose this folder (`tools/workbench-clipper`).
4. Done. Right-click any page.

Unpacked extensions survive restarts. Chrome may show a "disable developer-mode extensions" nag on launch; dismiss it. If your organization's Chrome policy blocks developer-mode extensions entirely, the OS clipboard shortcut (`Capture Clipboard.command`, or paste into the chat) does the same job with one more step.

## Get the clips into the workbench
```
python3 scripts/pull_clips.py          # moves Downloads/pm-workbench-inbox/** → inbox/<category>/
```
`/process-inbox` runs this first, so the nightly run picks them up automatically. Each clip keeps its frontmatter, so every register row that comes from a clip can cite the URL.

## Privacy
Clips can contain customer names. They are working material in `inbox/` and get archived, never committed to git (see `.gitignore`), and CLAUDE.md rule 15 redacts identifiers in durable summaries.
