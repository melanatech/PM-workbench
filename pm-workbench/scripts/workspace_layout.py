#!/usr/bin/env python3
"""Shared layout helpers for isolated fixtures and live workspaces.

Standard library only. Used by load_fixture.py and create_live_workspace.py so
copy/preflight rules stay in one place.
"""
import os
import shutil
import sys

# Kit root: the pm-workbench/ directory that contains scripts/ and .claude/
KIT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Working-data directories that must never be copied from a source that may
# contain real captures, registers, or secrets.
ROOT_MUTABLE_DIRS = {
    "inbox", "archive", "state", "logs", "registers", "outputs", "repos",
    "learning", "drafts", "prototypes", "roadmap", "reference",
    "node_modules", "browser-profiles", "__pycache__",
}

# Real directories every live workspace needs (created empty; not symlinks).
DATA_DIRS = (
    "inbox/meetings", "inbox/captures", "inbox/exports", "inbox/documents",
    "inbox/competitive",
    "archive", "state", "state/competitive", "logs", "registers",
    "outputs/daily", "outputs", "outputs/monthly",
    "outputs/todo-proposals", "outputs/todo-drafts",
    "repos", "learning", "drafts", "prototypes", "roadmap", "reference/context",
    "reference/templates", "reference/metric-definitions", "reference/user-research",
)

# Kit paths that --dev-links may symlink back to KIT_ROOT.
LINK_ENTRIES = (
    ".claude", "scripts", "tests", "tools", "fixtures",
    "AGENTS.md", "CLAUDE.md", "CONNECTIONS.md", "EVOLVING.md", "SCHEDULING.md",
    "SETUP.md", "SKILLS.md", "SOURCE-POLICY.md", "START HERE.md", "STATE-BACKUP.md",
    "BACKLOG.md", "NEW-USER-SETUP.md",
    "Capture Clipboard.command", "Run PM Workflow.command", ".gitignore",
)

# Names ignored at every level when copying kit code.
ALWAYS_IGNORE = {
    ".git", ".mcp.json", ".DS_Store",
    "CLAUDE.local.md", "settings.local.json",
    "__pycache__", "node_modules",
}

REGISTER_HEADERS = {
    "decisions.csv": "id,date,decision,made_by,source_link,affects",
    "commitments.csv": "id,description,owner,due_date,audience,source,status,last_updated",
    "risks.csv": "id,date_raised,risk,severity,mitigation,status,source",
    "todos.csv": (
        "id,description,owner,due_date,priority,status,initiative,blocks,links,"
        "origin,source,created,last_updated,note"
    ),
    "initiatives.csv": (
        "id,name,stage,prd,prototype,experiment,launch,related_okr,"
        "related_decisions,related_risks,last_updated,notes"
    ),
    "evidence.csv": (
        "evidence_id,capture_date,source_date,source_app,source_url,account,"
        "user_role,segment,workflow_stage,exact_observation,interpreted_problem,"
        "workaround,severity,frequency_signal,business_relevance,related_feature,"
        "related_okr,evidence_type,confidence"
    ),
    "research-participants.csv": (
        "id,name_or_alias,role,segment,last_contacted,outcome,source,notes"
    ),
}


def abspath_outside_kit(destination, kit_root=None):
    """Return an absolute destination that is not inside the kit tree."""
    root = os.path.abspath(kit_root or KIT_ROOT)
    target = os.path.abspath(destination)
    try:
        if os.path.commonpath([root, target]) == root:
            raise ValueError(
                f"destination must be outside the kit ({root}); got {target}"
            )
    except ValueError as error:
        # commonpath raises when paths are on different drives (Windows)
        if "outside the kit" in str(error):
            raise
    return target


def require_empty_destination(destination):
    """Refuse a path that already exists with contents. Empty dirs are removed."""
    target = os.path.abspath(destination)
    if os.path.lexists(target):
        if not os.path.isdir(target) or os.listdir(target):
            raise ValueError(
                f"destination must not exist or must be empty: {target}"
            )
        os.rmdir(target)
    return target


def copy_code_only(destination, kit_root=None, dry_run=False):
    """Copy kit logic without root-level working data or local secrets."""
    root = os.path.abspath(kit_root or KIT_ROOT)
    target = abspath_outside_kit(destination, root)
    require_empty_destination(target)

    def ignore(directory, names):
        ignored = {
            name for name in names
            if name.startswith(".env") or name in ALWAYS_IGNORE
        }
        if os.path.abspath(directory) == root:
            ignored.update(name for name in names if name in ROOT_MUTABLE_DIRS)
        return ignored

    if dry_run:
        print(f"would copy kit code from {root} -> {target}")
        return target

    os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
    shutil.copytree(root, target, ignore=ignore)
    return target


def create_data_dirs(destination, dry_run=False):
    """Create real (non-symlink) working-data directories under destination."""
    target = os.path.abspath(destination)
    created = []
    for relative in DATA_DIRS:
        path = os.path.join(target, relative)
        if os.path.islink(path):
            raise ValueError(f"refusing to use symlinked data path: {relative}")
        created.append(relative)
        if not dry_run:
            os.makedirs(path, exist_ok=True)
    return created


def seed_empty_registers(destination, dry_run=False):
    """Write header-only register CSVs and an empty run log."""
    target = os.path.abspath(destination)
    written = []
    registers = os.path.join(target, "registers")
    logs = os.path.join(target, "logs")
    if not dry_run:
        os.makedirs(registers, exist_ok=True)
        os.makedirs(logs, exist_ok=True)
    for name, header in REGISTER_HEADERS.items():
        relative = f"registers/{name}"
        path = os.path.join(target, relative)
        if os.path.lexists(path) and (os.path.islink(path) or not os.path.isfile(path)):
            raise ValueError(f"refusing unsafe register path: {relative}")
        written.append(relative)
        if not dry_run and not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(header + "\n")
    run_log = "logs/run-log.csv"
    written.append(run_log)
    if not dry_run and not os.path.exists(os.path.join(target, run_log)):
        with open(os.path.join(target, run_log), "w", encoding="utf-8") as handle:
            handle.write("timestamp,workflow,approx_duration,success,note\n")
    return written


def seed_reference_starter(destination, kit_root=None, dry_run=False):
    """Copy non-secret starter reference files; never overwrite existing ones.

    Also seeds `learning/README.md` (data dir, not under reference/) so a new
    live workspace knows capture will write `learning/[area].md`.
    """
    root = os.path.abspath(kit_root or KIT_ROOT)
    target = os.path.abspath(destination)
    source_ref = os.path.join(root, "reference")
    dest_ref = os.path.join(target, "reference")
    copied = []
    if not os.path.isdir(source_ref):
        return copied
    for directory, _dirs, files in os.walk(source_ref, followlinks=False):
        for filename in files:
            source = os.path.join(directory, filename)
            if os.path.islink(source):
                continue
            relative = os.path.relpath(source, source_ref)
            dest = os.path.join(dest_ref, relative)
            if os.path.lexists(dest):
                continue
            copied.append(f"reference/{relative.replace(os.sep, '/')}")
            if dry_run:
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(source, dest)

    # learning/ is a mutable data dir (empty on create); drop the README once.
    learning_readme_src = os.path.join(root, "learning", "README.md")
    learning_readme_dest = os.path.join(target, "learning", "README.md")
    if os.path.isfile(learning_readme_src) and not os.path.lexists(learning_readme_dest):
        copied.append("learning/README.md")
        if not dry_run:
            os.makedirs(os.path.dirname(learning_readme_dest), exist_ok=True)
            shutil.copyfile(learning_readme_src, learning_readme_dest)
    return copied


def create_dev_links(destination, kit_root=None, dry_run=False):
    """Symlink kit code into destination so edits land in the source checkout."""
    root = os.path.abspath(kit_root or KIT_ROOT)
    target = abspath_outside_kit(destination, root)
    if not dry_run:
        require_empty_destination(target)
        os.makedirs(target, exist_ok=True)
    elif not os.path.isdir(os.path.dirname(target) or "."):
        print(f"would create parent dirs for {target}")

    # Probe symlink support once.
    if not dry_run:
        probe = os.path.join(target, ".symlink-probe")
        try:
            os.symlink(root, probe)
        except OSError as error:
            try:
                os.rmdir(target)
            except OSError:
                pass
            raise ValueError(
                "this OS/user cannot create symlinks safely "
                f"({error}). Use copy mode without --dev-links."
            ) from error
        os.unlink(probe)

    linked = []
    for name in LINK_ENTRIES:
        source = os.path.join(root, name)
        if not os.path.lexists(source):
            continue
        dest = os.path.join(target, name)
        linked.append(name)
        if dry_run:
            print(f"would link {dest} -> {source}")
            continue
        if os.path.lexists(dest):
            raise ValueError(f"destination already has {name}")
        os.symlink(source, dest)
    return linked


def ensure_not_symlink_tree(destination, relative_paths):
    """Raise if any required data path is a symlink."""
    target = os.path.abspath(destination)
    for relative in relative_paths:
        path = os.path.join(target, relative.split("/")[0])
        if os.path.islink(path):
            raise ValueError(f"data path must be a real directory, not a symlink: {relative}")


def write_live_root_marker(destination):
    """Record the live workspace path so pull_clips / the clip watcher find it."""
    dest = os.path.abspath(destination)
    marker_dir = os.path.join(os.path.expanduser("~"), ".pm-workbench")
    os.makedirs(marker_dir, exist_ok=True)
    marker = os.path.join(marker_dir, "live-root")
    with open(marker, "w", encoding="utf-8") as handle:
        handle.write(dest + "\n")
    return marker


def next_steps(destination, mode):
    """Print the exact commands a new user should run next."""
    dest = os.path.abspath(destination)
    kit = KIT_ROOT
    print()
    print("Next steps:")
    print(f"  1. Open this folder in Claude Code (not the git repo root): {dest}")
    print("  2. Confirm the / menu lists: capture, brief, sync, discover, build, report, quick-close, todo")
    print(f"  3. From the git kit, isolate the fictional fixture:")
    print(f"       python3 {os.path.join(kit, 'scripts', 'load_fixture.py')} lumenly --isolate /tmp/pm-workbench-lumenly")
    print("     Open /tmp/pm-workbench-lumenly in Claude Code and run:")
    print("       /capture meeting-closeout inbox/meetings/2026-07-14-roadmap-review.txt")
    print("     Then: python3 scripts/check_run.py && python3 scripts/score_fixture.py")
    print(f"  4. Put private machine/company context in {os.path.join(dest, '.claude', 'CLAUDE.local.md')}")
    print(f"     (gitignored). Seed {os.path.join(dest, 'reference', 'links.csv')} only with approved links.")
    print(f"  5. Drop a real meeting file into {os.path.join(dest, 'inbox', 'meetings')} and run /capture.")
    print(f"  6. After clipping in Chrome: in Claude Code run /capture process-inbox")
    print(f"     (pulls from Downloads — no Full Disk Access needed). Optional watcher:")
    print(f"       bash {os.path.join(dest, 'scripts', 'install_clip_watcher.sh')}")
    print(f"  7. Read NEW-USER-SETUP.md for browser, scheduling, backup, and stub verification.")
    if mode == "dev-links":
        print("  Dev-links mode: kit edits in this folder change the git checkout. Commit from the repo.")
    else:
        print("  Copy mode: kit code is a snapshot. Pull/rebase the git clone and re-run this script")
        print("  into a new empty folder when you want kit updates (this script never overwrites).")
