#!/usr/bin/env python3
"""Fail a new draft that drops an accepted requirement.

Ledgers live in ``state/requirements/<family>.md``. No ledger means the check
passes. A row stays active until its status is ``removed`` or ``replaced``.

    # family: roadmap

    ## RR-01
    status: accepted
    must_include: busiest selling times
    note: First insight stays on the roadmap
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TEXT_SUFFIXES = {".md", ".html", ".htm", ".txt"}


@dataclass
class Requirement:
    id: str
    status: str
    must_include: str
    note: str = ""


def ledger_path(root: Path, family: str) -> Path:
    return root / "state" / "requirements" / f"{family}.md"


def family_for(relative: str) -> str | None:
    """Family key for a shareable draft. Critiques, Slack, and Jira plans are not the board."""
    rel = relative.replace("\\", "/").lower()
    name = Path(rel).name
    if not rel.startswith("outputs/external/"):
        return None
    if any(skip in name for skip in ("slack", "jira", "comms")):
        return None
    if "roadmap" in name:
        return "roadmap"
    if "kr-proposal" in name or name.startswith("kr"):
        return "kr"
    if "strategy" in name or "vision" in name:
        return "strategy"
    return None


def parse_ledger(text: str) -> list[Requirement]:
    chunks = re.split(r"(?m)^##\s+", text)
    rows: list[Requirement] = []
    for chunk in chunks[1:]:
        lines = chunk.splitlines()
        if not lines:
            continue
        head = lines[0].strip().split()[0]
        fields: dict[str, str] = {}
        for line in lines[1:]:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields[key.strip().lower()] = value.strip()
        phrase = fields.get("must_include") or ""
        if not phrase:
            continue
        rows.append(
            Requirement(
                id=head,
                status=(fields.get("status") or "accepted").lower(),
                must_include=phrase,
                note=fields.get("note") or "",
            )
        )
    return rows


def load_ledger(root: Path, family: str) -> list[Requirement]:
    path = ledger_path(root, family)
    if not path.is_file():
        return []
    return [row for row in parse_ledger(path.read_text(encoding="utf-8", errors="replace")) if row.status == "accepted"]


def missing(text: str, rows: list[Requirement]) -> list[str]:
    lowered = text.lower()
    found: list[str] = []
    for row in rows:
        if row.must_include.lower() not in lowered:
            note = f" — {row.note}" if row.note else ""
            found.append(f"{row.id} missing {row.must_include!r}{note}")
    return found


def check_file(root: Path, path: Path, relative: str) -> list[str]:
    if Path(relative).suffix.lower() not in TEXT_SUFFIXES:
        return []
    if relative.replace("\\", "/").startswith("state/requirements/"):
        return []
    family = family_for(relative)
    if not family:
        return []
    rows = load_ledger(root, family)
    if not rows:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return missing(text, rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a draft against its requirements ledger.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--path", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    path = Path(args.path)
    if not path.is_absolute():
        path = root / path
    relative = str(path.resolve().relative_to(root)) if path.resolve().is_relative_to(root) else path.name
    found = check_file(root, path, relative)
    family = family_for(relative) or "(none)"
    if not found:
        print(f"requirements-ledger: ok family={family} ({relative})")
        return 0
    print(f"REQUIREMENTS LEDGER BLOCKED in {relative} (family {family})", file=sys.stderr)
    print("Accepted rows stay until status is removed or replaced:", file=sys.stderr)
    for line in found:
        print(f"  - {line}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
