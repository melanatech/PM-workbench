#!/usr/bin/env python3
"""PostToolUse: block a draft that is outside the job card's streams."""
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
        import job_card  # noqa: E402

        relative = rel(path)
        found = job_card.stream_block(relative, job_card.load_card(job_card.Path(workspace)))
        if not found:
            sys.exit(0)
        lines = [f"JOB CARD BLOCKED in {relative}"]
        lines.extend(f"  - {line}" for line in found)
        lines.append("Edit state/job-card.md only when the PM expands the job.")
        block("\n".join(lines))
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"check_job_card skipped: {exc}")


if __name__ == "__main__":
    main()
