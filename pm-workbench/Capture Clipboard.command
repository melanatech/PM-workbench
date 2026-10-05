#!/bin/bash
# Fallback launcher. Preferred UX on macOS: right-click / Services →
# "Send to PM Workbench" after: bash scripts/install_clipboard_service.sh
# Always writes into the live workspace (~/.pm-workbench/live-root), never the kit.

set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# If this .command is a symlink into the kit, prefer the live root marker.
if [[ -f "$HOME/.pm-workbench/live-root" ]]; then
  ROOT="$(grep -v '^#' "$HOME/.pm-workbench/live-root" | head -1 | tr -d '[:space:]')"
elif [[ -n "${PM_LIVE_ROOT:-}" ]]; then
  ROOT="$PM_LIVE_ROOT"
else
  ROOT="$HERE"
fi
SCRIPT="$ROOT/scripts/capture_clipboard.py"
if [[ ! -f "$SCRIPT" ]]; then
  # Dev-links: scripts may live only in the kit while ROOT is the live folder
  SCRIPT="$HERE/scripts/capture_clipboard.py"
fi
if [[ ! -f "$SCRIPT" ]]; then
  # Symlink target of this .command is the kit
  REAL="$(cd "$(dirname "$0")" && pwd -P 2>/dev/null || pwd)"
  SCRIPT="$REAL/scripts/capture_clipboard.py"
fi
if [[ ! -f "$SCRIPT" ]]; then
  osascript -e 'display alert "PM Workbench" message "Could not find scripts/capture_clipboard.py. Open ~/pm-live in Terminal and run: bash scripts/install_clipboard_service.sh"' 2>/dev/null || \
    echo "Could not find scripts/capture_clipboard.py" >&2
  read -r -p "Press Enter to close." _
  exit 1
fi
python3 "$SCRIPT" --root "$ROOT" --gui
STATUS=$?
if [[ $STATUS -ne 0 ]]; then
  read -r -p "Press Enter to close." _
fi
exit $STATUS
