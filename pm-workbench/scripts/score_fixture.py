#!/usr/bin/env python3
"""score_fixture.py — score a fixture run against its gold answer set (Plan C regression check).

You still run the command in Claude Code (for example `/capture meeting-closeout
inbox/meetings/2026-07-14-roadmap-review.txt` in a workspace made by
`scripts/load_fixture.py lumenly --isolate PATH`). This script only reads the resulting
registers and reports, per register, items FOUND, MISSED and INVENTED against
fixtures/lumenly/gold.json. Standard library only; no model, no network.

  python3 scripts/score_fixture.py                    # score the registers in this workbench
  python3 scripts/score_fixture.py --root PATH        # score another workspace (the isolated copy)
  python3 scripts/score_fixture.py --gold PATH --json

Definitions
  found      a register row (not one of the preloaded fixture rows) matches an expected item: every
             word in `all` appears and at least one in `any` does (case-insensitive)
  missed     an expected item no row matched
  invented   a new row that matches no expected item, a row with a date outside `allowed_dates`,
             an expected risk logged without any `must_mark_unconfirmed` marker (stated as a fact),
             or forbidden text anywhere in the new rows
Exit code 0 when nothing was missed and nothing invented, else 1. A pass is a regression
signal for this one fixture; it does not show the kit helps in real work.
"""
import argparse
import csv
import json
import os
import re
import sys

DEFAULT_GOLD = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "fixtures", "lumenly", "gold.json")
REGISTERS = {"decisions": "decisions.csv", "commitments": "commitments.csv", "risks": "risks.csv"}
DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def read_rows(path):
    if not os.path.isfile(path):
        return []
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle))


def row_text(row):
    return " ".join(str(v) for v in row.values()).lower()


def matches(item, text):
    return all(w.lower() in text for w in item.get("all", [])) and \
        (not item.get("any") or any(w.lower() in text for w in item["any"]))


def score(root, gold):
    preloaded = set(gold.get("preloaded_ids", []))
    allowed = set(gold.get("allowed_dates", []))
    result = {}
    for kind, filename in REGISTERS.items():
        rows = [r for r in read_rows(os.path.join(root, "registers", filename))
                if (r.get("id") or "").strip() not in preloaded]
        expected = gold.get("expected", {}).get(kind, [])
        found, missed, invented, used = [], [], [], set()
        for item in expected:
            hit = next((i for i, r in enumerate(rows) if i not in used and matches(item, row_text(r))), None)
            if hit is None:
                missed.append(item["name"])
                continue
            used.add(hit)
            text = row_text(rows[hit])
            markers = item.get("must_mark_unconfirmed")
            if markers and not any(m in text for m in markers):
                invented.append(f"{rows[hit].get('id', '?')}: '{item['name']}' stated as fact, no unconfirmed marker")
            found.append(item["name"])
        for i, row in enumerate(rows):
            text = row_text(row)
            if i not in used:
                invented.append(f"{row.get('id', '?')}: matches no expected {kind[:-1]}")
            for date in DATE_RE.findall(text):
                if allowed and date not in allowed:
                    invented.append(f"{row.get('id', '?')}: date {date} not in the fixture")
            for bad in gold.get("forbidden_text", []):
                if bad.lower() in text:
                    invented.append(f"{row.get('id', '?')}: forbidden text '{bad}'")
        result[kind] = {"found": found, "missed": missed, "invented": invented}
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    parser.add_argument("--gold", default=DEFAULT_GOLD)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        with open(args.gold, encoding="utf-8") as handle:
            gold = json.load(handle)
    except (OSError, ValueError) as error:
        print(f"score_fixture: cannot read gold file: {error}", file=sys.stderr)
        return 2
    result = score(args.root, gold)
    bad = any(v["missed"] or v["invented"] for v in result.values())
    if args.json:
        print(json.dumps({"pass": not bad, "registers": result}, indent=2))
    else:
        for kind, v in result.items():
            print(f"{kind}: found {len(v['found'])}, missed {len(v['missed'])}, invented {len(v['invented'])}")
            for line in v["missed"]:
                print(f"  MISSED   {line}")
            for line in v["invented"]:
                print(f"  INVENTED {line}")
        print("PASS" if not bad else "FAIL")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
