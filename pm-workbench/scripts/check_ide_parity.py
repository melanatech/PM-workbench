#!/usr/bin/env python3
"""Check that each Claude command router has a Cursor, Codex, and VS Code twin, and that hook gates exist."""
from __future__ import annotations

import sys
from pathlib import Path

ROUTERS = (
    "capture",
    "brief",
    "sync",
    "discover",
    "build",
    "report",
    "quick-close",
    "todo",
)


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    missing = []
    for name in ROUTERS:
        paths = [
            root / ".claude" / "commands" / f"{name}.md",
            root / ".cursor" / "commands" / f"{name}.md",
            root / ".codex" / "prompts" / f"{name}.md",
            root / ".github" / "prompts" / f"{name}.prompt.md",
        ]
        for path in paths:
            if not path.is_file():
                missing.append(str(path.relative_to(root)))
    gates = [
        root / ".cursor" / "hooks" / "stop_gate.py",
        root / ".cursor" / "hooks" / "before_mcp.py",
        root / ".codex" / "hooks" / "check_external_artifact.py",
        root / ".github" / "copilot-instructions.md",
        root / ".cursor" / "rules" / "workbench.mdc",
    ]
    for path in gates:
        if not path.is_file():
            missing.append(str(path.relative_to(root)))
    if missing:
        print("MISSING")
        for item in missing:
            print(f"- {item}")
        return 1
    print(f"PASS routers={len(ROUTERS)} gates={len(gates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
