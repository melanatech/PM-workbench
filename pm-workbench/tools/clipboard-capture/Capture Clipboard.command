#!/bin/bash
# Fallback only — prefer right-click Services after install_clipboard_service.sh.
# Resolves live workspace via ~/.pm-workbench/live-root (not this file's location).
set -euo pipefail
HOME_DIR="${HOME:-$(/bin/echo ~)}"
LIVE_ROOT=""
if [[ -f "$HOME_DIR/.pm-workbench/live-root" ]]; then
  LIVE_ROOT="$(/usr/bin/grep -v '^#' "$HOME_DIR/.pm-workbench/live-root" | /usr/bin/head -1 | /usr/bin/tr -d '[:space:]')"
fi
if [[ -z "$LIVE_ROOT" || ! -d "$LIVE_ROOT" ]]; then
  LIVE_ROOT="$HOME_DIR/pm-live"
fi
SCRIPT="$LIVE_ROOT/scripts/capture_clipboard.py"
if [[ ! -f "$SCRIPT" ]]; then
  osascript -e "display alert \"PM Workbench\" message \"Missing $SCRIPT — set live-root or create ~/pm-live.\"" >/dev/null 2>&1 || true
  exit 1
fi
exec /usr/bin/python3 "$SCRIPT" --root "$LIVE_ROOT" --gui
