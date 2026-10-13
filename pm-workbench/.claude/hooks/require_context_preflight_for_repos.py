#!/usr/bin/env python3
"""PreToolUse Read|Grep|Glob: block repos/** without a fresh context preflight marker.

Marker may set allow_repos true after investigate / reuse_and_refresh / --allow-repos.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, payload, rel, root, warn

MARKER_MAX_AGE_HOURS = 4


def _paths_from_payload(p: dict) -> list[str]:
    ti = p.get("tool_input") or {}
    out = []
    for key in ("file_path", "path", "pattern"):
        # pattern is for Grep; still check path
        pass
    for key in ("file_path", "path"):
        v = ti.get(key)
        if isinstance(v, str) and v:
            out.append(v)
    # Grep often uses path
    if ti.get("glob"):
        pass
    return out


def _touches_repos(paths: list[str], rroot: str) -> bool:
    for path in paths:
        try:
            r = rel(path) if os.path.isabs(path) else path.replace("\\", "/")
        except Exception:
            r = path.replace("\\", "/")
        if r.startswith("repos/") or "/repos/" in f"/{r}":
            return True
        # absolute under root/repos
        full = path if os.path.isabs(path) else os.path.join(rroot, path)
        try:
            full = os.path.realpath(full)
            repos = os.path.realpath(os.path.join(rroot, "repos"))
            if full == repos or full.startswith(repos + os.sep):
                return True
        except Exception:
            continue
    return False


def _fresh(marker_path: str) -> bool:
    try:
        mtime = os.path.getmtime(marker_path)
    except OSError:
        return False
    return (datetime.now(timezone.utc).timestamp() - mtime) / 3600.0 <= MARKER_MAX_AGE_HOURS


def main() -> None:
    try:
        p = payload()
        tool = p.get("tool_name") or ""
        # Only gate read-like tools
        if tool and tool not in ("Read", "Grep", "Glob"):
            # matcher should already limit; be safe
            pass
        paths = _paths_from_payload(p)
        # Grep/Glob: path field
        ti = p.get("tool_input") or {}
        if ti.get("path"):
            paths.append(ti["path"])
        rroot = root()
        if not _touches_repos(paths, rroot):
            sys.exit(0)

        marker_path = os.path.join(rroot, "state", ".context-preflight.json")
        if not os.path.isfile(marker_path) or not _fresh(marker_path):
            block(
                "REPOS GATE: run context preflight before reading repos/**.\n"
                "python3 scripts/context_preflight.py --root <live> --topic \"…\"\n"
                "Use --allow-repos when recommendation is investigate/reuse_and_refresh "
                "or after an empty preflight when a code gap requires the clone."
            )
        marker = json.loads(open(marker_path, encoding="utf-8").read())
        if marker.get("allow_repos"):
            sys.exit(0)
        # reuse without allow_repos: block
        block(
            "REPOS GATE: preflight recommendation is "
            f"{marker.get('recommendation')!r} with allow_repos=false.\n"
            "Reuse cited analyses first. To open repos/** after a deliberate refresh "
            "decision, re-run: python3 scripts/context_preflight.py --root <live> "
            "--topic \"…\" --allow-repos (or --verify)."
        )
    except SystemExit:
        raise
    except Exception as e:
        warn(f"require_context_preflight_for_repos skipped: {e}")


if __name__ == "__main__":
    main()
