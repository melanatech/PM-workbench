# PM Workbench Clipper (Chrome extension, ~2 minutes to install, no admin)

**What it does:** right-click a page (or a selection) in Chrome → *Send to PM Workbench* → pick a category → a markdown file lands in `~/Downloads/pm-workbench-inbox/<category>/`, plus a viewport screenshot PNG for non-meeting categories. That is the whole extension. It never clicks, types, submits, or talks to the network.

**After updating this folder:** open `chrome://extensions` → find PM Workbench Clipper → **Reload**. Until you reload, Chrome keeps the old menu.

**Why Downloads (and not `inbox/` directly):** Chrome's extension downloads API can only write under the browser Downloads folder.

**How clips get into the workbench (preferred — no Full Disk Access):**

1. Clip in Chrome as usual.
2. In Claude Code (with `~/pm-live` open): `/capture process-inbox`  
   Step 0 runs `python3 scripts/pull_clips.py` and moves `~/Downloads/pm-workbench-inbox/**` → `inbox/<category>/`.  
   Approve the Bash run when prompted. That uses your interactive session, not a background agent, so you do **not** need Full Disk Access for `/usr/bin/python3`.

One-shot without a full inbox sweep:
```
python3 scripts/pull_clips.py
```
(from Terminal or ask Claude Code to run it)

**Optional:** `bash scripts/install_clip_watcher.sh` installs a LaunchAgent that moves files when Downloads changes. On macOS that background job often needs Full Disk Access — skip it unless you want zero Claude involvement.

**What is saved**

| | |
|---|---|
| **Yes** | Visible text: for meetings, scrolls the Stream transcript panel and accumulates `sub-entry-*` rows until `aria-setsize` (or scroll stalls); otherwise page `innerText` (up to ~200k chars); title; URL; up to 80 links |
| **Screenshot** | Optional **viewport** PNG for every category **except meetings** (what is on screen, not a scrolled full-page stitch). Meetings are text/transcript only |
| **No** | Embedded images from the page, video frames, or a stitched infinite-scroll capture |
| **Menu** | The six categories always scrape the **full transcript/page**. Under a highlight, a second group **Selection only** exists if you truly want just the highlight |

Stream tip: right-click the transcript → *Meeting notes / summary* and wait a few
seconds while it scrolls the panel (virtualized list). Check the notification count
(`entries/aria_setsize`). See [DEBUG.md](DEBUG.md) if clips still stop early.
Do not use **Selection only** for long meetings.

## Install (Chrome or Edge, macOS or Windows)
1. Open `chrome://extensions` (Edge: `edge://extensions`).
2. Turn on **Developer mode** (top right).
3. **Load unpacked** → choose this folder (`tools/workbench-clipper`).
4. Done. Right-click any page. After kit updates, **Reload** the extension.

## Privacy
Clips can contain customer names. They are working material in `inbox/` and get archived, never committed to git (see `.gitignore`), and CLAUDE.md rule 15 redacts identifiers in durable summaries.
