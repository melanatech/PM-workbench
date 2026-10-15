#!/usr/bin/env python3
"""Append-only source triage index (state/source-index.csv).

Usage:
  python3 scripts/source_index.py append --root ~/pm-live \\
    --path archive/documents/foo.html --source-role strategy \\
    --temporal-status current --origin primary --outcome hold \\
    --reason "ideas, no owner" --entities "INIT-004,MAPU" \\
    --summary "…" [--same-as …] [--sensitivity none] [--unread …]
  python3 scripts/source_index.py match --root ~/pm-live --entities INIT-004,MAPU
  python3 scripts/source_index.py promote --root ~/pm-live \\
    --path archive/… --linked-ids EV-001,DEC-002
  python3 scripts/source_index.py find-duplicate --root ~/pm-live --path <file>
  python3 scripts/source_index.py is-own-output --path <file>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

HEADER = [
    "source_path",
    "captured_date",
    "source_date",
    "source_role",
    "temporal_status",
    "origin",
    "outcome",
    "reason",
    "entities",
    "summary",
    "linked_ids",
    "same_as",
    "content_hash",
    "sensitivity",
    "unread",
    "status",
]

ROLES = {
    "evidence",
    "operating-update",
    "product-knowledge",
    "semantic-system",
    "strategy",
    "exploratory-thinking",
    "operating-model",
    "business-process",
    "design-artifact",
    "stakeholder-stance",
    "roadmap-plan",
    "engineering",
    "template",
    "how-to",
    "data",
    "kit-feedback",
    "other",
}

TEMPORAL = {
    "current",
    "historical-baseline",
    "superseded",
    "conflicting",
    "unknown",
}

ORIGINS = {"primary", "second-hand", "ai-summary", "derived-own"}

OUTCOMES = {"promote", "index", "hold", "ignore", "duplicate"}

STATUSES = {"open", "promoted", "superseded", "ignored"}

OWN_PREFIXES = ("outputs/", "drafts/", "prototypes/")

_TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".html",
    ".htm",
    ".csv",
    ".tsv",
    ".json",
    ".extracted.txt",
}


def index_path(root: Path) -> Path:
    return root / "state" / "source-index.csv"


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


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _entity_tokens(value: str) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def content_hash(path: Path) -> str:
    """SHA-256 of normalized text when readable; otherwise of raw bytes."""
    data = path.read_bytes()
    name = path.name.lower()
    if any(name.endswith(suffix) for suffix in _TEXT_SUFFIXES):
        text = data.decode("utf-8", errors="replace")
        normalized = re.sub(r"\s+", " ", text).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return hashlib.sha256(data).hexdigest()


def stem_key(path: str) -> str:
    """Group key for multi-file bundles (strip trailing export suffixes)."""
    name = Path(_normalize_path(path)).stem.lower()
    name = re.sub(r"\.(extracted|vision)$", "", name)
    name = re.sub(r"[-_](new\d*|updated|summary|accounting|m2m|ro)$", "", name)
    name = re.sub(r"[^a-z0-9]+", "", name)
    return name[:48]


def is_own_output(path: str) -> bool:
    norm = _normalize_path(path)
    return any(norm.startswith(prefix) or f"/{prefix}" in f"/{norm}" for prefix in OWN_PREFIXES)


def append_row(
    root: Path,
    *,
    source_path: str,
    source_role: str = "other",
    temporal_status: str = "unknown",
    origin: str = "primary",
    outcome: str = "index",
    reason: str = "",
    entities: str = "",
    summary: str = "",
    linked_ids: str = "",
    same_as: str = "",
    content_hash_value: str = "",
    sensitivity: str = "none",
    unread: str = "",
    status: str = "open",
    captured_date: str = "",
    source_date: str = "",
) -> bool:
    """Append or update by source_path. Returns True when a row was written."""
    ensure_index(root)
    path = _normalize_path(source_path)
    if source_role not in ROLES:
        raise ValueError(f"unknown source_role: {source_role}")
    if temporal_status not in TEMPORAL:
        raise ValueError(f"unknown temporal_status: {temporal_status}")
    if origin not in ORIGINS:
        raise ValueError(f"unknown origin: {origin}")
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown outcome: {outcome}")
    if status not in STATUSES:
        raise ValueError(f"unknown status: {status}")
    if is_own_output(path) and origin == "primary":
        origin = "derived-own"

    rows = read_rows(root)
    today = captured_date or date.today().isoformat()
    new_row = {
        "source_path": path,
        "captured_date": today,
        "source_date": source_date,
        "source_role": source_role,
        "temporal_status": temporal_status,
        "origin": origin,
        "outcome": outcome,
        "reason": reason,
        "entities": entities,
        "summary": summary,
        "linked_ids": linked_ids,
        "same_as": same_as,
        "content_hash": content_hash_value,
        "sensitivity": sensitivity or "none",
        "unread": unread,
        "status": status,
    }
    for index, row in enumerate(rows):
        if row["source_path"] == path:
            # Idempotent update: keep earliest captured_date; refresh the rest.
            new_row["captured_date"] = row["captured_date"] or today
            rows[index] = _blank_row(new_row)
            _write_all(index_path(root), rows)
            return True
    rows.append(_blank_row(new_row))
    _write_all(index_path(root), rows)
    return True


def match_entities(root: Path, entities: str, *, status: str = "") -> list[dict]:
    wanted = _entity_tokens(entities)
    if not wanted:
        return []
    results = []
    for row in read_rows(root):
        if status and row["status"] != status:
            continue
        have = _entity_tokens(row["entities"])
        if have & wanted:
            results.append(row)
    return results


def promote(root: Path, source_path: str, linked_ids: str = "") -> bool:
    path = _normalize_path(source_path)
    rows = read_rows(root)
    found = False
    for index, row in enumerate(rows):
        if row["source_path"] != path:
            continue
        row["status"] = "promoted"
        row["outcome"] = "promote"
        if linked_ids:
            existing = _entity_tokens(row["linked_ids"])
            existing |= _entity_tokens(linked_ids)
            row["linked_ids"] = ",".join(sorted(existing))
        rows[index] = _blank_row(row)
        found = True
        break
    if not found:
        return False
    _write_all(index_path(root), rows)
    return True


def find_duplicate(root: Path, path: Path) -> dict:
    """Return a match dict or empty when no duplicate is found.

    Keys when found: same_as, match_kind (hash|stem|title), content_hash.
    """
    ensure_index(root)
    if not path.is_file():
        return {"error": f"not a file: {path}"}
    digest = content_hash(path)
    stem = stem_key(str(path))
    title = path.stem.lower()
    for row in read_rows(root):
        if row["content_hash"] and row["content_hash"] == digest:
            return {
                "same_as": row["source_path"],
                "match_kind": "hash",
                "content_hash": digest,
            }
    for row in read_rows(root):
        other_stem = stem_key(row["source_path"])
        if stem and other_stem and stem == other_stem:
            return {
                "same_as": row["source_path"],
                "match_kind": "stem",
                "content_hash": digest,
            }
    for row in read_rows(root):
        other_title = Path(row["source_path"]).stem.lower()
        if title and other_title and title == other_title:
            return {
                "same_as": row["source_path"],
                "match_kind": "title",
                "content_hash": digest,
            }
    return {"content_hash": digest}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    append_p = sub.add_parser("append", help="append or update a source-index row")
    append_p.add_argument("--root", required=True)
    append_p.add_argument("--path", required=True)
    append_p.add_argument("--source-role", default="other")
    append_p.add_argument("--temporal-status", default="unknown")
    append_p.add_argument("--origin", default="primary")
    append_p.add_argument("--outcome", default="index")
    append_p.add_argument("--reason", default="")
    append_p.add_argument("--entities", default="")
    append_p.add_argument("--summary", default="")
    append_p.add_argument("--linked-ids", default="")
    append_p.add_argument("--same-as", default="")
    append_p.add_argument("--content-hash", default="")
    append_p.add_argument("--sensitivity", default="none")
    append_p.add_argument("--unread", default="")
    append_p.add_argument("--status", default="open")
    append_p.add_argument("--captured-date", default="")
    append_p.add_argument("--source-date", default="")

    match_p = sub.add_parser("match", help="find rows sharing entity tokens")
    match_p.add_argument("--root", required=True)
    match_p.add_argument("--entities", required=True)
    match_p.add_argument("--status", default="")

    promote_p = sub.add_parser("promote", help="mark a held/indexed row promoted")
    promote_p.add_argument("--root", required=True)
    promote_p.add_argument("--path", required=True)
    promote_p.add_argument("--linked-ids", default="")

    dup_p = sub.add_parser("find-duplicate", help="hash/stem/title duplicate check")
    dup_p.add_argument("--root", required=True)
    dup_p.add_argument("--path", required=True)

    own_p = sub.add_parser("is-own-output", help="true if path is under outputs/drafts/prototypes")
    own_p.add_argument("--path", required=True)

    args = parser.parse_args(argv)

    if args.command == "append":
        root = Path(args.root).expanduser().resolve()
        digest = args.content_hash
        candidate = Path(args.path)
        if not digest and candidate.is_file():
            digest = content_hash(candidate)
        append_row(
            root,
            source_path=args.path,
            source_role=args.source_role,
            temporal_status=args.temporal_status,
            origin=args.origin,
            outcome=args.outcome,
            reason=args.reason,
            entities=args.entities,
            summary=args.summary,
            linked_ids=args.linked_ids,
            same_as=args.same_as,
            content_hash_value=digest,
            sensitivity=args.sensitivity,
            unread=args.unread,
            status=args.status,
            captured_date=args.captured_date,
            source_date=args.source_date,
        )
        print(f"source-index: wrote {_normalize_path(args.path)}")
        return 0

    if args.command == "match":
        root = Path(args.root).expanduser().resolve()
        rows = match_entities(root, args.entities, status=args.status)
        for row in rows:
            print(
                f"{row['source_path']}\t{row['outcome']}\t{row['status']}\t"
                f"{row['entities']}\t{row['summary'][:80]}"
            )
        print(f"source-index: matches={len(rows)}")
        return 0

    if args.command == "promote":
        root = Path(args.root).expanduser().resolve()
        ok = promote(root, args.path, linked_ids=args.linked_ids)
        if not ok:
            print(f"ERROR: no row for {_normalize_path(args.path)}", file=sys.stderr)
            return 2
        print(f"source-index: promoted {_normalize_path(args.path)}")
        return 0

    if args.command == "find-duplicate":
        root = Path(args.root).expanduser().resolve()
        result = find_duplicate(root, Path(args.path).expanduser())
        if "error" in result:
            print(result["error"], file=sys.stderr)
            return 2
        if "same_as" in result:
            print(
                f"duplicate\t{result['match_kind']}\t{result['same_as']}\t"
                f"{result['content_hash']}"
            )
            return 0
        print(f"unique\t{result['content_hash']}")
        return 0

    if args.command == "is-own-output":
        print("yes" if is_own_output(args.path) else "no")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
