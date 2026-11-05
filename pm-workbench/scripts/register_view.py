#!/usr/bin/env python3
"""register_view.py — the one reader for current decisions (Plan E Part 1). Standard library only.

decisions.csv is append-only history. A later row that overrides an earlier one lists the earlier id
(or ids, separated by `;`) in its `supersedes` column; the earlier row is never edited. A row is
active unless a later row lists it. Workflows read current state through `active`, never the raw file.

Usage (from the workspace root)
  python3 scripts/register_view.py active decisions               # active rows, same columns, CSV
  python3 scripts/register_view.py active decisions --affects X   # only rows whose affects mentions X
  python3 scripts/register_view.py history decisions --id DEC-012 # the full chain, oldest first, with status
  python3 scripts/register_view.py integrity decisions            # dangling or self links, possible unrecorded
                                                                  # reversals, recent outputs citing a superseded id

A file without a `supersedes` column (before the one-time migration) reads as all rows active.
"""
import argparse
import csv
import datetime
import glob
import os
import re
import sys

REGISTERS = {"decisions": os.path.join("registers", "decisions.csv")}
ID_RE = re.compile(r"\bDEC-\d+\b")
CITE_WINDOW_DAYS = 7


def _resolve_root():
    for candidate in (os.environ.get("CLAUDE_PROJECT_DIR"), os.environ.get("PM_LIVE_ROOT"), os.getcwd()):
        if candidate and os.path.isdir(os.path.join(os.path.abspath(os.path.expanduser(candidate)), "registers")):
            return os.path.abspath(os.path.expanduser(candidate))
    return os.getcwd()


def parse_ids(cell):
    return [part.strip() for part in (cell or "").split(";") if part.strip()]


def superseded_by(rows):
    """{old_id: [ids of later rows that list it]}. Only links pointing at an earlier row count."""
    seen, out = set(), {}
    for row in rows:
        rid = (row.get("id") or "").strip()
        for old in parse_ids(row.get("supersedes")):
            if old in seen and old != rid:
                out.setdefault(old, []).append(rid)
        if rid:
            seen.add(rid)
    return out


def active_rows(rows):
    gone = superseded_by(rows)
    return [r for r in rows if (r.get("id") or "").strip() not in gone]


def chain(rows, target):
    """Every row linked to target through supersedes, either direction, in file order."""
    links = {}
    for row in rows:
        rid = (row.get("id") or "").strip()
        for old in parse_ids(row.get("supersedes")):
            links.setdefault(rid, set()).add(old)
            links.setdefault(old, set()).add(rid)
    found, todo = set(), [target]
    while todo:
        cur = todo.pop()
        if cur in found:
            continue
        found.add(cur)
        todo.extend(links.get(cur, ()))
    return [r for r in rows if (r.get("id") or "").strip() in found]


def problems(rows):
    """Link errors a writer must not save: unknown id, self link, or a link to a later row."""
    out, seen = [], set()
    all_ids = {(r.get("id") or "").strip() for r in rows}
    for row in rows:
        rid = (row.get("id") or "").strip()
        for old in parse_ids(row.get("supersedes")):
            if old == rid:
                out.append(f"{rid} supersedes itself")
            elif not re.fullmatch(r"DEC-\d+", old):
                out.append(f"{rid} supersedes '{old}', which is not a DEC- id")
            elif old not in all_ids:
                out.append(f"{rid} supersedes {old}, which does not exist")
            elif old not in seen:
                out.append(f"{rid} supersedes {old}, which comes after it")
        seen.add(rid)
    return out


def read_rows(root, register):
    path = os.path.join(root, REGISTERS[register])
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def write_rows(fields, rows, out=sys.stdout):
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)


def recent_citations(root, rows, today=None):
    """(path, id) for outputs changed in the last CITE_WINDOW_DAYS that cite a superseded id."""
    gone = superseded_by(rows)
    if not gone:
        return []
    today = today or datetime.date.today()
    cutoff = datetime.datetime.combine(today - datetime.timedelta(days=CITE_WINDOW_DAYS), datetime.time())
    hits = []
    for path in sorted(glob.glob(os.path.join(root, "outputs", "**", "*.md"), recursive=True)):
        if datetime.datetime.fromtimestamp(os.path.getmtime(path)) < cutoff:
            continue
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for did in sorted(set(ID_RE.findall(text)) & set(gone)):
            near = [line for line in text.splitlines() if did in line]
            if all(re.search(r"supersed|revers|replac|histor|was:", line, re.I) for line in near):
                continue
            hits.append((os.path.relpath(path, root), did))
    return hits


def unlinked_same_affects(rows):
    """Pairs of active decisions with the same non-empty affects value and no link: possible unrecorded reversals."""
    by_affects = {}
    for row in active_rows(rows):
        key = (row.get("affects") or "").strip().lower()
        if key:
            by_affects.setdefault(key, []).append((row.get("id") or "").strip())
    return {k: v for k, v in by_affects.items() if len(v) > 1}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("view", choices=["active", "history", "integrity"])
    parser.add_argument("register", choices=sorted(REGISTERS))
    parser.add_argument("--id")
    parser.add_argument("--affects")
    parser.add_argument("--root")
    args = parser.parse_args(argv)
    root = os.path.abspath(os.path.expanduser(args.root)) if args.root else _resolve_root()
    try:
        fields, rows = read_rows(root, args.register)
    except OSError as exc:
        print(f"cannot read {REGISTERS[args.register]}: {exc}", file=sys.stderr)
        return 2
    if args.view == "active":
        keep = active_rows(rows)
        if args.affects:
            keep = [r for r in keep if args.affects.lower() in (r.get("affects") or "").lower()]
        write_rows(fields, keep)
        return 0
    if args.view == "history":
        if not args.id:
            print("history needs --id DEC-nnn", file=sys.stderr)
            return 2
        linked = chain(rows, args.id.strip())
        if not linked:
            print(f"{args.id} not found", file=sys.stderr)
            return 1
        gone = superseded_by(rows)
        out_fields = fields + ["status"]
        write_rows(out_fields, [{**r, "status": "superseded by " + ";".join(gone[r["id"].strip()])
                                 if r["id"].strip() in gone else "active"} for r in linked])
        return 0
    bad = problems(rows)
    cites = recent_citations(root, rows)
    pairs = unlinked_same_affects(rows)
    print(f"# decisions integrity: {len(rows)} rows, {len(active_rows(rows))} active, "
          f"{len(superseded_by(rows))} superseded")
    print(f"link errors: {len(bad)}")
    for line in bad:
        print(f"  - {line}")
    print(f"outputs from the last {CITE_WINDOW_DAYS} days citing a superseded id: {len(cites)}")
    for path, did in cites:
        print(f"  - {path} cites {did}")
    print(f"active decisions sharing an affects value with no link (check for an unrecorded reversal): {len(pairs)}")
    for key, ids in sorted(pairs.items()):
        print(f"  - {key}: {', '.join(ids)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
