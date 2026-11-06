#!/usr/bin/env python3
"""Job card: finish line for a multi-draft run.

``state/job-card.md`` names the job, audience, due date, stop rule, and the
workstreams that may be written. With ``enforce: on``, a draft whose path
matches none of those streams is blocked. A missing card does not block
ordinary writes. ``check`` fails when dispatch is about to start without a
complete card.

    enforce: on
    job: One sentence finish line
    audience: who will read the result
    due: 2026-10-16
    stop: Do not start a workstream that is not listed
    streams: roadmap, release notes
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

GATED_PREFIXES = (
    "outputs/external/",
    "outputs/strategy/",
    "outputs/todo-drafts/",
    "roadmap/",
)
REQUIRED = ("job", "audience", "due", "stop", "streams")


@dataclass
class JobCard:
    enforce: bool
    job: str
    audience: str
    due: str
    stop: str
    streams: tuple[str, ...]

    def missing_fields(self) -> list[str]:
        blank = []
        for name in REQUIRED:
            value = getattr(self, name)
            if name == "streams":
                if not value:
                    blank.append(name)
            elif not str(value).strip():
                blank.append(name)
        return blank


def card_path(root: Path) -> Path:
    return root / "state" / "job-card.md"


def _fields(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for line in text.splitlines():
        if ":" not in line or line.startswith("#"):
            continue
        key, value = line.split(":", 1)
        found[key.strip().lower()] = value.strip()
    return found


def parse_card(text: str) -> JobCard:
    fields = _fields(text)
    raw = fields.get("streams") or ""
    streams = tuple(part.strip() for part in raw.split(",") if part.strip())
    return JobCard(
        enforce=(fields.get("enforce") or "").lower() == "on",
        job=fields.get("job") or "",
        audience=fields.get("audience") or "",
        due=fields.get("due") or "",
        stop=fields.get("stop") or "",
        streams=streams,
    )


def load_card(root: Path) -> JobCard | None:
    path = card_path(root)
    if not path.is_file():
        return None
    return parse_card(path.read_text(encoding="utf-8", errors="replace"))


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def gated(relative: str) -> bool:
    rel = relative.replace("\\", "/")
    if rel == "state/job-card.md" or rel.startswith("outputs/monthly/"):
        return False
    return rel.startswith(GATED_PREFIXES)


def stream_block(relative: str, card: JobCard | None) -> list[str]:
    """Findings for a write. Empty when the card is absent or not enforcing."""
    if card is None or not card.enforce or not gated(relative):
        return []
    missing = card.missing_fields()
    if missing:
        return [f"job card is on but incomplete: {', '.join(missing)}"]
    path_key = _norm(relative)
    if any(_norm(stream) and _norm(stream) in path_key for stream in card.streams):
        return []
    listed = ", ".join(card.streams)
    return [
        f"workstream not on the job card ({listed}). "
        "Add the stream only after the PM expands the job. Do not start it in this write."
    ]


def check_card(card: JobCard | None) -> list[str]:
    if card is None:
        return ["state/job-card.md is missing. Write it before dispatch."]
    if not card.enforce:
        return ["job card enforce is not on."]
    missing = card.missing_fields()
    if missing:
        return [f"job card missing: {', '.join(missing)}"]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check the session job card.")
    parser.add_argument("--root", default=".")
    parser.add_argument("command", nargs="?", default="check", choices=("check",))
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    problems = check_card(load_card(root))
    if problems:
        print("JOB CARD BLOCKED", file=sys.stderr)
        for line in problems:
            print(f"  - {line}", file=sys.stderr)
        return 2
    card = load_card(root)
    print(f"job-card: ok streams={', '.join(card.streams if card else ())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
