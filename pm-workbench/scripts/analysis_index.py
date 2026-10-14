#!/usr/bin/env python3
"""Append-only analysis cache index (state/analysis-index.csv).

Usage:
  python3 scripts/analysis_index.py append --root ~/pm-live \\
    --topic-key "reports|instrumentation|events" --path outputs/daily/foo.md \\
    --kind instrumentation --as-of 2026-10-07 --one-line "…" \\
    [--primary-sources "repos/x@abc;…"] [--initiative-ids INIT-033] \\
    [--source-workflow code-dive]
  python3 scripts/analysis_index.py list --root ~/pm-live [--topic reports]
  python3 scripts/analysis_index.py mark-stale --root ~/pm-live \\
    --initiative-ids INIT-001 --primary-sources archive/meetings/x.md \\
    --since 2026-10-14 --reason "new decision touches INIT-001" \\
    [--except-path outputs/daily/today.md]
  python3 scripts/analysis_index.py stale --root ~/pm-live --living
  python3 scripts/analysis_index.py clear-stale --root ~/pm-live --path outputs/prds/x.md

``stale_since`` is the date (YYYY-MM-DD) a newer fact shared an initiative id
or a primary-source token with this row. Empty means not flagged. The earliest
date is kept if the row is flagged again. ``append --refresh`` on the same
path updates the row and clears both stale columns. This does not rewrite the
deliverable.
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
    "stale_since",
    "stale_reason",
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


def _blank_row(raw: dict) -> dict:
    return {column: (raw.get(column) or "") for column in HEADER}


def _write_all(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        for raw in rows:
            writer.writerow(_blank_row(raw))


def ensure_index(root: Path) -> Path:
    path = index_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or path.stat().st_size == 0:
        _write_all(path, [])
        return path
    with path.open(encoding="utf-8", newline="") as fh:
        reader = csv.reader(fh)
        try:
            header = next(reader)
        except StopIteration:
            header = []
    if header == HEADER:
        return path
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    _write_all(path, rows)
    return path


def read_rows(root: Path) -> list[dict]:
    path = ensure_index(root)
    with path.open(encoding="utf-8", newline="") as fh:
        return [_blank_row(row) for row in csv.DictReader(fh)]


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
    refresh: bool = False,
) -> bool:
    """Append a row if path is new. With ``refresh``, update that path and clear staleness.

    Returns True if a row was written or refreshed.
    """
    kind = kind if kind in KINDS else "other"
    rel = path.replace("\\", "/").lstrip("./")
    rows = read_rows(root)
    fresh = {
        "topic_key": topic_key,
        "initiative_ids": initiative_ids,
        "kind": kind,
        "path": rel,
        "as_of_date": as_of_date or date.today().isoformat(),
        "one_line": re.sub(r"[\r\n]+", " ", one_line).strip(),
        "primary_sources": primary_sources,
        "source_workflow": source_workflow,
        "indexed_date": indexed_date or date.today().isoformat(),
        "stale_since": "",
        "stale_reason": "",
    }
    for index, row in enumerate(rows):
        if row.get("path") != rel:
            continue
        if not refresh:
            return False
        rows[index] = fresh
        _write_all(index_path(root), rows)
        return True
    rows.append(fresh)
    _write_all(index_path(root), rows)
    return True


def _field_tokens(field: str) -> set[str]:
    return {part.strip() for part in re.split(r"[;\n,]+", field or "") if part.strip()}


def mark_stale(
    root: Path,
    *,
    initiative_ids: str = "",
    primary_sources: str = "",
    reason: str = "",
    since: str = "",
    except_path: str = "",
) -> list[str]:
    """Flag indexed rows that share an initiative id or a primary-source token.

    Keeps the earliest ``stale_since``. Does not edit the deliverable.
    Returns the paths that are flagged (including ones already stale).
    """
    init_tokens = _field_tokens(initiative_ids)
    source_tokens = _field_tokens(primary_sources)
    if not init_tokens and not source_tokens:
        raise ValueError("mark_stale needs initiative ids or primary sources")
    since_value = (since or date.today().isoformat())[:10]
    reason_value = re.sub(r"[\r\n]+", " ", reason).strip()
    skip = except_path.replace("\\", "/").lstrip("./")
    rows = read_rows(root)
    flagged: list[str] = []
    changed = False
    for row in rows:
        rel = row.get("path") or ""
        if skip and rel == skip:
            continue
        row_inits = _field_tokens(row.get("initiative_ids") or "")
        row_sources = _field_tokens(row.get("primary_sources") or "")
        shares_init = bool(init_tokens and row_inits & init_tokens)
        shares_source = bool(source_tokens and row_sources & source_tokens)
        if not shares_init and not shares_source:
            continue
        flagged.append(rel)
        prior = (row.get("stale_since") or "")[:10]
        if prior and prior <= since_value:
            if not (row.get("stale_reason") or "").strip() and reason_value:
                row["stale_reason"] = reason_value
                changed = True
            continue
        row["stale_since"] = since_value
        if reason_value:
            row["stale_reason"] = reason_value
        changed = True
    if changed:
        _write_all(index_path(root), rows)
    return flagged


LIVING_PREFIXES = ("outputs/prds/", "outputs/strategy/", "roadmap/")
LIVING_KINDS = {"brief", "strategy"}


def is_living_deliverable(row: dict) -> bool:
    """PRD, brief, strategy, or roadmap — the daily-brief stale list."""
    path = (row.get("path") or "").replace("\\", "/")
    kind = row.get("kind") or ""
    if path.startswith(LIVING_PREFIXES):
        return True
    if kind in LIVING_KINDS:
        return True
    name = path.rsplit("/", 1)[-1]
    if "brief" in name or name.startswith("roadmap"):
        return True
    return False


def stale_rows(root: Path, *, living_only: bool = False) -> list[dict]:
    rows = [row for row in read_rows(root) if (row.get("stale_since") or "").strip()]
    if living_only:
        rows = [row for row in rows if is_living_deliverable(row)]
    return rows


def clear_stale(root: Path, path: str) -> bool:
    rel = path.replace("\\", "/").lstrip("./")
    rows = read_rows(root)
    found = False
    for row in rows:
        if row.get("path") != rel:
            continue
        found = True
        row["stale_since"] = ""
        row["stale_reason"] = ""
    if found:
        _write_all(index_path(root), rows)
    return found


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
    ap.add_argument("--refresh", action="store_true", help="update an existing path and clear staleness")

    lp = sub.add_parser("list")
    lp.add_argument("--topic", default="")

    mp = sub.add_parser("mark-stale")
    mp.add_argument("--initiative-ids", default="")
    mp.add_argument("--primary-sources", default="")
    mp.add_argument("--since", default="")
    mp.add_argument("--reason", default="")
    mp.add_argument("--except-path", default="")

    sp = sub.add_parser("stale")
    sp.add_argument("--living", action="store_true", help="PRD, brief, strategy, roadmap only")

    cp = sub.add_parser("clear-stale")
    cp.add_argument("--path", required=True)

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
            refresh=args.refresh,
        )
        if not wrote:
            print(f"skip: path already indexed ({args.path})")
        elif args.refresh and any(r.get("path") == args.path.replace("\\", "/").lstrip("./") for r in read_rows(root)):
            print("refreshed")
        else:
            print("appended")
        return 0

    if args.cmd == "mark-stale":
        try:
            flagged = mark_stale(
                root,
                initiative_ids=args.initiative_ids,
                primary_sources=args.primary_sources,
                reason=args.reason,
                since=args.since,
                except_path=args.except_path,
            )
        except ValueError as error:
            print(f"ERROR: {error}", file=sys.stderr)
            return 2
        if not flagged:
            print("stale: none")
        else:
            for rel in flagged:
                print(f"stale: {rel}")
        return 0

    if args.cmd == "stale":
        rows = stale_rows(root, living_only=args.living)
        if not rows:
            print("stale: none")
            return 0
        for row in rows:
            print(
                f"stale: {row.get('path', '')} since {row.get('stale_since', '')} "
                f"— {row.get('stale_reason', '')}"
            )
        return 0

    if args.cmd == "clear-stale":
        found = clear_stale(root, args.path)
        print("cleared" if found else f"missing: {args.path}")
        return 0 if found else 2

    for r in list_rows(root, args.topic):
        print(
            f"{r.get('as_of_date', '')}\t{r.get('kind', '')}\t{r.get('path', '')}\t"
            f"{r.get('one_line', '')}\tprimary={r.get('primary_sources', '')}\t"
            f"stale_since={r.get('stale_since', '')}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
