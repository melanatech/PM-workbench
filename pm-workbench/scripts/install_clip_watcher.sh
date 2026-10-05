#!/usr/bin/env bash
# OPTIONAL: LaunchAgent that moves new clips when Downloads/pm-workbench-inbox changes.
# Preferred path (no Full Disk Access): /capture process-inbox in Claude Code runs
# scripts/pull_clips.py interactively. Use this watcher only if you want auto-move
# without opening Claude — on macOS that often needs Full Disk Access for python3.
#
#   bash scripts/install_clip_watcher.sh
#   bash scripts/install_clip_watcher.sh --root ~/pm-live
#   bash scripts/install_clip_watcher.sh --uninstall

set -euo pipefail

ROOT=""
UNINSTALL=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root) ROOT="$2"; shift 2 ;;
    --uninstall) UNINSTALL=1; shift ;;
    -h|--help)
      sed -n '2,14p' "$0"
      exit 0
      ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ -z "$ROOT" ]]; then
  if [[ -n "${PM_LIVE_ROOT:-}" ]]; then
    ROOT="$PM_LIVE_ROOT"
  elif [[ -f "$HOME/.pm-workbench/live-root" ]]; then
    ROOT="$(grep -v '^#' "$HOME/.pm-workbench/live-root" | head -1 | tr -d '[:space:]')"
  else
    ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  fi
fi
ROOT="$(cd "$ROOT" && pwd)"

LABEL="com.pm-workbench.clip-watcher"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON="$(command -v python3)"
# Prefer the resolved binary path — FDA grants attach to the real executable.
PYTHON_REAL="$(python3 -c 'import sys; print(sys.executable)' 2>/dev/null || echo "$PYTHON")"
PULL="$ROOT/scripts/pull_clips.py"
LOG_DIR="$ROOT/logs"
CLIPS_DIR="$HOME/Downloads/pm-workbench-inbox"
mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents" "$HOME/.pm-workbench" \
  "$CLIPS_DIR/meetings" "$CLIPS_DIR/captures" "$CLIPS_DIR/discovery" \
  "$CLIPS_DIR/competitive" "$CLIPS_DIR/metrics" "$CLIPS_DIR/documents"
printf '%s\n' "$ROOT" > "$HOME/.pm-workbench/live-root"

if [[ "$UNINSTALL" -eq 1 ]]; then
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "uninstalled $LABEL"
  exit 0
fi

if [[ ! -f "$PULL" ]]; then
  echo "missing $PULL — run from a live workspace that has scripts/" >&2
  exit 1
fi

# Probe Downloads access before installing a silent failing agent.
if ! "$PYTHON_REAL" -c "import os; os.listdir(os.path.expanduser('~/Downloads/pm-workbench-inbox'))" 2>/dev/null; then
  echo "WARNING: this python cannot list ~/Downloads/pm-workbench-inbox (macOS privacy)." >&2
  echo "Grant Full Disk Access, then re-run this installer:" >&2
  echo "  1. System Settings → Privacy & Security → Full Disk Access" >&2
  echo "  2. Click + and add: $PYTHON_REAL" >&2
  echo "  3. Toggle it on; quit/reopen Terminal if needed" >&2
  echo "  4. bash scripts/install_clip_watcher.sh" >&2
  echo "Until then, move clips manually: python3 scripts/pull_clips.py" >&2
  open "x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles" 2>/dev/null \
    || open "x-apple.systempreferences:com.apple.settings.PrivacySecurity.extension" 2>/dev/null \
    || true
fi

# WatchPaths: launchd runs the job when the watched path changes (new clip), then exits.
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_REAL}</string>
    <string>${PULL}</string>
    <string>--root</string>
    <string>${ROOT}</string>
  </array>
  <key>WatchPaths</key>
  <array>
    <string>${CLIPS_DIR}</string>
    <string>${CLIPS_DIR}/meetings</string>
    <string>${CLIPS_DIR}/captures</string>
    <string>${CLIPS_DIR}/discovery</string>
    <string>${CLIPS_DIR}/competitive</string>
    <string>${CLIPS_DIR}/metrics</string>
    <string>${CLIPS_DIR}/documents</string>
  </array>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/clip-watcher.out.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/clip-watcher.err.log</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || launchctl unload "$PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null || launchctl load "$PLIST"
# Drain anything already sitting in Downloads (may fail without FDA — that's OK).
if "$PYTHON_REAL" "$PULL" --root "$ROOT"; then
  :
else
  echo "pull_clips could not drain Downloads yet (likely macOS privacy). Fix FDA, then:" >&2
  echo "  python3 scripts/pull_clips.py" >&2
fi
echo "installed $LABEL → $ROOT/inbox/"
echo "event-driven: runs pull_clips.py when ~/Downloads/pm-workbench-inbox/ changes"
echo "if clips stay in Downloads: grant Full Disk Access to $PYTHON_REAL"
echo "uninstall: bash scripts/install_clip_watcher.sh --uninstall"
