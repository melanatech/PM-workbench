# Clipboard capture (desktop apps)

Chrome has the **Workbench Clipper** (macOS and Windows). Slack / Mail / Notes need a separate path.

## macOS — right-click Services

```bash
cd ~/pm-live && bash scripts/install_clipboard_service.sh
```

That compiles a real Cocoa Services app into `~/Applications/Send to PM Workbench.app`. Shell scripts and Automator stubs cannot receive selected text — only an `NSServices` provider can.

**Enable once**

**System Settings → Keyboard → Keyboard Shortcuts → Services** → Text → turn ON **Send to PM Workbench**  
(Not under Privacy & Security.)

**Use it**

1. Select text in Slack (or Mail / Notes)
2. Right-click → **Services** → **Send to PM Workbench**  
   If the app hides Services on right-click: menu bar → app name → **Services** → **Send to PM Workbench**
3. Pick a category → file lands in `inbox/<category>/`  
   Categories: Discovery · Meeting notes · **Slack communication** · Just capture it · Competitive · Internal document · Metric/dashboard
4. `/capture process-inbox` (`inbox/slack/` routes as discovery-adjacent unless the paste is clearly a meeting summary)

Optional: assign a keyboard shortcut in that same Services list.

Fallback: `Capture Clipboard.command` (copy first, then double-click).

## Windows — no Services equivalent

Windows Explorer **Send to** is for files, not selected text in Slack/Teams. There is no right-click-selection install.

1. Copy text (Ctrl+C)
2. `python scripts/capture_clipboard.py --gui` from your live folder (or paste into Claude Code)
3. `/capture process-inbox`

Chrome still uses the Workbench Clipper.

Writes always go to the live workspace (`~/.pm-workbench/live-root`), never the git kit.
