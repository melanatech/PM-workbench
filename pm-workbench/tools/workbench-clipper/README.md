# PM Workbench Clipper (Chrome extension, ~2 minutes to install, no admin)

**What it does:** right-click a page (or a selection) in Chrome → *Send to PM Workbench* → pick a category → a markdown file lands in `~/Downloads/pm-workbench-inbox/<category>/`, plus a viewport screenshot PNG for non-meeting categories. **Walkthrough mode** records clicks/URLs + viewport PNGs in your **logged-in** tab until you Stop (SSO-safe alternative to Playwright). It never auto-clicks, types, submits, or talks to the network.

**Version:** 0.5.0+ required for walkthrough. **After updating this folder:** open `chrome://extensions` → find PM Workbench Clipper → **Reload**. Until you reload, Chrome keeps the old menu.

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
| **Screenshot** | Optional **viewport** PNG for every category **except meetings** (sidecar with page text). Meetings are text/transcript only |
| **Screenshot only** | Menu group **Screenshot only (no page text)** → pick a category → viewport PNG + stub markdown (`capture_kind: screenshot`). No `innerText` scrape |
| **Walkthrough** | *Walkthrough: Start recording* → use the product normally → *Mark step* (or Alt+Shift+M) for a clean frame → *Stop & save* (or toolbar badge / Alt+Shift+S). Also: toolbar icon toggles Start/Stop. Writes `walkthroughs/<stem>.md` + `.events.jsonl` + `.step-NN.png`. Viewport only — scroll then Mark step for below-the-fold |
| **No** | Embedded page images, video frames, automatic full-page stitch, keystroke/password values |
| **Menu** | Categories scrape transcript/page; **Selection only**; **Screenshot only**; **Walkthrough** Start / Mark / Stop |

Stream tip: right-click the transcript → *Meeting notes / summary* and wait a few
seconds while it scrolls the panel (virtualized list). Check the notification count
(`entries/aria_setsize`). See [DEBUG.md](DEBUG.md) if clips still stop early.
Do not use **Selection only** for long meetings.

## Install (Chrome or Edge, macOS or Windows)
1. Open `chrome://extensions` (Edge: `edge://extensions`).
2. Turn on **Developer mode** (top right).
3. **Load unpacked** → choose this folder (`tools/workbench-clipper`).
4. Done. Right-click any page. After kit updates, **Reload** the extension.

## Walkthrough quick start (SSO’d product UI)

1. Reload extension (v0.5.0+).
2. On the product tab (already signed in): right-click → *Send to PM Workbench* → **Walkthrough: Start recording** (or click the extension icon). Badge shows **REC**.
3. Click through the flow. After big UI changes or scrolling to content below the fold, **Walkthrough: Mark step** (Alt+Shift+M).
4. **Walkthrough: Stop & save** (Alt+Shift+S or click the icon again).
5. `/capture process-inbox` — pulls `~/Downloads/pm-workbench-inbox/walkthroughs/` into `inbox/walkthroughs/`.

Screenshots are **viewport-only** and do not wait for network idle by themselves; the extension debounces after navigation/`complete` and after scroll stops. Use Mark step when the frame looks right.

## Privacy
Clips can contain customer names. They are working material in `inbox/` and get archived, never committed to git (see `.gitignore`), and CLAUDE.md rule 15 redacts identifiers in durable summaries. Walkthroughs redact password field values.
