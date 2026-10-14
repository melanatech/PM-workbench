#!/usr/bin/env python3
"""Group rework_correction rows from usage-history into themes.

Themes seen twice or more → BACKLOG-style lines: needs enforcement, not prose.

Usage:
  python3 scripts/recurring_corrections.py --root ~/pm-live
  python3 scripts/recurring_corrections.py --root ~/pm-live --min-count 2
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

# keyword → theme id (order matters: first match wins)
THEME_RULES: list[tuple[str, list[str]]] = [
    (
        "assume_vs_search",
        [
            r"\bassum",
            r"\bguess",
            r"\bnamed surface\b",
            r"\bworkspace[- ]alias",
            r"\blooked? up\b",
            r"\bsearch(ed)? the context\b",
            r"\bwrong (file|path|folder)\b",
            r"\bglossary instead\b",
            r"\bname resolution\b",
        ],
    ),
    (
        "nonexistent_id",
        [
            r"\bCOM-\d+",
            r"\bDEC-\d+",
            r"\bRISK-\d+",
            r"\bEV-\d+",
            r"\bphantom\b",
            r"\bdoesn'?t exist\b",
            r"\bnon[- ]existent\b",
            r"\bmissing (COM|DEC|RISK|EV)\b",
            r"\bcit(e|ing|ed) .*\bthat (don'?t|do not) exist",
        ],
    ),
    (
        "links_paths",
        [
            r"\bclickable\b",
            r"\bmarkdown link",
            r"\bbare path",
            r"\blink(ed)? path",
            r"\brule 20\b",
            r"\bfile://",
            r"\bworkspace[- ]relative\b",
        ],
    ),
    (
        "workspace_sources",
        [
            r"\bincomplete\b.*\btranscript",
            r"\btranscript\b.*\bincomplete",
            r"\brecapture\b",
            r"\bclipper\b",
            r"\bBASELINE-SOURCES\b",
            r"\bauthority[- ]first\b",
            r"\brepos/\b",
            r"\bdrafts? as evidence\b",
        ],
    ),
]

THEME_LABELS = {
    "assume_vs_search": "Assumed a surface instead of looking it up (aliases / preflight)",
    "nonexistent_id": "Cited register IDs that do not exist",
    "links_paths": "Mentioned workspace paths without clickable Markdown links",
    "workspace_sources": "Wrong or incomplete workspace source (transcript/clipper/authority)",
}


def _match_theme(excerpt: str) -> str:
    text = (excerpt or "").lower()
    for theme, patterns in THEME_RULES:
        for pat in patterns:
            if re.search(pat, text, re.I):
                return theme
    return "other_correction"


def load_corrections(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("category") or "").strip() == "rework_correction":
                rows.append(row)
    return rows


def summarize(rows: list[dict], min_count: int = 2) -> list[dict]:
    by: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        theme = _match_theme(row.get("user_excerpt") or "")
        by[theme].append(row)
    out = []
    for theme, items in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        if len(items) < min_count:
            continue
        if theme == "other_correction":
            continue
        dates = sorted({(r.get("timestamp") or "")[:10] for r in items if r.get("timestamp")})
        out.append(
            {
                "theme": theme,
                "label": THEME_LABELS.get(theme, theme),
                "count": len(items),
                "first_seen": dates[0] if dates else "",
                "last_seen": dates[-1] if dates else "",
                "needs": "enforcement (hook or test), not another prose rule",
            }
        )
    return out


def format_report(items: list[dict]) -> str:
    if not items:
        return "No recurring correction themes (min count not met)."
    lines = ["## Recurring corrections (needs enforcement, not prose)", ""]
    for it in items:
        lines.append(
            f"- **{it['theme']}** ({it['count']}×, {it['first_seen']}→{it['last_seen']}): "
            f"{it['label']} — {it['needs']}"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", required=True, help="Live workspace root (e.g. ~/pm-live)")
    ap.add_argument("--min-count", type=int, default=2)
    ap.add_argument("--csv", action="store_true", help="Machine-readable CSV to stdout")
    args = ap.parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    hist = root / "state" / "usage-history.csv"
    rows = load_corrections(hist)
    items = summarize(rows, min_count=args.min_count)
    if args.csv:
        w = csv.DictWriter(
            sys.stdout,
            fieldnames=["theme", "label", "count", "first_seen", "last_seen", "needs"],
        )
        w.writeheader()
        for it in items:
            w.writerow(it)
    else:
        sys.stdout.write(format_report(items))
        if not rows:
            sys.stderr.write(f"(no rework_correction rows in {hist})\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
