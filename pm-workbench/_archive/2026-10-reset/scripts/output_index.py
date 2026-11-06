#!/usr/bin/env python3
"""Build the end-of-batch Output index, and detect a reply that skipped it.

A multi-draft close lists every file it just wrote under the heading
``## Output index``. Pointing at a single report file is not the index.
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\((outputs/[^)\s]+)\)|`(outputs/[^`\s]+)`")
HEADING = "## Output index"
MIN_LINKS = 4


def reply_paths(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in LINK_RE.finditer(text or ""):
        path = match.group(1) or match.group(2)
        if path not in seen:
            seen.add(path)
            found.append(path)
    return found


def reply_missing_index(text: str, min_links: int = MIN_LINKS) -> list[str]:
    """Paths cited in a reply that should have been an Output index."""
    paths = reply_paths(text)
    if len(paths) < min_links:
        return []
    if HEADING in (text or ""):
        return []
    return paths


def collect(root: Path, under: str, since_epoch: float) -> list[str]:
    base = root / under
    if not base.is_dir():
        return []
    rows: list[tuple[float, str]] = []
    for path in base.rglob("*"):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime < since_epoch:
            continue
        rows.append((mtime, str(path.relative_to(root))))
    rows.sort()
    return [rel for _, rel in rows]


def render(paths: list[str]) -> str:
    lines = [HEADING, "", "| Path |", "|---|"]
    if not paths:
        lines.append("| (none in this window) |")
    else:
        for path in paths:
            lines.append(f"| [{path}]({path}) |")
    lines.append("")
    lines.append("Paste this heading and table in the closing reply. A link to one report is not the index.")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print an Output index for files touched in a window.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--under", default="outputs")
    parser.add_argument("--hours", type=float, default=6.0)
    parser.add_argument("--check-reply", help="Path to a reply markdown file; exit 2 if the index heading is missing")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if args.check_reply:
        text = Path(args.check_reply).read_text(encoding="utf-8", errors="replace")
        missing = reply_missing_index(text)
        if not missing:
            print("output-index: reply ok")
            return 0
        print("OUTPUT INDEX MISSING from the reply. Include this heading and every path:", file=sys.stderr)
        print(render(missing), file=sys.stderr)
        return 2
    since = time.time() - args.hours * 3600
    paths = collect(root, args.under, since)
    print(render(paths))
    return 0


if __name__ == "__main__":
    sys.exit(main())
