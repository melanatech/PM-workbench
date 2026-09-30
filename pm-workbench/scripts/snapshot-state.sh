#!/usr/bin/env bash
# Create a local snapshot in an explicitly selected, approved non-Git location.
# This script never initializes, stages, commits, or pushes a repository.
set -euo pipefail
umask 077

WORKBENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
if [[ -z "${PM_STATE_BACKUP:-}" ]]; then
  echo "Set PM_STATE_BACKUP to an approved company-managed, access-controlled backup directory." >&2
  echo "No data was copied. This script will not default to a personal folder or Git repository." >&2
  exit 2
fi

mkdir -p "$PM_STATE_BACKUP"
BACKUP_DIR="$(cd "$PM_STATE_BACKUP" && pwd -P)"
case "$BACKUP_DIR/" in
  "$WORKBENCH_ROOT/"*)
    echo "Refusing to place sensitive state inside the workbench." >&2
    exit 2
    ;;
esac

if git -C "$BACKUP_DIR" rev-parse --show-toplevel >/dev/null 2>&1 \
  || git -C "$BACKUP_DIR" rev-parse --is-bare-repository 2>/dev/null | grep -qx true; then
  echo "Refusing to copy sensitive state into a Git working tree." >&2
  echo "Choose an approved company-managed backup location that is not a Git repository." >&2
  exit 2
fi

# Also reject a destination nested inside a bare repository, which has no
# working-tree root for `rev-parse --show-toplevel` to return.
candidate="$BACKUP_DIR"
while :; do
  if [[ -e "$candidate/.git" ]] || {
    [[ -f "$candidate/HEAD" && -d "$candidate/objects" && -d "$candidate/refs" ]]
  }; then
    echo "Refusing to copy sensitive state into a Git repository." >&2
    exit 2
  fi
  [[ "$candidate" == "/" ]] && break
  candidate="$(dirname "$candidate")"
done

STAMP="$(date +%Y%m%d-%H%M%S)"
SNAPSHOT_DIR="$BACKUP_DIR/$STAMP"
if [[ -e "$SNAPSHOT_DIR" ]]; then
  echo "Snapshot already exists: $SNAPSHOT_DIR" >&2
  exit 2
fi
mkdir -m 700 "$SNAPSHOT_DIR"

copied=0
for relative in registers reference/context logs; do
  source="$WORKBENCH_ROOT/$relative"
  if [[ -e "$source" ]]; then
    parent="$(dirname "$relative")"
    if [[ "$parent" != "." ]]; then
      mkdir -p "$SNAPSHOT_DIR/$parent"
    fi
    cp -R "$source" "$SNAPSHOT_DIR/$parent/"
    copied=1
  fi
done

if [[ "$copied" -eq 0 ]]; then
  rmdir "$SNAPSHOT_DIR"
  echo "No registers, context, or logs exist to snapshot."
  exit 1
fi

echo "Created a local snapshot at: $SNAPSHOT_DIR"
echo "It was not encrypted by this script and was not committed or uploaded."
echo "Apply your organization's approved access, encryption, and retention controls."
