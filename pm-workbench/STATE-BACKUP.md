# State backup & retention

The workbench's registers, living context, and logs may contain sensitive
company information. They are not safe to put in a personal GitHub repository
just because it is private. The project privacy rule and `.gitignore` prohibit
committing registers, logs, exports, raw captures, or sensitive state.

## Before backing up

1. Follow company policy for data classification, approved storage, encryption,
   access controls, and retention. If no approved destination is known, do not
   make an extra copy; ask the appropriate company owner.
2. Choose an approved, access-controlled company-managed directory that is
   **outside this workbench and outside every Git working tree**.
3. Set `PM_STATE_BACKUP` to that directory for the current shell. Do not put
   credentials or private data in the setting itself.
4. Run `scripts/snapshot-state.sh`. It creates a unique dated snapshot of
   `registers/`, `reference/context/`, and `logs/`; it does not initialize,
   stage, commit, encrypt, or upload anything.

The script refuses to run without an explicit destination, and refuses a
destination inside this workbench or a Git repository. New snapshot directories
are created with restrictive local permissions; the script does not change
permissions on an existing destination. This is not encryption and does not
replace the destination's company controls. Confirm the snapshot location and
apply the organization's retention policy; the script does not prune snapshots.

## Restore and history

Treat each snapshot as a recovery copy, not as live synchronization. Restore
only after checking the destination, the snapshot date, and any newer local
changes. The restore tool only considers `registers/`, `reference/context/`,
and `logs/`, the same paths captured by the snapshot script. It restores
missing files; identical files are left alone. It never replaces a differing
file. A differing file or an unsafe symlink/hardlink anywhere in the relevant
snapshot or live target scope refuses the entire restore during preflight.

Recovery flow:

1. Confirm the approved backup location and select the exact dated snapshot
   directory created by `snapshot-state.sh`. Do not point at the backup parent.
2. Review the plan without changing anything:
   ```
   scripts/restore-state.sh --dry-run /approved/backup/YYYYMMDD-HHMMSS
   ```
3. If the preview is correct, run the same command without `--dry-run`:
   ```
   scripts/restore-state.sh /approved/backup/YYYYMMDD-HHMMSS
   ```
4. If preflight reports a conflict or unsafe path, the restore has not started.
   Review and reconcile newer work manually; do not delete or replace newer
   records merely to make the restore pass. Then re-run the preview.

Immutable history registers and dated outputs preserve events; current state
rows in commitments, risks, and initiatives reflect the latest approved state
(see `CLAUDE.md`, rule 7). Restore is not synchronization or a way to roll back
newer records.

If an approved non-Git backup location is not available, leave the backup
unconfigured. Do not substitute a personal repository or an unapproved cloud
folder.
