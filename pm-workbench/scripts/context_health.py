#!/usr/bin/env python3
"""Report living-context files as missing, template-empty, stale, or ok.

The file list is ``reference/context/_manifest.md`` (the live copy when it
exists, otherwise the kit copy next to this script).

Usage:
  python3 scripts/context_health.py --root ~/pm-live
  python3 scripts/context_health.py --root ~/pm-live --brief
  python3 scripts/context_health.py --root ~/pm-live --ids current-priorities,people

Exit 0 when the root exists (gaps are printed, never a hard block).
Exit 2 when the root is missing.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

KIT_ROOT = Path(__file__).resolve().parents[1]

STATUS_TEMPLATE_RE = re.compile(r"(?m)^status:\s*template\s*$")
UPDATED_LINE_RE = re.compile(r"last[_\s-]*updated|updated\s*:", re.I)
DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
PLACEHOLDER_BULLET_RE = re.compile(
    r"\[[^\]]+\](\s*[—\-–:].*)?$"
)


def manifest_path(root: Path) -> Path:
    local = root / "reference" / "context" / "_manifest.md"
    if local.is_file():
        return local
    return KIT_ROOT / "reference" / "context" / "_manifest.md"


def load_manifest(root: Path) -> list[dict]:
    path = manifest_path(root)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 6:
            continue
        if cells[0] in {"id", "---"} or set(cells[0]) <= {"-", ":"}:
            continue
        if not cells[0] or cells[0].startswith("-"):
            continue
        try:
            freshness = int(cells[3])
        except ValueError:
            freshness = 0
        rows.append(
            {
                "id": cells[0],
                "path": cells[1],
                "need": cells[2],
                "freshness_days": freshness,
                "workflows": [w for w in cells[4].split(";") if w and w != "-"],
                "purpose": cells[5],
            }
        )
    return rows


def _bullet_body(line: str) -> str | None:
    stripped = line.strip()
    if stripped.startswith(("- ", "* ")):
        return stripped[2:].strip()
    numbered = re.match(r"^\d+\.\s+(.*)$", stripped)
    if numbered:
        return numbered.group(1).strip()
    return None


def is_template_empty(text: str) -> bool:
    """True when the file is still a blank template.

    ``status: template`` wins. Otherwise every bullet or numbered item is a
    bracket placeholder (``[ ]``, ``[TERM] — …``) and there is at least one
    such item. Intro prose does not count as filled context.
    """
    if STATUS_TEMPLATE_RE.search(text):
        return True
    bullets = []
    for line in text.splitlines():
        body = _bullet_body(line)
        if body is None:
            continue
        bullets.append(body)
    if not bullets:
        return False
    for body in bullets:
        if body in {"", "-", "[ ]"}:
            continue
        if PLACEHOLDER_BULLET_RE.fullmatch(body):
            continue
        return False
    return True


def last_updated(text: str, path: Path) -> tuple[date | None, str]:
    head = text.splitlines()[:25]
    for line in head:
        if UPDATED_LINE_RE.search(line):
            match = DATE_RE.search(line)
            if match:
                return date.fromisoformat(match.group(1)), "header"
    for line in head:
        match = DATE_RE.search(line)
        if match:
            return date.fromisoformat(match.group(1)), "header"
    if path.is_file():
        stamp = datetime.fromtimestamp(path.stat().st_mtime).date()
        return stamp, "mtime"
    return None, ""


def classify_file(path: Path, freshness_days: int, today: date | None = None) -> tuple[str, str]:
    """Return ``(status, detail)`` for one context file."""
    today = today or date.today()
    if not path.is_file():
        return "missing", "file not found"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        return "missing", str(error)
    if is_template_empty(text):
        return "template-empty", "still a template"
    if freshness_days <= 0:
        return "ok", "stable"
    updated, how = last_updated(text, path)
    if updated is None:
        return "stale", "no date"
    age = (today - updated).days
    if age > freshness_days:
        return "stale", f"last {how} {updated.isoformat()} ({age}d > {freshness_days}d)"
    return "ok", f"last {how} {updated.isoformat()}"


def assess(root: Path, today: date | None = None, ids: list[str] | None = None) -> list[dict]:
    today = today or date.today()
    wanted = {i.strip() for i in ids if i.strip()} if ids else None
    out = []
    for spec in load_manifest(root):
        if wanted is not None and spec["id"] not in wanted:
            continue
        path = root / spec["path"]
        status, detail = classify_file(path, spec["freshness_days"], today)
        out.append({**spec, "status": status, "detail": detail, "abs_path": str(path)})
    return out


def brief_line(rows: list[dict]) -> str:
    gaps = [r for r in rows if r["status"] != "ok"]
    if not gaps:
        return "context: ok"
    counts: dict[str, list[str]] = {}
    for row in gaps:
        counts.setdefault(row["status"], []).append(row["id"])
    parts = []
    for status in ("missing", "template-empty", "stale"):
        names = counts.get(status) or []
        if names:
            parts.append(f"{len(names)} {status}")
    listed = ", ".join(r["id"] for r in gaps)
    return f"context: {', '.join(parts)} ({listed}) — /brief context-setup"


def format_table(rows: list[dict]) -> str:
    if not rows:
        return "context: no manifest rows"
    lines = ["id\tstatus\tneed\tpath\tdetail"]
    for row in rows:
        lines.append(
            f"{row['id']}\t{row['status']}\t{row['need']}\t{row['path']}\t{row['detail']}"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--brief", action="store_true", help="one line for daily-brief")
    parser.add_argument("--ids", default="", help="comma-separated manifest ids")
    parser.add_argument("--today", default="", help="YYYY-MM-DD override for tests")
    args = parser.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    today = date.fromisoformat(args.today) if args.today else date.today()
    ids = [part.strip() for part in args.ids.split(",") if part.strip()] or None
    rows = assess(root, today=today, ids=ids)
    if args.brief:
        print(brief_line(rows))
    else:
        print(format_table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
