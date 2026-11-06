#!/usr/bin/env python3
"""Minimum exec-readiness check for an external roadmap.

A pass is not approval and not a gold file. It only blocks a few shapes that
cannot be an exec board: a changelog, a Now column stuffed with a backlog,
and items that are still a TBD label.

Product-specific pins belong in settled-facts, not here.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TEXT_SUFFIXES = {".md", ".html", ".htm", ".txt"}
CHANGELOG = re.compile(
    r"what'?s changed|where this came from|what we dropped",
    re.I,
)
INTERNAL = re.compile(
    r"the pm reviews|proposals, the pm|pm should confirm",
    re.I,
)
TICKET = re.compile(r"\b(?:[A-Z]{2,10}-\d+)\b")
TAG_RE = re.compile(r"<[^>]+>")


def is_external_roadmap(relative: str) -> bool:
    rel = relative.replace("\\", "/").lower()
    if Path(rel).suffix.lower() not in TEXT_SUFFIXES:
        return False
    return rel.startswith("outputs/external/") and "roadmap" in Path(rel).name


def _strip(fragment: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", fragment)).strip()


def now_items(text: str) -> list[str]:
    html = re.search(
        r"(<h[1-4][^>]*>[^<]*\bNow\b.*?)(?=<h[1-4][^>]*>[^<]*\b(?:Next|Later|Trade)|$)",
        text,
        re.I | re.S,
    )
    if html:
        chunk = html.group(1)
        items = [_strip(li) for li in re.findall(r"<li\b[^>]*>(.*?)</li>", chunk, re.I | re.S)]
        items += [_strip(art) for art in re.findall(r"<article\b[^>]*>(.*?)</article>", chunk, re.I | re.S)]
        return [item for item in items if item]
    md = re.search(
        r"(?m)^#{1,3}[^\n]*\bNow\b[^\n]*\n(.*?)(?=^#{1,3} |\Z)",
        text,
        re.I | re.S,
    )
    if not md:
        return []
    return [line.strip() for line in re.findall(r"(?m)^[-*] (.+)$", md.group(1))]


def findings_for(text: str) -> list[str]:
    found: list[str] = []
    if CHANGELOG.search(text):
        found.append("changelog_voice: drop 'what's changed', 'where this came from', and 'what we dropped' — this is the shareable roadmap, not a revision note")
    if INTERNAL.search(text):
        found.append("internal_voice: rewrite process asides ('the pm reviews') into the decision an exec can read")
    items = now_items(text)
    themes = []
    granular = []
    for item in items:
        tickets = TICKET.findall(item)
        words = item.split()
        if len(tickets) >= 3:
            granular.append(item[:80])
        elif len(tickets) == 0 and 2 <= len(words) <= 6:
            themes.append(item[:80])
        if re.search(r"\bTBD\b", item) and len(words) < 12:
            found.append(f"vague_item: {item[:80]!r} is a label without a decision")
        if len(words) > 55:
            found.append(f"over_detail: Now item is {len(words)} words — keep the exec line, move the rest off the board")
        if re.search(r"\brelease notes\b", item, re.I) and not re.search(r"not (repeated|on the roadmap|listed)", item, re.I):
            found.append(f"shipped_in_now: {item[:80]!r} belongs in release notes, not Now")
        if re.fullmatch(r"(event tracking|decision|decisions|review|reviews)", item.split("—")[0].strip(), re.I):
            found.append(f"meta_item: {item[:60]!r} is process, not a roadmap bet")
    if themes and granular:
        found.append(
            "granularity_mix: Now lists theme-level items next to ticket dumps. "
            "One altitude: a bet an exec can rank, with keys in a second line — not a peer of the bet."
        )
    if len(items) > 5:
        found.append(
            f"now_overloaded: Now has {len(items)} items. An exec board is a few bets in priority order, not a backlog. "
            "Saying 'first' does not prioritize a long list."
        )
    return found


def check_file(path: Path, relative: str) -> list[str]:
    if not is_external_roadmap(relative):
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    return findings_for(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check an external roadmap for exec readiness.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--path", required=True)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    path = Path(args.path)
    if not path.is_absolute():
        path = root / path
    relative = str(path.resolve().relative_to(root)) if path.resolve().is_relative_to(root) else path.name
    found = check_file(path, relative)
    if not found:
        print(f"roadmap-audience: ok ({relative})")
        return 0
    print(f"ROADMAP AUDIENCE BLOCKED in {relative}", file=sys.stderr)
    for line in found:
        print(f"  - {line}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
