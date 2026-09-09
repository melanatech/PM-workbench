#!/usr/bin/env bash
# End-of-session state snapshot to your personal backup repo.
# One-time: set BACKUP_REMOTE to your private repo, run `git init` in ./state-backup.
set -euo pipefail
BACKUP_DIR="${PM_STATE_BACKUP:-$HOME/pm-workbench-state}"
mkdir -p "$BACKUP_DIR"
cp -R registers reference/context logs "$BACKUP_DIR/" 2>/dev/null || true
cd "$BACKUP_DIR"
git add -A && git commit -m "state snapshot $(date +%F-%H%M)" || echo "nothing to snapshot"
# git push   # uncomment once your remote is configured
