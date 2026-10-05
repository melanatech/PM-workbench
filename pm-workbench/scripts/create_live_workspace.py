#!/usr/bin/env python3
"""Create a non-git live workspace for daily Claude Code use.

Usage (from the repository root or from pm-workbench/):
  python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live
  python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live --dev-links
  python3 pm-workbench/scripts/create_live_workspace.py ~/pm-live --dry-run

Default: copy kit code into a fresh folder and create empty data directories.
--dev-links: symlink kit code back to this checkout so fixes land in git.
Never overwrites a non-empty destination. Standard library only.
"""
import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import workspace_layout as layout  # noqa: E402


def build_workspace(destination, *, dev_links=False, dry_run=False):
    dest = os.path.abspath(os.path.expanduser(destination))
    mode = "dev-links" if dev_links else "copy"

    if dry_run:
        print(f"Dry run for {dest} ({mode}):")

    if dev_links:
        linked = layout.create_dev_links(dest, dry_run=dry_run)
        if dry_run:
            for name in linked:
                print(f"  link {name}")
        else:
            print(f"Created dev-links workspace at {dest}")
            print(f"  linked {len(linked)} kit path(s) to {layout.KIT_ROOT}")
    else:
        layout.copy_code_only(dest, dry_run=dry_run)
        if dry_run:
            print(f"  copy kit code from {layout.KIT_ROOT}")
        else:
            print(f"Created copy workspace at {dest}")

    data_dirs = layout.create_data_dirs(dest, dry_run=dry_run)
    registers = layout.seed_empty_registers(dest, dry_run=dry_run)
    reference = layout.seed_reference_starter(dest, dry_run=dry_run)

    # Data paths must stay real directories (hooks refuse symlink writes).
    top_data = sorted({p.split("/")[0] for p in layout.DATA_DIRS})
    if not dry_run:
        layout.ensure_not_symlink_tree(dest, top_data)

    if dry_run:
        for relative in data_dirs:
            print(f"  mkdir {relative}")
        for relative in registers:
            print(f"  seed {relative}")
        for relative in reference:
            print(f"  copy {relative}")
        layout.next_steps(dest, mode)
        return 0

    print(f"  data dirs: {len(data_dirs)}")
    print(f"  registers/logs seeded: {len(registers)}")
    print(f"  reference starter files: {len(reference)}")
    layout.write_live_root_marker(dest)
    layout.next_steps(dest, mode)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "destination",
        help="empty directory for the live workspace (for example: ~/pm-live)",
    )
    parser.add_argument(
        "--dev-links",
        action="store_true",
        help="symlink kit code to this checkout instead of copying (contributors)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the plan without writing",
    )
    args = parser.parse_args(argv)
    try:
        return build_workspace(
            args.destination, dev_links=args.dev_links, dry_run=args.dry_run
        )
    except (OSError, ValueError) as error:
        print(f"Could not create live workspace: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
