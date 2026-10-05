#!/usr/bin/env python3
"""Local git checkpoints for a prototype under prototypes/[name]/.

Does not push. Only touches the prototype directory's own git repo
(Step 2 of prototype-build initializes it). The label→commit index lives
outside that repo so restores cannot erase newer checkpoint history:

  logs/prototype-checkpoints/[name].md

Usage (from live workspace root):
  python3 scripts/prototype_checkpoint.py --path prototypes/foo --label after-scaffold
  python3 scripts/prototype_checkpoint.py --path prototypes/foo --label after-qa
  python3 scripts/prototype_checkpoint.py --path prototypes/foo --list
  python3 scripts/prototype_checkpoint.py --path prototypes/foo --restore after-qa
  python3 scripts/prototype_checkpoint.py --path prototypes/foo --restore abc1234
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone


def run(cmd, cwd, check=True):
    return subprocess.run(
        cmd, cwd=cwd, check=check, capture_output=True, text=True
    )


def workspace_root_from_proto(proto: str) -> str:
    """prototypes/[name] → parent of prototypes/ (live workspace)."""
    parts = os.path.abspath(proto).split(os.sep)
    if "prototypes" not in parts:
        raise ValueError("path not under prototypes/")
    idx = parts.index("prototypes")
    root = os.sep.join(parts[:idx])
    return root if root else os.sep


def log_path_for(proto: str) -> str:
    root = workspace_root_from_proto(proto)
    name = os.path.basename(os.path.abspath(proto))
    directory = os.path.join(root, "logs", "prototype-checkpoints")
    os.makedirs(directory, exist_ok=True)
    return os.path.join(directory, f"{name}.md")


def ensure_git(proto: str) -> None:
    if os.path.isdir(os.path.join(proto, ".git")):
        return
    run(["git", "init"], proto)
    ignore = os.path.join(proto, ".gitignore")
    if not os.path.exists(ignore):
        with open(ignore, "w", encoding="utf-8") as handle:
            handle.write(
                "node_modules/\ndist/\nbuild/\n.expo/\n.next/\n*.log\n.DS_Store\n"
            )


def append_log(proto: str, label: str, commit: str, message: str) -> str:
    path = log_path_for(proto)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = f"- `{stamp}` **{label}** `{commit[:12]}` — {message}\n"
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(
                f"# Checkpoints: {os.path.basename(proto)}\n\n"
                "Local git commits inside the prototype folder only "
                "(never pushed by the kit). Restore:\n\n"
                f"`python3 scripts/prototype_checkpoint.py "
                f"--path prototypes/{os.path.basename(proto)} "
                f"--restore <label-or-hash>`\n\n"
                "## Log\n\n"
            )
    with open(path, encoding="utf-8") as handle:
        prev = handle.read()
    if "## Log\n" not in prev:
        prev = prev.rstrip() + "\n\n## Log\n\n"
    head, _, tail = prev.partition("## Log\n")
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(head + "## Log\n\n" + line + tail.lstrip("\n"))
    return path


def find_commit_for_label(proto: str, label: str) -> str | None:
    path = log_path_for(proto)
    if not os.path.exists(path):
        return None
    needle = f"**{label}** `"
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if needle in line:
                try:
                    return line.split(needle, 1)[1].split("`", 1)[0]
                except IndexError:
                    continue
    return None


def cmd_checkpoint(proto: str, label: str, message: str | None) -> int:
    ensure_git(proto)
    msg = message or f"checkpoint: {label}"
    run(["git", "add", "-A"], proto)
    status = run(["git", "status", "--porcelain"], proto)
    if not status.stdout.strip():
        run(["git", "commit", "--allow-empty", "-m", msg], proto)
    else:
        run(["git", "commit", "-m", msg], proto)
    commit = run(["git", "rev-parse", "HEAD"], proto).stdout.strip()
    path = append_log(proto, label, commit, msg)
    print(f"checkpoint {label} → {commit[:7]} ({proto})")
    print(f"log {path}")
    return 0


def cmd_list(proto: str) -> int:
    path = log_path_for(proto)
    if not os.path.exists(path):
        print("No checkpoint log yet.")
        return 0
    print(open(path, encoding="utf-8").read())
    return 0


def resolve_commit(proto: str, target: str) -> str | None:
    found = find_commit_for_label(proto, target)
    if found:
        target = found
    probe = run(["git", "rev-parse", "--verify", target], proto, check=False)
    if probe.returncode != 0:
        return None
    return probe.stdout.strip()


def cmd_restore(proto: str, target: str, force: bool) -> int:
    ensure_git(proto)
    full = resolve_commit(proto, target)
    if not full:
        print(f"Unknown label or commit: {target}", file=sys.stderr)
        return 1
    dirty = run(["git", "status", "--porcelain"], proto).stdout.strip()
    if dirty and not force:
        print(
            "Working tree is dirty. Commit, or restore with --force "
            "(discards uncommitted changes).",
            file=sys.stderr,
        )
        return 2
    if force:
        run(["git", "checkout", "-f", full], proto)
    else:
        run(["git", "checkout", full], proto)
    print(f"restored {proto} → {full[:7]}")
    print("Detached HEAD. To keep editing:")
    print(f"  cd {proto} && git switch -c resume-{full[:7]}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--path",
        required=True,
        help="prototype directory, e.g. prototypes/my-flow",
    )
    parser.add_argument("--label", help="checkpoint label, e.g. after-qa")
    parser.add_argument("--message", help="optional commit message")
    parser.add_argument("--list", action="store_true", help="print checkpoint log")
    parser.add_argument(
        "--restore",
        metavar="LABEL_OR_HASH",
        help="checkout a prior checkpoint (label or git hash)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="with --restore, discard uncommitted changes",
    )
    args = parser.parse_args(argv)

    proto = os.path.abspath(args.path)
    if not os.path.isdir(proto):
        print(f"Not a directory: {proto}", file=sys.stderr)
        return 1
    if "prototypes" not in proto.replace("\\", "/").split("/"):
        print("Refusing: --path must be under prototypes/", file=sys.stderr)
        return 2

    if args.list:
        return cmd_list(proto)
    if args.restore:
        return cmd_restore(proto, args.restore, args.force)
    if not args.label:
        print("Need --label, --list, or --restore", file=sys.stderr)
        return 1
    return cmd_checkpoint(proto, args.label, args.message)


if __name__ == "__main__":
    sys.exit(main())
