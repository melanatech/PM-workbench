#!/usr/bin/env python3
"""PreToolUse on Task|Agent: give every worker the PM's saved rules.

A worker does not see the chat or the CLAUDE.md import. Before this hook, a rule
saved in reference/context/pm-brain.md reached a worker only if the coordinator
remembered to paste it. This reads the file at dispatch and prepends it to the
worker's prompt, and logs which version each worker was given.

Fails open: any error allows the dispatch unchanged.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root  # noqa: E402

PM_BRAIN = "reference/context/pm-brain.md"
MARKER = "[STANDING RULES"
MAX_RULES_CHARS = 9000


def read_rules(workspace: Path) -> tuple[str, str]:
    try:
        text = (workspace / PM_BRAIN).read_text(encoding="utf-8").strip()
    except OSError:
        return "", ""
    if not text:
        return "", ""
    return text[:MAX_RULES_CHARS], hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def build(text: str, version: str) -> str:
    return "\n".join(
        [
            f"{MARKER} from {PM_BRAIN}, read at dispatch, version {version}]",
            "These are the PM's saved rules. Apply each one that governs the file you write or the "
            "text you draft. If the task brief conflicts with one of them, do not choose silently: "
            "follow the rule and name the conflict in your result.",
            "",
            text,
            "[END STANDING RULES]",
            "",
            "",
        ]
    )


def log(workspace: Path, entry: dict) -> None:
    try:
        folder = workspace / "state" / "hooks"
        folder.mkdir(parents=True, exist_ok=True)
        row = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "hook": "inject_standing_rules", **entry}
        with (folder / "hook-log.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass


def main() -> None:
    try:
        data = payload()
        tool_input = data.get("tool_input") or {}
        prompt = tool_input.get("prompt")
        if not isinstance(prompt, str):
            sys.exit(0)
        workspace = Path(root())
        meta = {
            "subagent_type": tool_input.get("subagent_type") or "",
            "description": str(tool_input.get("description") or "")[:80],
        }
        if MARKER in prompt:
            log(workspace, {**meta, "decision": "already present"})
            sys.exit(0)
        text, version = read_rules(workspace)
        if not text:
            log(workspace, {**meta, "decision": "no rules file"})
            sys.exit(0)
        updated = {**tool_input, "prompt": build(text, version) + prompt}
        log(workspace, {**meta, "decision": "injected", "standing_rules_version": version})
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "allow",
                        "updatedInput": updated,
                    }
                }
            )
        )
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        sys.stderr.write(f"[workbench hook] inject_standing_rules skipped: {exc}\n")
        sys.exit(0)


if __name__ == "__main__":
    main()
