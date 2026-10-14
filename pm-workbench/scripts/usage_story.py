#!/usr/bin/env python3
"""Numbers and a structure check for the monthly usage story.

    python3 scripts/usage_story.py data  --root ~/pm-live [--since 2026-10-03]
    python3 scripts/usage_story.py check --root ~/pm-live outputs/usage/<date>-story.md

``data`` prints markdown tables from live files: weekly work mix (rows and
token share), named workflows per week, corrections (excluding subagent results
returning to the main session), correction turns for theming, and outcome counts per
week. It never prints cost; spend comes from the internal cost dashboard.

``check`` exits 1 when a story is missing a required section, opens with
something other than the executive summary, or divides spend by an artifact
count.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import re
import sys
from pathlib import Path

TOKEN_COLS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)
INJECTED_PREFIXES = ("<task-notification",)

GROUPS = {
    "rework_correction": "Correction or redo",
    "other": "Not classified",
    "lookup": "Lookup",
    "capture": "Capture",
    "prototype": "Prototype",
    "explore_brief": "Explore brief",
    "code_dive": "Code dive",
}

REQUIRED_SECTIONS = (
    ("executive summary", r"^##\s+executive summary"),
    ("so what", r"^##\s+so what"),
    ("work mix change", r"^##\s+what changed"),
    ("corrections", r"^##\s+.*correction"),
    ("outcomes", r"^##\s+what it produced"),
    ("cost", r"^##\s+cost"),
    ("limits", r"^##\s+what we cannot claim"),
    ("next run", r"^##\s+next run"),
)

PER_ARTIFACT = re.compile(
    r"\$\s?\d[\d,.]*\s*(?:per|/)\s*(?:output\s+)?"
    r"(?:file|output|decision|commitment|row|artifact|evidence|initiative|to-?do|issue|commit)s?\b",
    re.I,
)


def week_of(day: str) -> str:
    d = dt.date.fromisoformat(day[:10])
    return (d - dt.timedelta(days=d.weekday())).isoformat()


def tokens(row: dict) -> int:
    total = 0
    for col in TOKEN_COLS:
        try:
            total += int(row.get(col) or 0)
        except ValueError:
            pass
    return total


def is_injected(excerpt: str) -> bool:
    return excerpt.lstrip().startswith(INJECTED_PREFIXES)


def group_of(row: dict) -> str:
    category = row.get("category") or ""
    if is_injected(row.get("user_excerpt") or ""):
        return "Subagent result returned"
    if category.startswith("workflow:"):
        return "Named workbench workflow"
    return GROUPS.get(category, category or "Not classified")


def read_csv(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def pct(n: int, d: int) -> str:
    return f"{round(100 * n / d)}%" if d else "—"


def usage_tables(rows: list[dict]) -> list[str]:
    out: list[str] = []
    if not rows:
        return ["No rows in state/usage-history.csv. Run session_usage.py --backfill first."]

    days = sorted({r["timestamp"][:10] for r in rows if r.get("timestamp")})
    weeks = sorted({week_of(d) for d in days})
    out.append(
        f"Usage rows: {len(rows):,} calls, {len({r['session_id'] for r in rows})} sessions, "
        f"{days[0]} to {days[-1]} ({len(days)} days with activity)."
    )
    for w in weeks:
        in_week = [d for d in days if week_of(d) == w]
        out.append(f"- Week of {w}: {in_week[0]} to {in_week[-1]}, {len(in_week)} active days")

    by_week = collections.defaultdict(list)
    for r in rows:
        by_week[week_of(r["timestamp"])].append(r)

    groups = sorted({group_of(r) for r in rows})
    out += ["", "### Work mix by week (share of calls / share of tokens)", ""]
    out.append("| Kind of work | " + " | ".join(f"Week of {w}" for w in weeks) + " |")
    out.append("|---|" + "---|" * len(weeks))
    for g in groups:
        cells = []
        for w in weeks:
            wr = by_week[w]
            n = sum(1 for r in wr if group_of(r) == g)
            t = sum(tokens(r) for r in wr if group_of(r) == g)
            cells.append(f"{pct(n, len(wr))} / {pct(t, sum(tokens(r) for r in wr))}")
        out.append(f"| {g} | " + " | ".join(cells) + " |")

    out += ["", "### Named workflows by week (calls)", ""]
    for w in weeks:
        c = collections.Counter(
            r["category"].split(":", 1)[1] for r in by_week[w] if r["category"].startswith("workflow:")
        )
        out.append(f"- Week of {w}: " + (", ".join(f"{k} {v}" for k, v in c.most_common()) or "none"))

    rework = [r for r in rows if r["category"] == "rework_correction"]
    real = [r for r in rework if not is_injected(r.get("user_excerpt", ""))]
    turns: dict[str, dict] = {}
    for r in real:
        turns.setdefault(r.get("user_uuid") or r["message_uuid"], r)
    out += ["", "### Corrections", ""]
    out.append(
        f"Labeled correction calls: {len(rework):,}. From subagent results "
        f"(excluded): {len(rework) - len(real):,}. Real correction calls: {len(real):,} "
        f"({pct(len(real), len(rows))} of all calls) from {len(turns)} distinct turns."
    )
    for w in weeks:
        wr = by_week[w]
        n = sum(1 for r in wr if r["category"] == "rework_correction" and not is_injected(r.get("user_excerpt", "")))
        out.append(f"- Week of {w}: {n:,} of {len(wr):,} calls ({pct(n, len(wr))})")
    per_day = collections.Counter(r["timestamp"][:10] for r in real)
    out.append("- By day: " + ", ".join(f"{d} {n}" for d, n in sorted(per_day.items())))

    out += ["", "### Correction turns to theme (internal only — do not quote in external output)", ""]
    for t in sorted(turns.values(), key=lambda r: r["timestamp"]):
        excerpt = " ".join(t.get("user_excerpt", "").split())[:140]
        out.append(f"- {t['timestamp'][:10]}: {excerpt}")

    surfaces = collections.Counter(r.get("surface") or "unknown" for r in rows)
    out += ["", "### Surface", "", ", ".join(f"{k} {v:,}" for k, v in surfaces.most_common())]
    return out


def outcome_tables(root: Path, since: str) -> list[str]:
    specs = (
        ("Decisions", "registers/decisions.csv", "date"),
        ("Commitments (by last update)", "registers/commitments.csv", "last_updated"),
        ("Evidence", "registers/evidence.csv", "capture_date"),
        ("Initiatives (by last update)", "registers/initiatives.csv", "last_updated"),
        ("To-dos created", "registers/todos.csv", "created"),
    )
    out = ["", f"### Outcomes per week (on or after {since})", ""]
    for label, rel, col in specs:
        rows = read_csv(root / rel)
        if not rows:
            out.append(f"- {label}: [{rel}]({rel}) missing or empty")
            continue
        dated = [r for r in rows if (r.get(col) or "")[:10] >= since]
        c = collections.Counter(week_of(r[col]) for r in dated if re.match(r"\d{4}-\d{2}-\d{2}", r.get(col) or ""))
        weekly = ", ".join(f"week of {w}: {n}" for w, n in sorted(c.items())) or "none"
        out.append(f"- {label}: {len(dated)} of {len(rows)} on file ({weekly})")
        if rel.endswith("decisions.csv"):
            out.append("  - `made_by` is free text: read it to say who decided, do not count it by exact match")
        if rel.endswith("todos.csv"):
            done = sum(1 for r in rows if (r.get("status") or "").strip().lower() == "done")
            out.append(f"  - Done: {done} of {len(rows)}")
    return out


def cmd_data(args: argparse.Namespace) -> int:
    root = Path(args.root).expanduser()
    rows = read_csv(root / "state" / "usage-history.csv")
    lines = usage_tables(rows) + outcome_tables(root, args.since)
    lines += [
        "",
        "Cost is not computed here. Use the internal cost dashboard (spend, tokens, and its date range).",
    ]
    print("\n".join(lines))
    return 0


def check_story(text: str) -> list[str]:
    problems: list[str] = []
    lines = text.splitlines()
    headings = [ln.strip().lower() for ln in lines if ln.startswith("## ")]
    for name, pattern in REQUIRED_SECTIONS:
        if not any(re.match(pattern, h) for h in headings):
            problems.append(f"missing section: {name}")
    if headings and not headings[0].startswith("## executive summary"):
        problems.append("first section must be the executive summary")
    for i, ln in enumerate(lines, 1):
        if PER_ARTIFACT.search(ln):
            problems.append(f"line {i}: spend divided by an artifact count")
    return problems


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.story)
    if not path.is_absolute():
        path = Path(args.root).expanduser() / path
    problems = check_story(path.read_text(encoding="utf-8"))
    for p in problems:
        print(p)
    if not problems:
        print("ok")
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data")
    d.add_argument("--root", required=True)
    d.add_argument("--since", default="2026-10-03", help="live start date for outcome counts")
    d.set_defaults(fn=cmd_data)
    c = sub.add_parser("check")
    c.add_argument("--root", required=True)
    c.add_argument("story")
    c.set_defaults(fn=cmd_check)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
