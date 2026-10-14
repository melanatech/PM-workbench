#!/usr/bin/env python3
"""Stop hook: last assistant message must link every existing workspace path.

Exit 2 → Claude Code asks the model to fix the reply in the same turn.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, block, warn
from _paths import find_unlinked_paths


def _last_assistant_text(transcript_path: str) -> str:
    if not transcript_path or not os.path.isfile(transcript_path):
        return ""
    last = ""
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                role = obj.get("role") or (obj.get("message") or {}).get("role")
                if role != "assistant":
                    continue
                content = obj.get("content") or (obj.get("message") or {}).get("content")
                if isinstance(content, str):
                    last = content
                elif isinstance(content, list):
                    parts = []
                    for c in content:
                        if isinstance(c, dict) and c.get("type") == "text":
                            parts.append(c.get("text") or "")
                        elif isinstance(c, str):
                            parts.append(c)
                    last = "\n".join(parts)
    except OSError:
        return ""
    return last


try:
    p = payload()
    tp = p.get("transcript_path") or ""
    text = _last_assistant_text(tp)
    if not text or len(text) < 40:
        sys.exit(0)
    # Skip pure tool-result dumps with no prose (heuristic)
    unlinked = find_unlinked_paths(text, root())
    if not unlinked:
        sys.exit(0)
    lines = [
        "LINK CHECK FAILED — convert these existing paths to workspace-relative Markdown links:",
    ]
    for u in unlinked:
        lines.append(f"  `{u}` → `[{u}]({u})`")
    lines.append(
        "Rule 20: every existing file/folder mentioned in the reply must be clickable. "
        "Rewrite the reply with links (exceptions: fenced code, shell commands, globs, missing paths)."
    )
    block("\n".join(lines))
except SystemExit:
    raise
except Exception as e:
    warn(f"check_reply_links skipped: {e}")
