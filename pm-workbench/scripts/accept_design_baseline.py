#!/usr/bin/env python3
"""Accept the current HTML as the approved design baseline.

Copies ``<html>`` over ``state/hooks/design-baselines/<rel-path>`` and appends
an acceptance row to ``state/hooks/hook-log.jsonl``.

**Only run when the PM explicitly asks to accept a redesign.** Agents must not
call this to clear a failing gate after an unapproved design change.

Usage (from the live workspace root):
  python3 scripts/accept_design_baseline.py <file.html>

Note: ``scripts/`` may be a symlink into the kit. This script locates the live
root via cwd (or ``--root``), not via ``__file__``.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _find_live_root(explicit: str | None) -> Path:
    if explicit:
        root = Path(explicit).expanduser().resolve()
        if not (root / ".cursor" / "hooks" / "_common.py").is_file():
            raise SystemExit(f"error: --root {root} has no .cursor/hooks/_common.py")
        return root
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".cursor" / "hooks" / "_common.py").is_file():
            return candidate
    raise SystemExit(
        "error: run from the live workspace (e.g. ~/pm-live) or pass --root"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file", help="HTML artifact whose current design is approved")
    ap.add_argument(
        "--root",
        help="Live workspace root (default: discover from cwd)",
    )
    args = ap.parse_args(argv)

    root = _find_live_root(args.root)
    hooks_dir = root / ".cursor" / "hooks"
    sys.path.insert(0, str(hooks_dir))
    from _common import (  # noqa: E402
        log_decision,
        rel_to_root,
        write_design_baseline,
    )

    path = Path(args.file)
    if not path.is_absolute():
        path = (root / path).resolve()
    else:
        path = path.resolve()
    if not path.is_file():
        print(f"error: {path} not found", file=sys.stderr)
        return 2
    if path.suffix.lower() not in {".html", ".htm"}:
        print(f"error: {path} is not HTML", file=sys.stderr)
        return 2

    rel = rel_to_root(path, root)
    baseline = write_design_baseline(root, path)
    baseline_rel = rel_to_root(baseline, root)
    log_decision(
        root,
        {
            "hook": "accept_design_baseline",
            "decision": "accepted",
            "path": rel,
            "baseline": baseline_rel,
            "reason": "PM explicitly accepted redesign baseline",
        },
    )
    print(f"Accepted design baseline for {rel}")
    print(f"  -> {baseline_rel}")
    print("Logged to state/hooks/hook-log.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
