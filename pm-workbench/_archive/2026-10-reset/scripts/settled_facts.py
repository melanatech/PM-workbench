#!/usr/bin/env python3
"""Block a draft that reopens a pinned product fact.

Facts live in ``reference/context/settled-facts.md`` (live workspace).
Claude memory notes are not this check. A missing file skips the check.

Each fact is a ``## SF-…`` section:

    ## SF-001
    status: active
    scope: roadmap,insights
    fact: One sentence a person can apply.
    forbid: phrase that reopens the fact
    allow: phrase that means the draft is citing the pin, not reopening it
    source: chat 2026-10-16

``scope`` is a comma list of path substrings. Empty scope matches any scanned file.
``name`` is an optional filename substring (use it so a pin does not hit every draft).
``allow`` phrases are looked for in a short window around each ``forbid`` hit.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

WINDOW = 240
TEXT_SUFFIXES = {".md", ".html", ".htm", ".txt"}
SKIP_PARTS = (
    "reference/context/settled-facts",
    "state/requirements/",
    "outputs/monthly/",
)


@dataclass
class SettledFact:
    id: str
    status: str
    scope: tuple[str, ...]
    name_contains: str
    skip_name: tuple[str, ...]
    fact: str
    forbid: tuple[str, ...]
    allow: tuple[str, ...]
    source: str = ""
    extra: dict[str, str] = field(default_factory=dict)


def facts_path(root: Path) -> Path:
    return root / "reference" / "context" / "settled-facts.md"


def parse_facts(text: str) -> list[SettledFact]:
    chunks = re.split(r"(?m)^##\s+", text)
    facts: list[SettledFact] = []
    for chunk in chunks[1:]:
        lines = chunk.splitlines()
        if not lines:
            continue
        head = lines[0].strip()
        if not head.upper().startswith("SF-"):
            continue
        fields: dict[str, list[str]] = {}
        for line in lines[1:]:
            if not line.strip() or line.strip().startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields.setdefault(key.strip().lower(), []).append(value.strip())
        scope = tuple(p.strip().lower() for p in (fields.get("scope") or [""])[0].split(",") if p.strip())
        facts.append(
            SettledFact(
                id=head.split()[0],
                status=(fields.get("status") or ["active"])[0].lower(),
                scope=scope,
                name_contains=(fields.get("name") or [""])[0].lower(),
                skip_name=tuple(p.strip().lower() for p in (fields.get("skip_name") or [""])[0].split(",") if p.strip()),
                fact=(fields.get("fact") or [""])[0],
                forbid=tuple(fields.get("forbid") or []),
                allow=tuple(a.lower() for a in fields.get("allow") or []),
                source=(fields.get("source") or [""])[0],
            )
        )
    return facts


def load_facts(root: Path) -> list[SettledFact]:
    path = facts_path(root)
    if not path.is_file():
        return []
    return [f for f in parse_facts(path.read_text(encoding="utf-8", errors="replace")) if f.status == "active"]


def _skip(relative: str) -> bool:
    rel = relative.replace("\\", "/")
    if Path(rel).suffix.lower() not in TEXT_SUFFIXES:
        return True
    return any(part in rel for part in SKIP_PARTS)


def _in_scope(fact: SettledFact, relative: str) -> bool:
    rel = relative.replace("\\", "/").lower()
    filename = Path(rel).name
    if fact.name_contains and fact.name_contains not in filename:
        return False
    if any(skip in filename for skip in fact.skip_name):
        return False
    if not fact.scope:
        return True
    return any(part in rel for part in fact.scope)


def violations(text: str, relative: str, facts: list[SettledFact]) -> list[str]:
    if _skip(relative):
        return []
    found: list[str] = []
    lowered = text.lower()
    for fact in facts:
        if not _in_scope(fact, relative):
            continue
        for phrase in fact.forbid:
            needle = phrase.lower()
            if not needle:
                continue
            start = 0
            while True:
                at = lowered.find(needle, start)
                if at < 0:
                    break
                window = lowered[max(0, at - WINDOW) : at + len(needle) + WINDOW]
                if any(allow in window for allow in fact.allow):
                    start = at + len(needle)
                    continue
                found.append(
                    f"{fact.id} reopened ({phrase!r}). {fact.fact} "
                    f"Cite it as settled, or add an allow phrase from the pin. Source: {fact.source or 'settled-facts.md'}."
                )
                break
    return found


def check_file(root: Path, path: Path, relative: str | None = None) -> list[str]:
    rel = relative or str(path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return violations(text, rel, load_facts(root))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a draft against settled facts.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--path", required=True, help="File to check, relative to --root or absolute")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    path = Path(args.path)
    if not path.is_absolute():
        path = root / path
    relative = str(path.resolve().relative_to(root)) if path.resolve().is_relative_to(root) else str(path)
    found = check_file(root, path, relative)
    if not found:
        print(f"settled-facts: ok ({relative})")
        return 0
    print(f"SETTLED FACT BLOCKED in {relative}", file=sys.stderr)
    for line in found:
        print(f"  - {line}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
