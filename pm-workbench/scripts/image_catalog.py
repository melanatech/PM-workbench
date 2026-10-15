#!/usr/bin/env python3
"""Visual catalog for PNGs and other images (state/image-catalog.csv).

One line per image: what it shows, and register / initiative links.
No embeddings — lookup is by path, kind, entities, or related_ids.

Usage:
  python3 scripts/image_catalog.py append --root ~/pm-live \\
    --path archive/documents/foo.png --kind screenshot \\
    --one-line "Reports Hub phase playground viewport" \\
    --related-ids INIT-001 --parent-path archive/documents/foo.md
  python3 scripts/image_catalog.py match --root ~/pm-live --entities INIT-001
  python3 scripts/image_catalog.py list --root ~/pm-live [--kind screenshot]
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

HEADER = [
    "image_path",
    "captured_date",
    "kind",
    "one_line",
    "related_ids",
    "entities",
    "parent_path",
    "vision_path",
    "sensitivity",
    "status",
]

KINDS = {
    "screenshot",
    "pdf-page",
    "walkthrough-step",
    "design",
    "diagram",
    "other",
}

STATUSES = {"open", "superseded", "ignored"}


def catalog_path(root: Path) -> Path:
    return root / "state" / "image-catalog.csv"


def _blank_row(raw: dict) -> dict:
    return {column: (raw.get(column) or "") for column in HEADER}


def _write_all(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        for raw in rows:
            writer.writerow(_blank_row(raw))


def ensure_catalog(root: Path) -> Path:
    path = catalog_path(root)
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
    path = ensure_catalog(root)
    with path.open(encoding="utf-8", newline="") as fh:
        return [_blank_row(row) for row in csv.DictReader(fh)]


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _tokens(value: str) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def guess_kind(path: str) -> str:
    name = Path(_normalize_path(path)).name.lower()
    if ".step-" in name or name.startswith("step-"):
        return "walkthrough-step"
    if name.startswith("page-") or "/.pages/" in _normalize_path(path).lower():
        return "pdf-page"
    if "storyboard" in name or "playground" in name or "capability" in name:
        return "design"
    if "diagram" in name or "process" in name:
        return "diagram"
    if name.endswith(".png") or name.endswith(".jpg") or name.endswith(".jpeg") or name.endswith(".webp"):
        return "screenshot"
    return "other"


def append_row(
    root: Path,
    *,
    image_path: str,
    kind: str = "",
    one_line: str = "",
    related_ids: str = "",
    entities: str = "",
    parent_path: str = "",
    vision_path: str = "",
    sensitivity: str = "none",
    status: str = "open",
    captured_date: str = "",
) -> bool:
    ensure_catalog(root)
    path = _normalize_path(image_path)
    kind = kind or guess_kind(path)
    if kind not in KINDS:
        raise ValueError(f"unknown kind: {kind}")
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    if not (one_line or "").strip():
        raise ValueError("one_line is required")

    rows = read_rows(root)
    today = captured_date or date.today().isoformat()
    new_row = {
        "image_path": path,
        "captured_date": today,
        "kind": kind,
        "one_line": one_line.strip(),
        "related_ids": related_ids,
        "entities": entities,
        "parent_path": _normalize_path(parent_path) if parent_path else "",
        "vision_path": _normalize_path(vision_path) if vision_path else "",
        "sensitivity": sensitivity or "none",
        "status": status,
    }
    for index, row in enumerate(rows):
        if row["image_path"] == path:
            new_row["captured_date"] = row["captured_date"] or today
            rows[index] = _blank_row(new_row)
            _write_all(catalog_path(root), rows)
            return True
    rows.append(_blank_row(new_row))
    _write_all(catalog_path(root), rows)
    return True


def match(
    root: Path,
    *,
    entities: str = "",
    related_ids: str = "",
    kind: str = "",
) -> list[dict]:
    want_e = _tokens(entities)
    want_r = _tokens(related_ids)
    results = []
    for row in read_rows(root):
        if kind and row["kind"] != kind:
            continue
        if want_e or want_r:
            hit_e = bool(want_e and (_tokens(row["entities"]) & want_e))
            hit_r = bool(want_r and (_tokens(row["related_ids"]) & want_r))
            if not (hit_e or hit_r):
                continue
        results.append(row)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    append_p = sub.add_parser("append", help="append or update an image-catalog row")
    append_p.add_argument("--root", required=True)
    append_p.add_argument("--path", required=True)
    append_p.add_argument("--kind", default="")
    append_p.add_argument("--one-line", required=True)
    append_p.add_argument("--related-ids", default="")
    append_p.add_argument("--entities", default="")
    append_p.add_argument("--parent-path", default="")
    append_p.add_argument("--vision-path", default="")
    append_p.add_argument("--sensitivity", default="none")
    append_p.add_argument("--status", default="open")
    append_p.add_argument("--captured-date", default="")

    match_p = sub.add_parser("match", help="find rows by entity or related id")
    match_p.add_argument("--root", required=True)
    match_p.add_argument("--entities", default="")
    match_p.add_argument("--related-ids", default="")
    match_p.add_argument("--kind", default="")

    list_p = sub.add_parser("list", help="list catalog rows")
    list_p.add_argument("--root", required=True)
    list_p.add_argument("--kind", default="")

    args = parser.parse_args(argv)

    if args.command == "append":
        root = Path(args.root).expanduser().resolve()
        append_row(
            root,
            image_path=args.path,
            kind=args.kind,
            one_line=args.one_line,
            related_ids=args.related_ids,
            entities=args.entities,
            parent_path=args.parent_path,
            vision_path=args.vision_path,
            sensitivity=args.sensitivity,
            status=args.status,
            captured_date=args.captured_date,
        )
        print(f"image-catalog: wrote {_normalize_path(args.path)}")
        return 0

    if args.command == "match":
        root = Path(args.root).expanduser().resolve()
        if not args.entities and not args.related_ids and not args.kind:
            print("ERROR: pass --entities and/or --related-ids (or use list)", file=sys.stderr)
            return 2
        rows = match(
            root,
            entities=args.entities,
            related_ids=args.related_ids,
            kind=args.kind,
        )
        for row in rows:
            print(
                f"{row['image_path']}\t{row['kind']}\t{row['related_ids']}\t"
                f"{row['one_line'][:80]}"
            )
        print(f"image-catalog: matches={len(rows)}")
        return 0

    if args.command == "list":
        root = Path(args.root).expanduser().resolve()
        rows = read_rows(root)
        if args.kind:
            rows = [row for row in rows if row["kind"] == args.kind]
        for row in rows:
            print(
                f"{row['image_path']}\t{row['kind']}\t{row['related_ids']}\t"
                f"{row['one_line'][:80]}"
            )
        print(f"image-catalog: rows={len(rows)}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
