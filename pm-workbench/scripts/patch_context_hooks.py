#!/usr/bin/env python3
"""Idempotently wire context-grounding + repos-gate hooks into .claude/settings*.json.

Run from kit root:
  python3 scripts/patch_context_hooks.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
CLAUDE = KIT / ".claude"

REPOS_HOOK = {
    "matcher": "Read|Grep|Glob",
    "hooks": [
        {
            "type": "command",
            "command": (
                'PY=$(command -v python3 || command -v python); '
                '"$PY" "$CLAUDE_PROJECT_DIR/.claude/hooks/require_context_preflight_for_repos.py"'
            ),
            "timeout": 20,
        }
    ],
}

GROUNDING = {
    "type": "command",
    "command": (
        'PY=$(command -v python3 || command -v python); '
        '"$PY" "$CLAUDE_PROJECT_DIR/.claude/hooks/check_context_grounding.py"'
    ),
    "timeout": 20,
}


def patch(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.setdefault("hooks", {})
    changed = False
    pre = hooks.setdefault("PreToolUse", [])
    if not any("require_context_preflight_for_repos" in json.dumps(x) for x in pre):
        pre.append(REPOS_HOOK)
        changed = True
    post = hooks.setdefault("PostToolUse", [])
    for entry in post:
        if entry.get("matcher") == "Write|Edit":
            cmds = entry.setdefault("hooks", [])
            if not any("check_context_grounding" in c.get("command", "") for c in cmds):
                cmds.append(GROUNDING)
                changed = True
    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> int:
    any_changed = False
    for name in ("settings.json", "settings.core.json", "settings.full.json"):
        path = CLAUDE / name
        if not path.is_file():
            print(f"skip missing {name}")
            continue
        try:
            if patch(path):
                print(f"patched {name}")
                any_changed = True
            else:
                print(f"ok {name}")
        except PermissionError as e:
            print(f"PERMISSION_DENIED {name}: {e}", file=sys.stderr)
            print(
                "Apply manually: add PreToolUse Read|Grep|Glob -> "
                "require_context_preflight_for_repos.py and PostToolUse "
                "check_context_grounding.py (see SETUP.md).",
                file=sys.stderr,
            )
            return 2
    return 0 if not any_changed else 0


if __name__ == "__main__":
    sys.exit(main())
