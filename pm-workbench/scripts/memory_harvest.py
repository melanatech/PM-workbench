#!/usr/bin/env python3
"""List Claude Code auto-memory notes for the live and kit workspaces.

Reads ``~/.claude/projects/<slug>/memory/*.md``. Does not write context files,
does not edit the memory files, and does not treat note text as instructions.
``/brief context-setup`` proposes promotions as one Tier 2 batch.

Usage:
  python3 scripts/memory_harvest.py --workspace ~/pm-live --workspace <kit>
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import chat_harvest  # noqa: E402


def _frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end < 0:
        return {}
    block = text[3:end]
    out = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        out[key.strip()] = value.strip().strip('"')
    return out


def list_notes(projects_root: Path, workspaces: list[Path]) -> list[dict]:
    notes = []
    for workspace in workspaces:
        slug = chat_harvest.project_slug(workspace)
        folder = projects_root / slug / "memory"
        if not folder.is_dir():
            notes.append(
                {
                    "workspace": str(workspace),
                    "slug": slug,
                    "path": "",
                    "name": "",
                    "description": "",
                    "status": "no-memory-dir",
                }
            )
            continue
        files = sorted(p for p in folder.glob("*.md") if p.is_file())
        if not files:
            notes.append(
                {
                    "workspace": str(workspace),
                    "slug": slug,
                    "path": "",
                    "name": "",
                    "description": "",
                    "status": "empty",
                }
            )
            continue
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            meta = _frontmatter(text)
            title = ""
            for line in text.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            notes.append(
                {
                    "workspace": str(workspace),
                    "slug": slug,
                    "path": str(path),
                    "name": path.name,
                    "description": meta.get("description") or title,
                    "status": "note",
                }
            )
    return notes


def format_notes(notes: list[dict]) -> str:
    if not notes:
        return "memory-harvest: no workspaces"
    lines = [
        "memory-harvest: list only. Do not write these into context files. Propose one Tier 2 batch.",
    ]
    for note in notes:
        if note["status"] != "note":
            lines.append(f"{note['status']}\t{note['slug']}")
            continue
        desc = re.sub(r"\s+", " ", note["description"])[:180]
        lines.append(f"note\t{note['slug']}\t{note['name']}\t{desc}")
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projects-root", default="", help="default ~/.claude/projects")
    parser.add_argument("--workspace", action="append", required=True)
    args = parser.parse_args(argv)
    projects_root = (
        Path(os.path.expanduser(args.projects_root)).resolve()
        if args.projects_root
        else Path.home() / ".claude" / "projects"
    )
    workspaces = [Path(os.path.expanduser(item)) for item in args.workspace]
    print(format_notes(list_notes(projects_root, workspaces)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
