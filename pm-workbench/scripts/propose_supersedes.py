#!/usr/bin/env python3
"""propose_supersedes.py — one-time migration of registers/decisions.csv to the `supersedes` column (Plan E Part 1).

Three steps, each run on purpose. Nothing is applied without --add-column or --apply.

  python3 scripts/propose_supersedes.py                      # dry run: print the header change and proposed links
  python3 scripts/propose_supersedes.py --add-column         # append an empty `supersedes` column; rows unchanged
  python3 scripts/propose_supersedes.py --write-proposals    # save the Tier 2 batch to outputs/registers/
  python3 scripts/propose_supersedes.py --apply DEC-009=DEC-008 [DEC-065=DEC-035;DEC-064 ...]
                                                             # fill approved links into empty cells only

Proposals come from the same text patterns workbench_metrics.py used before the column existed (supersede,
reverse, replaces, overrule, overrides, plus an earlier id within 60 days). Text matching is a lead, not an
answer: "consistent with DEC-026" is not a reversal. The PM approves each link. Before writing, the file is
copied to state/backups/decisions-<timestamp>.csv.
"""
import argparse
import csv
import datetime
import io
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register_view  # noqa: E402

WORDS = ("supersede", "reverse", "replaces", "overrule", "overrides")
WINDOW_DAYS = 60
PATH = os.path.join("registers", "decisions.csv")


def parse_day(text):
    try:
        return datetime.date.fromisoformat((text or "").strip()[:10])
    except ValueError:
        return None


def proposals(rows):
    out = []
    for row in rows:
        text = (row.get("decision") or "")
        low = text.lower()
        word = next((w for w in WORDS if w in low), None)
        if not word or (row.get("supersedes") or "").strip():
            continue
        new_day, rid = parse_day(row.get("date")), (row.get("id") or "").strip()
        earlier = []
        for old in rows:
            oid = (old.get("id") or "").strip()
            if oid == rid:
                break
            old_day = parse_day(old.get("date"))
            if oid and re.search(rf"\b{re.escape(oid)}\b", text, re.I) and new_day and old_day \
                    and 0 <= (new_day - old_day).days <= WINDOW_DAYS:
                earlier.append(oid)
        if earlier:
            start = max(0, low.find(word) - 80)
            out.append({"id": rid, "supersedes": ";".join(earlier), "word": word,
                        "excerpt": " ".join(text[start:start + 220].split())})
    return out


def backup(root):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(root, "state", "backups", f"decisions-{stamp}.csv")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.copy2(os.path.join(root, PATH), dest)
    return dest


def save(root, fields, rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    with open(os.path.join(root, PATH), "w", newline="", encoding="utf-8") as handle:
        handle.write(buf.getvalue())


def proposals_markdown(found, today):
    lines = [f"# Proposed `supersedes` links for decisions.csv ({today})", "",
             "Tier 2 batch: nothing is applied until the PM approves. Each row is a text match, not a verdict.",
             "Approve with `python3 scripts/propose_supersedes.py --apply NEW=OLD[;OLD] ...`.", "",
             "| New row | Would supersede | Matched word | Text around the match |", "|---|---|---|---|"]
    for item in found:
        lines.append(f"| {item['id']} | {item['supersedes']} | {item['word']} | {item['excerpt'].replace('|', '/')} |")
    if not found:
        lines.append("| — | — | — | No row matched the patterns. |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root")
    parser.add_argument("--add-column", action="store_true")
    parser.add_argument("--write-proposals", action="store_true")
    parser.add_argument("--apply", nargs="*", metavar="NEW=OLD[;OLD]")
    args = parser.parse_args(argv)
    root = os.path.abspath(os.path.expanduser(args.root)) if args.root else register_view._resolve_root()
    fields, rows = register_view.read_rows(root, "decisions")
    has_column = "supersedes" in fields

    if args.add_column:
        if has_column:
            print("supersedes column already present; nothing to do")
            return 0
        print(f"backup: {os.path.relpath(backup(root), root)}")
        save(root, fields + ["supersedes"], [{**r, "supersedes": ""} for r in rows])
        print(f"added supersedes column to {PATH}; {len(rows)} rows unchanged")
        return 0

    if args.apply is not None:
        if not has_column:
            print("run --add-column first", file=sys.stderr)
            return 2
        by_id = {(r.get("id") or "").strip(): r for r in rows}
        for pair in args.apply:
            new, _, olds = pair.partition("=")
            if new not in by_id or not olds:
                print(f"skip {pair}: expected NEW=OLD with an existing NEW id", file=sys.stderr)
                return 2
            if (by_id[new].get("supersedes") or "").strip():
                print(f"skip {pair}: {new} already has supersedes={by_id[new]['supersedes']}", file=sys.stderr)
                return 2
            by_id[new]["supersedes"] = olds
        bad = register_view.problems(rows)
        if bad:
            print("not applied; link errors:\n  " + "\n  ".join(bad), file=sys.stderr)
            return 1
        print(f"backup: {os.path.relpath(backup(root), root)}")
        save(root, fields, rows)
        print(f"applied {len(args.apply)} link(s); {len(register_view.superseded_by(rows))} decision(s) now superseded")
        return 0

    found = proposals(rows)
    today = datetime.date.today().isoformat()
    if args.write_proposals:
        dest = os.path.join(root, "outputs", "registers", f"{today}-supersedes-proposals.md")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as handle:
            handle.write(proposals_markdown(found, today))
        print(f"wrote {os.path.relpath(dest, root)}")
        return 0
    print(f"{PATH}: {len(rows)} rows; supersedes column {'present' if has_column else 'missing (run --add-column)'}")
    print(proposals_markdown(found, today))
    return 0


if __name__ == "__main__":
    sys.exit(main())
