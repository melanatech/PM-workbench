#!/bin/bash
set -euo pipefail
ROOT="${1:-$HOME/pm-live}"
mkdir -p "$HOME/.pm-workbench"
printf '%s\n' "$ROOT" > "$HOME/.pm-workbench/live-root"
echo "live-root → $(cat "$HOME/.pm-workbench/live-root")"
