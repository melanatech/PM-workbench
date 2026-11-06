#!/usr/bin/env python3
"""Stop hook: warn when a reply narrates in-flight agents.

Exits 0. A blocking Stop hook makes Claude Code regenerate the reply.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, warn  # noqa: E402


def _last_assistant_text(transcript_path: str) -> str:
    if not transcript_path or not os.path.isfile(transcript_path):
        return ""
    last = ""
    try:
        with open(transcript_path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
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
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            parts.append(part.get("text") or "")
                        elif isinstance(part, str):
                            parts.append(part)
                    last = "\n".join(parts)
    except OSError:
        return ""
    return last


def main() -> None:
    try:
        incoming = payload()
        text = _last_assistant_text(incoming.get("transcript_path") or "")
        if not text:
            sys.exit(0)
        workspace = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        sys.path.insert(0, os.path.join(workspace, "scripts"))
        import quiet_progress  # noqa: E402

        hits = quiet_progress.chatter_hits(text)
        if not hits:
            sys.exit(0)
        warn(
            "Quiet batch: do not narrate timers or each agent finish. "
            "One line is allowed — Batch: N of M on disk — then the ## Output index. "
            f"This reply matched: {', '.join(hits)}"
        )
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"check_quiet_progress skipped: {exc}")


if __name__ == "__main__":
    main()
