#!/usr/bin/env python3
"""PostToolUse: block a write that reopens a pinned settled fact."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, payload, rel, root, warn  # noqa: E402


def main() -> None:
    try:
        incoming = payload()
        path = (incoming.get("tool_input", {}) or {}).get("file_path") or ""
        if not path:
            sys.exit(0)
        workspace = root()
        sys.path.insert(0, os.path.join(workspace, "scripts"))
        import settled_facts  # noqa: E402

        relative = rel(path)
        full = path if os.path.isabs(path) else os.path.join(workspace, relative)
        if not os.path.isfile(full):
            sys.exit(0)
        found = settled_facts.check_file(
            settled_facts.Path(workspace),
            settled_facts.Path(full),
            relative,
        )
        if not found:
            sys.exit(0)
        lines = [f"SETTLED FACT BLOCKED in {relative}"]
        lines.extend(f"  - {line}" for line in found)
        lines.append("Read reference/context/settled-facts.md and cite the pin. Do not ask again.")
        block("\n".join(lines))
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"check_settled_facts skipped: {exc}")


if __name__ == "__main__":
    main()
