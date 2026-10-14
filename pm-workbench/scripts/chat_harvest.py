#!/usr/bin/env python3
"""Harvest the PM's own Claude Code messages since a cursor.

Reuses ``scripts/transcripts.py`` (user turns only). Usage metrics stay in
``session_usage.py``. This script extracts candidate statements and writes
``state/chat-harvest/[date].md``. It does not read assistant text and it does
not write durable context files.

Usage:
  python3 scripts/chat_harvest.py --root ~/pm-live
  python3 scripts/chat_harvest.py --root ~/pm-live --workspace ~/pm-live --workspace ~/PM-workbench/pm-workbench

Cursor: ``state/.chat-harvest-cursor`` (ISO timestamp). Turns at or before
that timestamp are skipped. The cursor advances to the newest turn seen,
including ones the fact filter dropped, so the next run does not rescan them.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import transcripts  # noqa: E402

CURSOR_NAME = ".chat-harvest-cursor"
EXCERPT_MAX = 400

FACT_CUES = (
    "decided",
    "decision",
    "confirmed",
    "confirm",
    "priority",
    "priorities",
    "owner",
    "due ",
    "because",
    "we should",
    "i'll ",
    "i will ",
    "commitment",
    "risk",
    "metric",
    "actually",
    "correction",
    "agreed",
    "said ",
    "ship ",
    "launch",
)

ACKS = {
    "thanks",
    "thank you",
    "ok",
    "okay",
    "yes",
    "no",
    "yep",
    "nope",
    "lgtm",
    "sounds good",
    "got it",
}


def project_slug(workspace: Path) -> str:
    """Claude Code project-folder name for a workspace path."""
    resolved = workspace.expanduser().resolve()
    return "-" + resolved.as_posix().lstrip("/").replace("/", "-")


def is_fact_like(text: str) -> bool:
    """Cheap keep-filter. The workflow classifies what remains."""
    raw = (text or "").strip()
    if len(raw) < 40:
        return False
    if raw.startswith("/") or raw.startswith("<command") or raw.startswith("<local-command"):
        return False
    if "<command-name>" in raw or "<command-args>" in raw:
        return False
    folded = re.sub(r"\s+", " ", raw).strip().lower().strip(".!")
    if folded in ACKS:
        return False
    lower = folded
    if any(cue in lower for cue in FACT_CUES):
        return True
    if re.search(r"\b20\d{2}-\d{2}-\d{2}\b", raw):
        return True
    if re.search(r"\b(?:INIT|DEC|COM|RISK|EV|TODO)-\d+\b", raw):
        return True
    if len(raw) > 80 and any(word in f" {lower} " for word in (" is ", " are ", " was ", " were ")):
        return True
    return False


def excerpt(text: str) -> str:
    one = re.sub(r"\s+", " ", text).strip()
    if len(one) > EXCERPT_MAX:
        return one[: EXCERPT_MAX - 1] + "…"
    return one


def read_cursor(root: Path) -> str:
    path = root / "state" / CURSOR_NAME
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0].strip()


def write_cursor(root: Path, timestamp: str) -> None:
    path = root / "state" / CURSOR_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(timestamp.strip() + "\n", encoding="utf-8")


def _after_cursor(timestamp: str, cursor: str) -> bool:
    if not cursor:
        return True
    if not timestamp:
        return False
    return timestamp > cursor


def harvest(
    root: Path,
    *,
    projects_root: Path | None = None,
    workspaces: list[Path] | None = None,
    today: date | None = None,
) -> dict:
    """Write candidates and advance the cursor. Returns a small summary."""
    cursor = read_cursor(root)
    projects_dirs = None
    if workspaces:
        base = projects_root or (Path.home() / ".claude" / "projects")
        projects_dirs = []
        for workspace in workspaces:
            folder = base / project_slug(workspace)
            if folder.is_dir():
                projects_dirs.append(folder)
    turns = list(
        transcripts.iter_user_turns(
            projects_dirs=projects_dirs,
            projects_root=projects_root,
        )
    )
    seen = [t for t in turns if _after_cursor(t.timestamp, cursor)]
    kept = [t for t in seen if is_fact_like(t.text)]
    newest = cursor
    for turn in seen:
        if turn.timestamp and turn.timestamp > newest:
            newest = turn.timestamp
    wrote = ""
    if kept:
        day = (today or date.today()).isoformat()
        out_dir = root / "state" / "chat-harvest"
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{day}.md"
        block = _render(kept, cursor_before=cursor, cursor_after=newest)
        if path.is_file():
            with path.open("a", encoding="utf-8") as handle:
                handle.write("\n" + block)
        else:
            path.write_text(block, encoding="utf-8")
        wrote = str(path.relative_to(root)).replace("\\", "/")
    if newest and newest != cursor:
        write_cursor(root, newest)
    return {
        "cursor_before": cursor,
        "cursor_after": newest,
        "seen": len(seen),
        "kept": len(kept),
        "path": wrote,
    }


def _render(turns, *, cursor_before: str, cursor_after: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        f"# Chat harvest {stamp}",
        "",
        f"cursor_before: {cursor_before or '(none)'}",
        f"cursor_after: {cursor_after or '(none)'}",
        "source: PM user turns only (scripts/transcripts.py). No assistant text.",
        "These are candidates. Do not copy them into durable files until the Tier 2 batch is accepted. Quote the minimum.",
        "",
        "## Candidates",
        "",
    ]
    for index, turn in enumerate(turns, start=1):
        lines.extend(
            [
                f"### {index}",
                f"- timestamp: {turn.timestamp}",
                f"- session: {turn.session_id}",
                f"- project: {turn.project}",
                f"- entrypoint: {turn.entrypoint}",
                f"- excerpt: {excerpt(turn.text)}",
                "",
            ]
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="live workspace")
    parser.add_argument(
        "--projects-root",
        default="",
        help="Claude projects directory (default ~/.claude/projects)",
    )
    parser.add_argument(
        "--workspace",
        action="append",
        default=[],
        help="limit to this workspace's project slug; repeat for kit + live",
    )
    args = parser.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    projects_root = Path(os.path.expanduser(args.projects_root)).resolve() if args.projects_root else None
    workspaces = [Path(os.path.expanduser(item)) for item in args.workspace] or None
    summary = harvest(root, projects_root=projects_root, workspaces=workspaces)
    print(
        f"chat-harvest: seen={summary['seen']} kept={summary['kept']} "
        f"path={summary['path'] or '(none)'} cursor={summary['cursor_after'] or '(none)'}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
