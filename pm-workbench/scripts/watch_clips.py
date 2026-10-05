#!/usr/bin/env python3
"""Move clips from Downloads into the live workspace (thin wrapper around pull_clips).

Preferred on macOS: bash scripts/install_clip_watcher.sh — launchd WatchPaths runs
pull_clips.py when the Downloads folder changes (no polling).

  python3 scripts/watch_clips.py --once     # single pull
  python3 scripts/watch_clips.py            # optional poll fallback (non-macOS / debug)
"""
from __future__ import annotations

import argparse
import os
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import pull_clips  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="live workspace root")
    parser.add_argument(
        "--interval",
        type=float,
        default=30.0,
        help="poll interval seconds for --poll fallback only (default 30)",
    )
    parser.add_argument("--once", action="store_true", help="pull once and exit (default)")
    parser.add_argument(
        "--poll",
        action="store_true",
        help="fallback: poll forever (prefer install_clip_watcher.sh WatchPaths on macOS)",
    )
    args = parser.parse_args(argv)

    root = pull_clips.resolve_live_root(args.root)

    def run_once():
        count, detail = pull_clips.pull_clips(root)
        if isinstance(detail, str):
            print(detail)
        else:
            for rel in detail:
                print("  +", rel)
            print(f"moved {count} clip(s) into {root}/inbox/")
        return 0

    if args.poll:
        print(
            f"polling Downloads/pm-workbench-inbox → {root}/inbox/ "
            f"(every {args.interval}s; Ctrl-C to stop). "
            "On macOS prefer: bash scripts/install_clip_watcher.sh"
        )
        while True:
            count, detail = pull_clips.pull_clips(root)
            if not isinstance(detail, str) and count:
                for rel in detail:
                    print("  +", rel)
                print(f"moved {count} clip(s)")
            time.sleep(max(5.0, args.interval))

    return run_once()


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nstopped")
        sys.exit(0)
