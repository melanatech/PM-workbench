#!/usr/bin/env python3
"""Append-only analysis cache index (state/analysis-index.csv).

Usage:
  python3 scripts/analysis_index.py append --root ~/pm-live \\
    --topic-key "reports|instrumentation|events" --path outputs/daily/foo.md \\
    --kind instrumentation --as-of 2026-10-07 --one-line "…" \\
    [--primary-sources "repos/x@abc;…"] [--initiative-ids INIT-033] \\
    [--source-workflow code-dive]
  python3 scripts/analysis_index.py list --root ~/pm-live [--topic reports]
"""
from __future__ import annotations

import argparse
import csv
import os
import re
import sys
from datetime import date
from pathlib import Path

HEADER = [
    "topic_key",
    "initiative_ids",
    "kind",
    "path",
    "as_of_date",
    "one_line",
    "primary_sources",
    "source_workflow",
    "indexed_date",
]

KINDS = {
    "instrumentation",
    "events",
    "code-dive",
    "product-flow",
    "discovery",
    "competitive",
    "web-search",
    "strategy",
    "reconcile",
    "research",
    "brief",
    "other",
}


def index_path(root: Path) -> Path:
    return root / "state" / "analysis-index.csv"


def ensure_index(root: Path) -> Path:
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        with path.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerow(HEADER)
    return path


def read_rows(root: Path) -> list[dict]:
    path = ensure_index(root)
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def append_row(
    root: Path,
    *,
    topic_key: str,
    path: str,
    kind: str = "other",
    as_of_date: str = "",
    one_line: str = "",
    primary_sources: str = "",
    initiative_ids: str = "",
    source_workflow: str = "",
    indexed_date: str = "",
) -> bool:
    """Append a row if path is new. Returns True if written."""
    kind = kind if kind in KINDS else "other"
    rel = path.replace("\\", "/").lstrip("./")
    rows = read_rows(root)
    if any(r.get("path") == rel for r in rows):
        return False
    idx = ensure_index(root)
    with idx.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\n")
        w.writerow(
            {
                "topic_key": topic_key,
                "initiative_ids": initiative_ids,
                "kind": kind,
                "path": rel,
                "as_of_date": as_of_date or date.today().isoformat(),
                "one_line": re.sub(r"[\r\n]+", " ", one_line).strip(),
                "primary_sources": primary_sources,
                "source_workflow": source_workflow,
                "indexed_date": indexed_date or date.today().isoformat(),
            }
        )
    return True


def list_rows(root: Path, topic: str = "") -> list[dict]:
    rows = read_rows(root)
    if not topic:
        return rows
    tokens = {t.lower() for t in re.split(r"[\s|,]+", topic) if t}
    out = []
    for r in rows:
        blob = " ".join(
            [
                r.get("topic_key", ""),
                r.get("initiative_ids", ""),
                r.get("kind", ""),
                r.get("path", ""),
                r.get("one_line", ""),
            ]
        ).lower()
        if any(t in blob for t in tokens):
            out.append(r)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, help="live workspace root")
    sub = p.add_subparsers(dest="cmd", required=True)

    ap = sub.add_parser("append")
    ap.add_argument("--topic-key", required=True)
    ap.add_argument("--path", required=True)
    ap.add_argument("--kind", default="other")
    ap.add_argument("--as-of", dest="as_of", default="")
    ap.add_argument("--one-line", default="")
    ap.add_argument("--primary-sources", default="")
    ap.add_argument("--initiative-ids", default="")
    ap.add_argument("--source-workflow", default="")

    lp = sub.add_parser("list")
    lp.add_argument("--topic", default="")

    args = p.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2

    if args.cmd == "append":
        wrote = append_row(
            root,
            topic_key=args.topic_key,
            path=args.path,
            kind=args.kind,
            as_of_date=args.as_of,
            one_line=args.one_line,
            primary_sources=args.primary_sources,
            initiative_ids=args.initiative_ids,
            source_workflow=args.source_workflow,
        )
        print("appended" if wrote else f"skip: path already indexed ({args.path})")
        return 0

    for r in list_rows(root, args.topic):
        print(
            f"{r.get('as_of_date', '')}\t{r.get('kind', '')}\t{r.get('path', '')}\t"
            f"{r.get('one_line', '')}\tprimary={r.get('primary_sources', '')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
