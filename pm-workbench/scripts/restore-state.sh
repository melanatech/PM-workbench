#!/usr/bin/env bash
# Restore missing files from a snapshot without replacing current workbench state.
set -euo pipefail
umask 077

usage() {
  cat >&2 <<'USAGE'
Usage: scripts/restore-state.sh [--dry-run] SNAPSHOT_DIR

Restore missing files from a snapshot made by scripts/snapshot-state.sh.
Only registers/, reference/context/, and logs/ are in scope. Existing identical
files are left untouched; differing files and unsafe links refuse the restore.
Use --dry-run to review the planned actions without changing anything.
USAGE
}

dry_run=0
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  usage
  exit 0
fi
if [[ "${1:-}" == "--dry-run" ]]; then
  dry_run=1
  shift
fi
if [[ "$#" -ne 1 ]]; then
  usage
  exit 2
fi

WORKBENCH_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SNAPSHOT_ARG="$1"
if [[ -L "$SNAPSHOT_ARG" || ! -d "$SNAPSHOT_ARG" ]]; then
  echo "Unsafe or missing snapshot directory: $SNAPSHOT_ARG" >&2
  exit 2
fi
SNAPSHOT_DIR="$(cd "$SNAPSHOT_ARG" && pwd -P)"
case "$SNAPSHOT_DIR/" in
  "$WORKBENCH_ROOT/"*)
    echo "Refusing a snapshot inside the workbench." >&2
    exit 2
    ;;
esac
if [[ "$SNAPSHOT_DIR" == "$WORKBENCH_ROOT" ]]; then
  echo "Refusing to use the workbench itself as a snapshot." >&2
  exit 2
fi

# Build the complete source manifest before validating or changing the target.
# A process substitution hides the producer's exit status, so capture and check
# find directly. Every later snapshot pass reuses this validated manifest.
manifest="$(mktemp "${TMPDIR:-/tmp}/pm-restore-manifest.XXXXXXXX")"
trap 'rm -f "$manifest"' EXIT
if ! find "$SNAPSHOT_DIR" -mindepth 1 -print0 > "$manifest"; then
  echo "Failed to enumerate the snapshot completely; refusing restore." >&2
  exit 2
fi
if ! cat "$manifest" > /dev/null; then
  echo "Failed to read the complete snapshot manifest; refusing restore." >&2
  exit 2
fi

# A snapshot must contain only the paths copied by snapshot-state.sh. Reject
# links and special files before mapping any snapshot entry into the workbench.
while IFS= read -r -d '' path || [[ -n "${path:-}" ]]; do
  relative="${path#"$SNAPSHOT_DIR"/}"
  case "$relative" in
    registers|registers/*|logs|logs/*|reference|reference/context|reference/context/*) ;;
    *)
      echo "Unsafe snapshot path outside the saved state scope: $relative" >&2
      exit 2
      ;;
  esac
  if [[ -L "$path" ]]; then
    echo "Unsafe symlink in snapshot: $relative" >&2
    exit 2
  fi
  if [[ ! -d "$path" && ! -f "$path" ]]; then
    echo "Unsafe special file in snapshot: $relative" >&2
    exit 2
  fi
done < "$manifest"

# The link-count scan is checked too: an incomplete scan cannot authorize a
# restore. Its list is only used to refuse unsafe input; the main manifest
# remains the sole source of paths to preflight and restore.
snapshot_hardlinks="$(mktemp "${TMPDIR:-/tmp}/pm-restore-hardlinks.XXXXXXXX")"
trap 'rm -f "$manifest" "$snapshot_hardlinks"' EXIT
if ! find "$SNAPSHOT_DIR" -type f -links +1 -print0 > "$snapshot_hardlinks"; then
  echo "Failed to inspect snapshot hardlinks; refusing restore." >&2
  exit 2
fi
if [[ -s "$snapshot_hardlinks" ]]; then
  IFS= read -r -d '' path < "$snapshot_hardlinks" || true
  relative="${path#"$SNAPSHOT_DIR"/}"
  echo "Unsafe hardlinked file in snapshot: $relative" >&2
  exit 2
fi

# Snapshot paths are enumerated first so that unexpected top-level entries,
# including files where a saved root directory is expected, cannot be ignored.
for root in "$SNAPSHOT_DIR/registers" "$SNAPSHOT_DIR/reference" "$SNAPSHOT_DIR/logs"; do
  if [[ -e "$root" && ! -d "$root" ]]; then
    echo "Unsafe snapshot root: ${root#"$SNAPSHOT_DIR"/}" >&2
    exit 2
  fi
done
if [[ -e "$SNAPSHOT_DIR/reference" && ! -d "$SNAPSHOT_DIR/reference/context" ]]; then
  echo "Unsafe snapshot path: reference must contain context/." >&2
  exit 2
fi

# Reject symlinks and hardlinked files anywhere under the destination roots,
# not just at paths that happen to be present in this snapshot.
for target_root in "$WORKBENCH_ROOT/registers" "$WORKBENCH_ROOT/logs" \
                   "$WORKBENCH_ROOT/reference" "$WORKBENCH_ROOT/reference/context"; do
  if [[ -L "$target_root" ]]; then
    echo "Unsafe symlink in restore target: ${target_root#"$WORKBENCH_ROOT"/}" >&2
    exit 2
  fi
done
for target_root in "$WORKBENCH_ROOT/registers" "$WORKBENCH_ROOT/logs" \
                   "$WORKBENCH_ROOT/reference/context"; do
  if [[ -d "$target_root" ]]; then
    if ! unsafe_link="$(find "$target_root" -type l -print -quit)"; then
      echo "Failed to inspect restore target symlinks: ${target_root#"$WORKBENCH_ROOT"/}" >&2
      exit 2
    fi
    if [[ -n "$unsafe_link" ]]; then
      echo "Unsafe symlink in restore target: ${unsafe_link#"$WORKBENCH_ROOT"/}" >&2
      exit 2
    fi
    if ! hardlink="$(find "$target_root" -type f -links +1 -print -quit)"; then
      echo "Failed to inspect restore target hardlinks: ${target_root#"$WORKBENCH_ROOT"/}" >&2
      exit 2
    fi
    if [[ -n "$hardlink" ]]; then
      echo "Unsafe hardlinked file in restore target: ${hardlink#"$WORKBENCH_ROOT"/}" >&2
      exit 2
    fi
  elif [[ -e "$target_root" ]]; then
    echo "Unsafe restore target (not a directory): ${target_root#"$WORKBENCH_ROOT"/}" >&2
    exit 2
  fi
done

# Preflight every snapshot entry before writing anything. No differing target
# file is ever eligible for replacement.
while IFS= read -r -d '' path || [[ -n "${path:-}" ]]; do
  relative="${path#"$SNAPSHOT_DIR"/}"
  target="$WORKBENCH_ROOT/$relative"
  if [[ -L "$target" ]]; then
    echo "Unsafe symlink in restore target: $relative" >&2
    exit 2
  fi
  if [[ -d "$path" ]]; then
    if [[ -e "$target" && ! -d "$target" ]]; then
      echo "Conflict (directory required): $relative" >&2
      exit 2
    fi
  else
    if ! cat "$path" > /dev/null; then
      echo "Failed to read snapshot file during preflight: $relative" >&2
      exit 2
    fi
    if [[ -e "$target" ]]; then
      if [[ ! -f "$target" ]]; then
        echo "Conflict (regular file required): $relative" >&2
        exit 2
      fi
      if ! cmp -s "$path" "$target"; then
        echo "Conflict (existing file differs): $relative" >&2
        exit 2
      fi
    fi
  fi
done < "$manifest"

if [[ "$dry_run" -eq 1 ]]; then
  while IFS= read -r -d '' path || [[ -n "${path:-}" ]]; do
    relative="${path#"$SNAPSHOT_DIR"/}"
    target="$WORKBENCH_ROOT/$relative"
    if [[ -f "$path" ]]; then
      if [[ -e "$target" ]]; then
        echo "Unchanged (identical): $relative"
      else
        echo "Would restore: $relative"
      fi
    fi
  done < "$manifest"
  echo "Dry run complete; no files were changed."
  exit 0
fi

# Create missing directories only after the complete preflight. Install files
# through a same-directory temporary followed by ln, whose no-clobber behavior
# prevents a concurrent target from ever being overwritten.
while IFS= read -r -d '' path || [[ -n "${path:-}" ]]; do
  relative="${path#"$SNAPSHOT_DIR"/}"
  if [[ -d "$path" ]]; then
    target="$WORKBENCH_ROOT/$relative"
    if [[ ! -d "$target" ]]; then
      mkdir -p "$target"
    fi
  fi
done < "$manifest"

while IFS= read -r -d '' path || [[ -n "${path:-}" ]]; do
  relative="${path#"$SNAPSHOT_DIR"/}"
  target="$WORKBENCH_ROOT/$relative"
  [[ -f "$path" ]] || continue
  if [[ -e "$target" ]]; then
    # Identical files are intentionally not rewritten.
    continue
  fi
  temporary="$(mktemp "$(dirname "$target")/.restore-state.XXXXXXXX")"
  if ! cp "$path" "$temporary"; then
    rm -f "$temporary"
    echo "Failed to stage snapshot file: $relative" >&2
    exit 2
  fi
  if ! ln "$temporary" "$target"; then
    rm -f "$temporary"
    if [[ -f "$target" ]] && cmp -s "$path" "$target"; then
      echo "Unchanged (identical): $relative"
      continue
    fi
    echo "Conflict while restoring (target appeared or is unsafe): $relative" >&2
    exit 2
  fi
  rm -f "$temporary"
  echo "Restored: $relative"
done < "$manifest"