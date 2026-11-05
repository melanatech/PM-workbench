#!/usr/bin/env python3
"""PostToolUse: an edit to a kit file must not name a person, company, project, or internal system.

Resolves symlinks, so an edit made through a live workspace that links `.claude/`,
`scripts/`, or `tests/` into the kit is checked too. Files outside the kit repo,
and gitignored local files, are skipped. Terms: `scripts/check_kit_generic.py`.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, block, warn

KIT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KIT / "scripts"))

try:
    import check_kit_generic as ckg

    p = payload()
    path = (p.get("tool_input", {}) or {}).get("file_path") or ""
    if not path:
        sys.exit(0)
    full = Path(path).resolve()
    if not ckg.in_kit(full) or not full.is_file():
        sys.exit(0)
    import subprocess
    ignored = subprocess.run(["git", "check-ignore", "-q", str(full)], cwd=ckg.REPO).returncode == 0
    if ignored:
        sys.exit(0)
    hits = ckg.scan([full])
    if hits:
        block(
            "This edit puts specific context into the public kit:\n"
            + "\n".join("  " + h for h in hits[:20])
            + "\n" + ckg.FIX
        )
except SystemExit:
    raise
except Exception as e:  # fail open
    warn(f"check_kit_generic: {e}")
