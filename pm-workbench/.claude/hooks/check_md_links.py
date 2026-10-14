#!/usr/bin/env python3
"""PostToolUse: .md under outputs/drafts/learning/reference/context/state must link paths."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, rel, block, warn
from _paths import find_unlinked_paths, file_relative_href

WATCHED = (
    "outputs/", "drafts/", "learning/",
    "reference/context/", "state/",
)


try:
    p = payload()
    path = (p.get("tool_input", {}) or {}).get("file_path") or ""
    r = rel(path)
    if not r.endswith(".md") or not r.startswith(WATCHED):
        sys.exit(0)
    full = os.path.join(root(), r)
    if not os.path.isfile(full):
        sys.exit(0)
    txt = open(full, encoding="utf-8", errors="replace").read()
    unlinked = find_unlinked_paths(txt, root())
    if not unlinked:
        sys.exit(0)
    lines = [
        f"LINK CHECK FAILED in {r} — use file-relative Markdown links for these existing paths:",
    ]
    for u in unlinked:
        href = file_relative_href(r, u)
        lines.append(f"  `{u}` → `[{u}]({href})`")
    block("\n".join(lines))
except SystemExit:
    raise
except Exception as e:
    warn(f"check_md_links skipped: {e}")
