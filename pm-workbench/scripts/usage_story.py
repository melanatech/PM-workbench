#!/usr/bin/env python3
"""Numbers and a structure check for the monthly usage story.

    python3 scripts/usage_story.py data  --root ~/pm-live [--since 2026-10-03]
    python3 scripts/usage_story.py check --root ~/pm-live outputs/usage/<date>-story.md
    python3 scripts/usage_story.py check-postmortem --root ~/pm-live outputs/monthly/<date>-<slug>-postmortem.md

``data`` prints markdown tables from live files: weekly work mix (rows and
token share), named workflows per week, corrections (excluding subagent results
returning to the main session), corrections per PM message with coverage, returns that
crossed the Plan E stale-session line, correction turns for theming, and outcome counts per
week. It never prints cost; spend comes from the internal cost dashboard.

``check`` exits 1 when a story is missing a required section, opens with
something other than the executive summary, or divides spend by an artifact
count.

``check-postmortem`` exits 1 when a postmortem is missing a required section
or opens with something other than the executive verdict.
"""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import os
import re
import statistics
import sys
from pathlib import Path

TOKEN_COLS = (
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)
INJECTED_PREFIXES = ("<task-notification",)
CONTEXT_COLS = ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
COLD_SHARE = 0.8

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

POSTMORTEM_SECTIONS = (
    ("executive verdict", r"^##\s+executive verdict"),
    ("intended job and success criteria", r"^##\s+intended job"),
    ("lean progression", r"^##\s+lean progression"),
    ("artifact lineage", r"^##\s+artifact lineage"),
    ("what went well", r"^##\s+what went well"),
    ("what went wrong", r"^##\s+what went wrong"),
    ("root causes", r"^##\s+root causes"),
    ("lessons", r"^##\s+lessons"),
    ("prioritized improvements", r"^##\s+prioritized improvements"),
    ("proposed next test", r"^##\s+proposed (?:next|second) test"),
    ("sources and limitations", r"^##\s+sources and limitations"),
    ("review gate", r"^##\s+review gate"),
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


def context(row: dict) -> int:
    total = 0
    for col in CONTEXT_COLS:
        try:
            total += int(row.get(col) or 0)
        except ValueError:
            pass
    return total


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def parse_ts(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00"))


def is_main(row: dict) -> bool:
    return (row.get("is_sidechain") or "no") != "yes"


def pm_messages(rows: list[dict]) -> dict[str, dict]:
    """One entry per PM message (user_uuid). Subagent results are dropped from both sides.

    A row with no user_uuid is left out. Counting it by message_uuid would make one API call
    look like one message. A message is a correction if any of its calls is tagged
    rework_correction, and labeled if any of its calls has a tag other than ``other``.
    """
    msgs: dict[str, dict] = {}
    for r in rows:
        if not is_main(r) or is_injected(r.get("user_excerpt") or "") or not r.get("user_uuid"):
            continue
        m = msgs.setdefault(
            r["user_uuid"],
            {"timestamp": r["timestamp"], "correction": False, "labeled": False},
        )
        category = r.get("category") or "other"
        m["correction"] = m["correction"] or category == "rework_correction"
        m["labeled"] = m["labeled"] or category != "other"
    return msgs


def eligible_returns(rows: list[dict], idle_minutes: int, min_tokens: int) -> list[dict]:
    """First reply of a new PM message in the same session, when the previous call was
    idle_minutes or more earlier and held min_tokens or more of context.

    That reply is the continuation when the work stayed in the same chat. This file has
    no accepted-pick-up link, so a new chat is not scored in its place. A reply that
    starts with !force is included; the median keeps it and the print counts it apart.
    """
    by_session = collections.defaultdict(list)
    for r in rows:
        if is_main(r) and r.get("timestamp"):
            by_session[r["session_id"]].append(r)
    found = []
    for session, calls in by_session.items():
        calls.sort(key=lambda r: r["timestamp"])
        for prev, cur in zip(calls, calls[1:]):
            excerpt = cur.get("user_excerpt") or ""
            if is_injected(excerpt) or (cur.get("user_uuid") and cur.get("user_uuid") == prev.get("user_uuid")):
                continue
            idle = (parse_ts(cur["timestamp"]) - parse_ts(prev["timestamp"])).total_seconds() / 60
            if idle < idle_minutes or context(prev) < min_tokens:
                continue
            size = context(cur)
            try:
                rewritten = int(cur.get("cache_creation_input_tokens") or 0)
            except ValueError:
                rewritten = 0
            found.append({
                "session_id": session,
                "timestamp": cur["timestamp"],
                "rewritten": rewritten,
                "cold": bool(size) and rewritten >= COLD_SHARE * size,
                "forced": excerpt.lstrip().startswith("!force"),
            })
    return found


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


def median(nums: list[int]) -> float | None:
    if not nums:
        return None
    return statistics.median(nums)


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

    msgs = pm_messages(rows)
    out += ["", "### Corrections per PM message, with coverage", ""]
    out.append(
        "Unit: one PM message (`user_uuid`), not one call. Subagent results are left out of "
        "both sides, and so is a row with no `user_uuid`. Labeled = any tag other than `other`."
    )
    for w in weeks:
        wm = [m for m in msgs.values() if week_of(m["timestamp"]) == w]
        n = len(wm)
        labeled = sum(1 for m in wm if m["labeled"])
        fixes = sum(1 for m in wm if m["correction"])
        out.append(
            f"- Week of {w}: corrections {fixes} of {n} PM messages ({pct(fixes, n)}); "
            f"coverage {labeled} of {n} ({pct(labeled, n)}); "
            f"among labeled {fixes} of {labeled} ({pct(fixes, labeled)})"
        )

    idle_minutes = env_int("SESSION_MEMORY_IDLE_MINUTES", 60)
    min_tokens = env_int("SESSION_MEMORY_MIN_TOKENS", 80000)
    returns = eligible_returns(rows, idle_minutes, min_tokens)
    out += ["", "### Returns past the stale-session line (Plan E)", ""]
    out.append(
        f"Line: {idle_minutes}+ minutes since the previous reply and {min_tokens:,}+ tokens of "
        f"context before it. A chat that crosses twice counts twice. Cold = the return wrote "
        f"{round(COLD_SHARE * 100)}% or more of its context from scratch. The median is tokens "
        "written from scratch on the first reply in the chat that continued: the same chat, or "
        "a new chat only when a pick-up was accepted. This file has no pick-up record, so the "
        "reply scored is the one in the same chat. A return that starts with !force stays in "
        "the median and is also counted on its own line. Token counts, not cost."
    )
    for w in weeks:
        wr = [e for e in returns if week_of(e["timestamp"]) == w]
        kept = [e["rewritten"] for e in wr]
        chats = len({e["session_id"] for e in wr})
        cold = sum(1 for e in wr if e["cold"])
        forced = sum(1 for e in wr if e["forced"])
        mid = median(kept)
        mid_text = f"{mid:,.0f}" if mid is not None else "—"
        out.append(
            f"- Week of {w}: {len(wr)} returns in {chats} chats; cold {cold}; "
            f"started with !force {forced}; median from-scratch tokens: {mid_text}"
        )
    forced_all = sum(1 for e in returns if e["forced"])
    mid_all = median([e["rewritten"] for e in returns])
    mid_all_text = f"{mid_all:,.0f}" if mid_all is not None else "—"
    out.append(
        f"- All rows in this file: {len(returns)} eligible returns; "
        f"started with !force {forced_all}; "
        f"median from-scratch tokens: {mid_all_text}"
    )

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


def check_postmortem(text: str) -> list[str]:
    problems: list[str] = []
    headings = [ln.strip().lower() for ln in text.splitlines() if ln.startswith("## ")]
    for name, pattern in POSTMORTEM_SECTIONS:
        if not any(re.match(pattern, h) for h in headings):
            problems.append(f"missing section: {name}")
    if headings and not headings[0].startswith("## executive verdict"):
        problems.append("first section must be the executive verdict")
    return problems


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.story)
    if not path.is_absolute():
        path = Path(args.root).expanduser() / path
    checker = check_postmortem if args.cmd == "check-postmortem" else check_story
    problems = checker(path.read_text(encoding="utf-8"))
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
    p = sub.add_parser("check-postmortem")
    p.add_argument("--root", required=True)
    p.add_argument("story")
    p.set_defaults(fn=cmd_check)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
