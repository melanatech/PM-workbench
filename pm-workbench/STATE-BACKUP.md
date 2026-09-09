# State backup & retention

Registers and working state (`registers/`, `reference/context/`, `logs/`) are the
system's durable memory. They need a backup story separate from the
version-controlled workflow logic.

## Convention (end-of-session snapshot, not live sync)
- At the end of a working session (or on demand), snapshot state to a **personal
  GitHub repo you control** — NOT a live per-write sync (that invites CSV merge
  conflicts and noise). One commit captures the day's accumulated registers.
- Suggested: a private `pm-workbench-state` repo, pushed via
  `scripts/snapshot-state.sh` (stub included). The workflow folder's own logic
  stays in its own repo; state is backed up separately so sensitive working data
  isn't entangled with shareable workflow code.
- Retention: keep snapshots; they double as an audit trail and a recovery point
  if a register is corrupted or a bad edit lands.

## Why not live sync
Every command already shows its diffs and writes append-only CSVs; a daily
snapshot is enough to never lose more than a session, without turning every
`/quick-close` into a git operation.
