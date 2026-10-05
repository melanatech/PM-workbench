#!/bin/bash
# Double-click this to install right-click Services (runs outside Cursor sandbox).
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="${PM_LIVE_ROOT:-$HOME/pm-live}"
if [[ -f "$HOME/.pm-workbench/live-root" ]]; then
  ROOT="$(grep -v '^#' "$HOME/.pm-workbench/live-root" | head -1 | tr -d '[:space:]')"
fi
[[ -d "$ROOT" ]] || ROOT="$HOME/pm-live"
SCRIPT="$ROOT/scripts/install_clipboard_service.sh"
if [[ ! -f "$SCRIPT" ]]; then
  SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/install_clipboard_service.sh"
fi
bash "$SCRIPT" --root "$ROOT"
echo ""
echo "Press Enter to close…"
read -r _
