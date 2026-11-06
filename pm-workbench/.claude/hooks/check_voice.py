#!/usr/bin/env python3
"""PreToolUse on Write|Edit: judge a team-facing draft before it is saved.

The judgment is semantic (scripts/check_voice.py). A failing draft is refused.
If the judge cannot run, the hook warns and allows the write.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
from _common import block, payload, rel, warn  # noqa: E402
import check_voice  # noqa: E402

MIN_EDIT = check_voice.MIN_EDIT_CHARS


def _text_for(tool: str, incoming: dict, existing: str) -> str | None:
    tool_input = incoming.get("tool_input") or {}
    if tool == "Write":
        return tool_input.get("content") or ""
    new = tool_input.get("new_string") or ""
    if len(new) < MIN_EDIT:
        return None
    return new


def main() -> None:
    try:
        if os.environ.get("CHECK_VOICE_DISABLE") == "1":
            sys.exit(0)
        incoming = payload()
        tool_input = incoming.get("tool_input") or {}
        path = tool_input.get("file_path") or ""
        relative = rel(path)
        sample = tool_input.get("content") or tool_input.get("new_string") or ""
        if not check_voice.is_team_facing(relative, sample):
            sys.exit(0)
        text = _text_for(incoming.get("tool_name") or "", incoming, "")
        if text is None:
            sys.exit(0)
        workspace = check_voice.Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        verdict = check_voice.judge(text, workspace, relative=relative)
        if verdict.unavailable:
            warn(check_voice.report(relative, verdict))
        if verdict.ok:
            sys.exit(0)
        block(check_voice.report(relative, verdict))
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"check_voice skipped: {exc}")


if __name__ == "__main__":
    main()
