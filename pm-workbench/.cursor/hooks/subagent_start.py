#!/usr/bin/env python3
"""subagentStart: log-only. Records whether a Task prompt that edits a shared
artifact carried the dispatch header + number gate, and always allows.

The old deny did not stop workers, and Cursor skips this event on resumed
subagents. The dispatch block is now injected by preToolUse (dispatch_inject.py),
and worker results are checked by subagentStop (subagent_claims_gate.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    emit,
    load_config,
    log_decision,
    looks_like_shared_edit_task,
    project_root,
    prompt_has_design_header,
    prompt_has_number_gate,
    read_stdin_json,
)
from dispatch_inject import DISPATCH_BLOCK_REF, MARKER  # noqa: E402


def main() -> int:
    payload = read_stdin_json()
    root = project_root(payload)
    config = load_config(root)

    task = payload.get("task") or payload.get("prompt") or payload.get("description") or ""
    shared_edit = looks_like_shared_edit_task(task, config)
    missing = []
    if shared_edit and not prompt_has_design_header(task):
        missing.append("dispatch header")
    if shared_edit and not prompt_has_number_gate(task):
        missing.append("number gate")

    log_decision(
        root,
        {
            "hook": "subagentStart",
            "decision": "allow",
            "would_have_denied": bool(missing),
            "missing": missing,
            "dispatch_block_present": MARKER in task or DISPATCH_BLOCK_REF in task,
            "subagent_type": payload.get("subagent_type") or "",
            "subagent_id": payload.get("subagent_id"),
            "conversation_id": payload.get("conversation_id"),
            "parent_conversation_id": payload.get("parent_conversation_id"),
            "payload_keys": sorted(payload.keys()),
            "task_preview": task[:200],
        },
    )
    emit({"permission": "allow"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
