#!/usr/bin/env python3
"""PostToolUse: block an external roadmap that is not exec-readable."""
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
        import roadmap_audience  # noqa: E402

        relative = rel(path)
        full = path if os.path.isabs(path) else os.path.join(workspace, relative)
        if not os.path.isfile(full):
            sys.exit(0)
        found = roadmap_audience.check_file(roadmap_audience.Path(full), relative)
        if not found:
            sys.exit(0)
        lines = [f"ROADMAP AUDIENCE BLOCKED in {relative}"]
        lines.extend(f"  - {line}" for line in found)
        block("\n".join(lines))
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"check_roadmap_audience skipped: {exc}")


if __name__ == "__main__":
    main()
