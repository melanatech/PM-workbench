#!/bin/bash
# Open the PM Workbench automation Chrome (SSO + Playwright CDP on 9222).
# Keep this window open while Claude reads company pages.
set -euo pipefail
exec /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$HOME/chrome-claude-profile" \
  --no-first-run \
  --no-default-browser-check \
  "$@"
