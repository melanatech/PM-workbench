#!/usr/bin/env python3
"""Single intake gate: pull Downloads clips → report what is waiting in inbox.

Always run this before claiming "nothing to process."

Usage:
  python3 scripts/intake_status.py --root ~/pm-live
  python3 scripts/intake_status.py --root ~/pm-live --pull   # default: pull
  python3 scripts/intake_status.py --root ~/pm-live --no-pull

Exit codes:
  0 — printed status (may still have pending=0)
  2 — could not resolve a usable live root / pull blocked
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import pull_clips  # noqa: E402


def _pending_inbox(live_root: Path) -> list[str]:
    processed: set[str] = set()
    pf = live_root / "state" / "processed-files.txt"
    if pf.is_file():
        processed = {ln.strip() for ln in pf.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()}

    pending: list[str] = []
    inbox = live_root / "inbox"
    if not inbox.is_dir():
        return pending
    for path in sorted(inbox.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or path.name in pull_clips.SKIP_NAMES:
            continue
        rel = path.relative_to(live_root).as_posix()
        name = path.name
        if name in processed or rel in processed:
            continue
        if any(name == Path(p).name or p.endswith(name) or p.endswith(rel) for p in processed):
            continue
        pending.append(rel)
    return pending


def _downloads_pending() -> list[str]:
    out: list[str] = []
    for src in pull_clips.clip_sources():
        if not os.path.isdir(src):
            continue
        for cat in sorted(os.listdir(src)):
            d = os.path.join(src, cat)
            if not os.path.isdir(d):
                continue
            try:
                names = os.listdir(d)
            except PermissionError:
                return [f"BLOCKED reading {d}"]
            for name in names:
                if pull_clips._should_skip_name(name):
                    continue
                fp = os.path.join(d, name)
                if os.path.isfile(fp):
                    out.append(f"{cat}/{name}")
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="live workspace (required if marker is wrong/missing)")
    parser.add_argument("--pull", dest="do_pull", action="store_true", default=True)
    parser.add_argument("--no-pull", dest="do_pull", action="store_false")
    args = parser.parse_args(argv)

    try:
        root = Path(pull_clips.resolve_live_root(args.root))
    except ValueError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        print(
            "Fix: python3 scripts/intake_status.py --root ~/pm-live\n"
            "  or: echo \"$HOME/pm-live\" > ~/.pm-workbench/live-root",
            file=sys.stderr,
        )
        return 2

    print(f"live_root={root}")

    before_dl = _downloads_pending()
    print(f"downloads_pending_before_pull={len(before_dl)}")
    for rel in before_dl[:30]:
        print(f"  downloads: {rel}")
    if len(before_dl) > 30:
        print(f"  … +{len(before_dl) - 30} more")

    if args.do_pull:
        count, detail = pull_clips.pull_clips(str(root))
        if isinstance(detail, str):
            print(f"pull: {detail}")
            if "PermissionError" in detail or "blocked" in detail.lower():
                return 2
        else:
            for rel in detail:
                print(f"  + {rel}")
            print(f"moved {count} clip(s) into {root}/inbox/")

    after_dl = _downloads_pending()
    pending = _pending_inbox(root)
    print(f"downloads_still_pending={len(after_dl)}")
    for rel in after_dl[:20]:
        print(f"  downloads: {rel}")
    print(f"inbox_unprocessed={len(pending)}")
    for rel in pending:
        print(f"  inbox: {rel}")

    if pending or after_dl:
        print("STATUS: work waiting — process these files; do NOT say inbox is empty")
    else:
        print("STATUS: nothing waiting in Downloads or unprocessed inbox")
    return 0


if __name__ == "__main__":
    sys.exit(main())
