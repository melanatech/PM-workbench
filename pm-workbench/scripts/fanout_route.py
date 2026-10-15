#!/usr/bin/env python3
"""Map a captured item type to the fan-out surfaces that can receive it.

Capture workflows tag each extracted item, then read and write only the
surfaces this table names. Mechanical writes (analysis index, staleness,
metric rows) are script calls. Learning digests stay a judgment step.

Usage:
  python3 scripts/fanout_route.py --types decision,evidence
  python3 scripts/fanout_route.py --check
"""
from __future__ import annotations

import argparse
import re
import sys

# Surface numbers match `.claude/workflows/_fan-out.md`. Do not add a number
# here unless a type has nowhere to go.
SURFACES = {
    1: "registers/decisions.csv, commitments.csv, risks.csv",
    2: "registers/evidence.csv",
    3: "registers/initiatives.csv",
    4: "reference/context/assumptions-and-open-questions.md",
    5: "reference/context/current-priorities.md",
    6: "learning/ (area file and learning/entities/ when a named entity is claimed)",
    7: "reference/user-research/",
    8: "state/competitive/ and outputs/monthly/competitive-log.md",
    9: "outputs/todo-proposals/",
    10: "drafts/",
    11: "reference/context/glossary.md",
    12: "state/okr-history.csv",
    13: "state/analysis-index.csv",
    14: "state/web-search/",
    15: "state/source-index.csv",
}

# Type -> surfaces to read and, when the item applies, write.
# Surface 3 is included for types that can name an initiative.
# Surface 5 for strategy-frame is proposal-only (Tier 3); never a direct write.
# Surface 10 is included for follow-up only when the workflow is already drafting a ticket.
# Surface 15 is written by source triage for every classified source.
ROUTES = {
    "decision": (1, 3, 5),
    "commitment": (1,),
    "risk": (1, 5),
    "evidence": (2, 3, 7),
    "metric": (12,),
    "competitor": (3, 8),
    "term": (11,),
    "durable-product-fact": (3, 6),
    "assumption": (4,),
    "follow-up": (9, 10),
    "analysis": (13,),
    "external-grounding": (14,),
    "strategy-frame": (3, 4, 5, 6, 12, 15),
    "semantic-definition": (3, 4, 6, 13, 15),
    "stakeholder-stance": (15,),
}


def normalize_type(name: str) -> str:
    return re.sub(r"[\s_]+", "-", (name or "").strip().lower())


def routes_for(types: list[str]) -> dict[str, tuple[int, ...]]:
    out = {}
    for raw in types:
        key = normalize_type(raw)
        if key not in ROUTES:
            raise KeyError(key)
        out[key] = ROUTES[key]
    return out


def surfaces_for(types: list[str]) -> list[int]:
    found = []
    seen = set()
    for numbers in routes_for(types).values():
        for number in numbers:
            if number not in seen:
                seen.add(number)
                found.append(number)
    return found


def orphan_surfaces() -> list[int]:
    used = {number for numbers in ROUTES.values() for number in numbers}
    return sorted(set(SURFACES) - used)


def unused_types() -> list[str]:
    return sorted(key for key, numbers in ROUTES.items() if not numbers)


def check() -> list[str]:
    problems = []
    orphans = orphan_surfaces()
    if orphans:
        problems.append("orphan surfaces: " + ", ".join(str(n) for n in orphans))
    empty = unused_types()
    if empty:
        problems.append("types with no surface: " + ", ".join(empty))
    for key, numbers in ROUTES.items():
        unknown = [n for n in numbers if n not in SURFACES]
        if unknown:
            problems.append(f"{key} names unknown surfaces {unknown}")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--types", default="", help="comma-separated item types")
    parser.add_argument("--check", action="store_true", help="exit 1 if a surface or type is orphaned")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        if problems:
            print("\n".join(problems), file=sys.stderr)
            return 1
        print(f"fanout-route: ok types={len(ROUTES)} surfaces={len(SURFACES)}")
        return 0
    if not args.types:
        print("ERROR: pass --types or --check", file=sys.stderr)
        return 2
    try:
        mapping = routes_for([part for part in args.types.split(",") if part.strip()])
    except KeyError as error:
        print(f"ERROR: unknown type {error.args[0]}", file=sys.stderr)
        return 2
    for key, numbers in mapping.items():
        names = "; ".join(f"{n}:{SURFACES[n]}" for n in numbers)
        print(f"{key}\t{','.join(str(n) for n in numbers)}\t{names}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
