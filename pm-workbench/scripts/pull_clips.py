#!/usr/bin/env python3
"""Move clips saved by the Workbench Clipper (Downloads/pm-workbench-inbox/<category>/*)
into <live-root>/inbox/<category>/. Cross-platform (macOS, Windows, Linux). Idempotent.

Chrome extensions cannot write outside the browser Downloads folder. This script is the
bridge into the live workspace.

Preferred path (no Full Disk Access): run from Claude Code via `/capture process-inbox`
(step 0) or ask Claude / Terminal to run `python3 scripts/pull_clips.py`. That uses your
interactive session's access to Downloads.

Optional: scripts/install_clip_watcher.sh (LaunchAgent). On macOS the background job often
needs Full Disk Access for /usr/bin/python3 — only install that if you want auto-move
without opening Claude.

Live root resolution (first match):
  1. --root / path argument
  2. PM_LIVE_ROOT environment variable
  3. ~/.pm-workbench/live-root (one-line path written by create_live_workspace.py)
  4. directory containing this script's parent (the workspace this script lives in)
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys

CATEGORIES = ("discovery", "competitive", "meetings", "metrics", "documents", "captures")

# Meetings are transcript text only — do not pull leftover viewport PNGs into inbox.
SKIP_PNG_CATEGORIES = frozenset({"meetings"})

# Never move browser/OS junk. Everything else under a category folder is a clip —
# board CSVs, PDFs, docs — not only .md (that filter left documents stuck in Downloads).
SKIP_NAMES = frozenset({".DS_Store", "Thumbs.db", "desktop.ini"})
SKIP_SUFFIXES = (".crdownload", ".tmp", ".partial", ".download")


def _should_skip_name(name: str) -> bool:
    if name in SKIP_NAMES or name.startswith("."):
        return True
    lower = name.lower()
    return any(lower.endswith(suf) for suf in SKIP_SUFFIXES)


def clip_sources():
    home = os.path.expanduser("~")
    return [
        os.path.join(home, "Downloads", "pm-workbench-inbox"),
        os.path.join(home, "OneDrive", "Downloads", "pm-workbench-inbox"),
    ]


def resolve_live_root(explicit=None):
    if explicit:
        return os.path.abspath(os.path.expanduser(explicit))
    env = os.environ.get("PM_LIVE_ROOT")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    marker = os.path.join(os.path.expanduser("~"), ".pm-workbench", "live-root")
    if os.path.isfile(marker):
        with open(marker, encoding="utf-8") as handle:
            lines = [ln.strip() for ln in handle if ln.strip() and not ln.strip().startswith("#")]
        if lines:
            return os.path.abspath(os.path.expanduser(lines[0]))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _notify_macos(message: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        import subprocess
        subprocess.run(
            [
                "osascript", "-e",
                f'display notification {message!r} with title "PM Workbench clip watcher"',
            ],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def pull_clips(live_root, *, dry_run=False):
    src = next((c for c in clip_sources() if os.path.isdir(c)), None)
    if not src:
        return 0, "no clips folder found (expected ~/Downloads/pm-workbench-inbox/)"

    try:
        categories = sorted(os.listdir(src))
    except PermissionError:
        msg = (
            f"macOS blocked reading {src} (PermissionError). "
            "From Claude Code or Terminal run: python3 scripts/pull_clips.py "
            "(approve the Bash prompt). Full Disk Access is only needed for the "
            "optional LaunchAgent watcher, not for this interactive pull."
        )
        _notify_macos("Blocked from Downloads — run pull_clips from Claude Code or Terminal")
        return 0, msg

    moved = []
    skipped_png = 0
    leftover = []  # files we saw but did not move (should stay empty except junk)
    for cat in categories:
        d = os.path.join(src, cat)
        if not os.path.isdir(d):
            continue
        dest_cat = cat if cat in CATEGORIES else "captures"
        dest = os.path.join(live_root, "inbox", dest_cat)
        if not dry_run:
            os.makedirs(dest, exist_ok=True)
        try:
            names = sorted(os.listdir(d))
        except PermissionError:
            msg = (
                f"macOS blocked reading {d} (PermissionError). "
                "Run python3 scripts/pull_clips.py from Claude Code or Terminal."
            )
            _notify_macos("Blocked from Downloads — run pull_clips from Claude Code or Terminal")
            return len(moved), (moved if moved else msg)

        for name in names:
            if _should_skip_name(name):
                continue
            if name.endswith(".png") and dest_cat in SKIP_PNG_CATEGORIES:
                # Drop meeting screenshots (clipper 0.3.1+ no longer writes them).
                if not dry_run:
                    try:
                        os.remove(os.path.join(d, name))
                    except OSError:
                        pass
                skipped_png += 1
                continue
            from_path = os.path.join(d, name)
            if not os.path.isfile(from_path):
                continue
            to_path = os.path.join(dest, name)
            if dry_run:
                moved.append(os.path.relpath(to_path, live_root))
                continue
            if os.path.exists(to_path):
                base, ext = os.path.splitext(name)
                n = 1
                while os.path.exists(to_path):
                    to_path = os.path.join(dest, f"{base}-{n}{ext}")
                    n += 1
            try:
                shutil.move(from_path, to_path)
                moved.append(os.path.relpath(to_path, live_root))
            except OSError as err:
                leftover.append(f"{cat}/{name} ({err})")
    if leftover and not moved:
        return 0, "could not move: " + "; ".join(leftover)
    if skipped_png and not moved:
        return 0, f"removed {skipped_png} meeting screenshot(s); no clips to move"
    return len(moved), moved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="live workspace root (default: PM_LIVE_ROOT / marker / script parent)")
    parser.add_argument("--dry-run", action="store_true", help="list moves without writing")
    args = parser.parse_args(argv)

    root = resolve_live_root(args.root)
    count, detail = pull_clips(root, dry_run=args.dry_run)
    if isinstance(detail, str):
        print(detail, file=sys.stderr if "PermissionError" in detail or "blocked" in detail.lower() else sys.stdout)
        return 2 if "PermissionError" in detail or "blocked" in detail.lower() else 0
    for rel in detail:
        print("  +", rel)
    prefix = "would move" if args.dry_run else "moved"
    print(f"{prefix} {count} clip(s) into {root}/inbox/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
