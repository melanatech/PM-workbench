#!/usr/bin/env python3
"""Load fictional fixtures without silently replacing existing workspace files.

Usage:
  python3 scripts/load_fixture.py lumenly
  python3 scripts/load_fixture.py lumenly --dry-run
  python3 scripts/load_fixture.py lumenly --isolate /tmp/pm-workbench-lumenly

In the live workspace, loading is all-or-nothing: differing existing files are
reported and left untouched unless --overwrite is explicitly supplied. The
--isolate mode makes a code-only copy, loads the fixture there, and leaves the
source workspace unchanged. The isolated copy can be removed when finished.
"""
import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import workspace_layout as layout  # noqa: E402

ROOT = layout.KIT_ROOT
ROOT_MUTABLE_DIRS = layout.ROOT_MUTABLE_DIRS
INVENTORY_SKIP = (".git/", "node_modules/", ".claude/", "fixtures/", "scripts/",
                  "tools/", "tests/")
PROJECT_FILES = {
    "AGENTS.md", "CLAUDE.md", "CONNECTIONS.md", "EVOLVING.md", "SCHEDULING.md",
    "SETUP.md", "SKILLS.md", "SOURCE-POLICY.md", "START HERE.md", "STATE-BACKUP.md",
    "BACKLOG.md", "NEW-USER-SETUP.md",
    "Capture Clipboard.command", "Run PM Workflow.command", ".gitignore",
}


def fixture_files(fixture_root):
    """Yield (source, relative path) pairs without following symlinks."""
    for directory, dirs, files in os.walk(fixture_root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not os.path.islink(os.path.join(directory, d)))
        for filename in sorted(files):
            source = os.path.join(directory, filename)
            if os.path.islink(source):
                raise ValueError(f"fixture contains a symlink: {source}")
            relative = os.path.relpath(source, fixture_root)
            if relative == "README.md":
                continue
            yield source, relative


def conflicts_for(files, destination):
    conflicts, identical, new, unsafe = [], [], [], []
    for source, relative in files:
        target = os.path.join(destination, relative)
        parent = destination
        for component in relative.split("/")[:-1]:
            parent = os.path.join(parent, component)
            if os.path.islink(parent):
                unsafe.append(relative)
                break
        if relative in unsafe:
            continue
        if os.path.islink(target):
            unsafe.append(relative)
            continue
        if not os.path.lexists(target):
            new.append(relative)
        elif not os.path.isfile(target):
            unsafe.append(relative)
        elif os.stat(target).st_nlink > 1:
            unsafe.append(relative)
        else:
            with open(source, "rb") as src, open(target, "rb") as dst:
                (identical if src.read() == dst.read() else conflicts).append(relative)
    return conflicts, identical, new, unsafe


def run_log_rows(root):
    path = os.path.join(root, "logs", "run-log.csv")
    try:
        with open(path, newline="", encoding="utf-8") as handle:
            return max(0, sum(1 for row in csv.reader(handle) if row) - 1)
    except (OSError, csv.Error):
        return 0


def file_inventory(root):
    inventory = {}
    for directory, dirs, files in os.walk(root):
        relative_dir = os.path.relpath(directory, root).replace(os.sep, "/")
        relative_dir = "" if relative_dir == "." else relative_dir + "/"
        if any(relative_dir.startswith(prefix) for prefix in INVENTORY_SKIP):
            dirs[:] = []
            continue
        for filename in files:
            relative = relative_dir + filename
            if relative == "state/.last-check" or (
                relative_dir == "" and relative in PROJECT_FILES
            ):
                continue
            digest = hashlib.sha256()
            try:
                with open(os.path.join(directory, filename), "rb") as handle:
                    for chunk in iter(lambda: handle.read(65536), b""):
                        digest.update(chunk)
            except OSError:
                continue
            inventory[relative] = digest.hexdigest()
    return inventory


def write_check_baseline(root, kind):
    state = os.path.join(root, "state")
    if os.path.islink(state):
        raise ValueError("state/ is a symlink; refusing to write the check baseline")
    os.makedirs(state, exist_ok=True)
    marker = os.path.join(state, ".last-check")
    if os.path.islink(marker) or (
        os.path.lexists(marker)
        and (not os.path.isfile(marker) or os.stat(marker).st_nlink > 1)
    ):
        raise ValueError("state/.last-check is not a safe regular file")
    with open(marker, "w", encoding="utf-8") as handle:
        json.dump({
            "kind": kind,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "cutoff": time.time(),
            "run_log_rows": run_log_rows(root),
            "inventory": file_inventory(root),
        }, handle)
    os.utime(marker, None)


def copy_code_only(destination):
    """Copy the kit without carrying local/raw working data into an isolate."""
    return layout.copy_code_only(destination, kit_root=ROOT)


def load_into(fixture_root, destination, overwrite, dry_run=False):
    files = list(fixture_files(fixture_root))
    conflicts, identical, new, unsafe = conflicts_for(files, destination)
    state_dir = os.path.join(destination, "state")
    marker = os.path.join(state_dir, ".last-check")
    if os.path.islink(state_dir) or os.path.islink(marker) or (
        os.path.lexists(marker)
        and (not os.path.isfile(marker) or os.stat(marker).st_nlink > 1)
    ):
        unsafe.append("state/.last-check")
    if unsafe:
        print("Refusing to write through symlinks, non-regular files, or hard-linked targets.", file=sys.stderr)
        for relative in unsafe:
            print(f"  unsafe target: {relative}", file=sys.stderr)
        print("No fixture files were copied.", file=sys.stderr)
        return 2
    if conflicts and not overwrite:
        print("Refusing to load: existing, different files would be replaced.", file=sys.stderr)
        for relative in conflicts:
            print(f"  conflict: {relative}", file=sys.stderr)
        print("No fixture files were copied. Use a disposable workspace (--isolate), "
              "or explicitly pass --overwrite only when replacing these files is intended.",
              file=sys.stderr)
        return 2

    if dry_run:
        print(f"Fixture plan for {os.path.abspath(destination)}:")
        for relative in new:
            print(f"  + {relative}")
        for relative in identical:
            print(f"  = unchanged: {relative}")
        for relative in conflicts:
            print(f"  ! replace: {relative}")
        if not new and not conflicts:
            print("  all fixture files already match")
        return 0

    for source, relative in files:
        target = os.path.join(destination, relative)
        if relative in identical:
            continue
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(source, target)

    # The marker intentionally establishes the fixture as the checker's baseline.
    write_check_baseline(destination, "fixture loaded")
    print(f"Loaded fictional fixture into {os.path.abspath(destination)}.")
    print(f"  copied: {len(new) + len(conflicts)} file(s); already identical: {len(identical)}")
    print("  checker baseline reset; run a workflow before running scripts/check_run.py")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", help="fixture name under fixtures/ (for example: lumenly)")
    parser.add_argument("--overwrite", action="store_true",
                        help="explicitly replace differing fixture target files in this workspace")
    parser.add_argument("--dry-run", action="store_true", help="show the plan without writing")
    parser.add_argument("--isolate", metavar="PATH",
                        help="copy code only to a new, separate workspace and load the fixture there")
    args = parser.parse_args()

    if args.isolate and (args.overwrite or args.dry_run):
        parser.error("--isolate cannot be combined with --overwrite or --dry-run")

    fixture_root = os.path.abspath(os.path.join(ROOT, "fixtures", args.fixture))
    fixtures_dir = os.path.join(ROOT, "fixtures")
    if os.path.commonpath([fixtures_dir, fixture_root]) != fixtures_dir or not os.path.isdir(fixture_root):
        parser.error(f"unknown fixture: {args.fixture!r}")

    destination = ROOT
    isolated = False
    try:
        if args.isolate:
            destination = copy_code_only(args.isolate)
            isolated = True
        result = load_into(fixture_root, destination, overwrite=(args.overwrite or isolated),
                           dry_run=args.dry_run)
    except (OSError, ValueError) as error:
        print(f"Could not load fixture: {error}", file=sys.stderr)
        return 2
    if isolated and result == 0:
        print("This isolated copy excludes root-level working data and raw captures from the source.")
        print("To discard the test, remove the isolated directory after confirming its path.")
    return result


if __name__ == "__main__":
    sys.exit(main())
