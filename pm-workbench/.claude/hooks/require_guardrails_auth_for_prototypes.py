#!/usr/bin/env python3
"""PreToolUse Write|Edit: stop prototypes/ while ux_guardrails needs auth.

~/.claude/mcp-needs-auth-cache.json is a JSON object keyed by MCP server name.
An unauthenticated server is an entry like
{"timestamp": <epoch ms>, "ttlMs": <ms, often 90000>, "id": <optional>}.
Claude writes the key when a connect needs auth and deletes it after a
successful connect. ttlMs is only how long Claude skips another reconnect
attempt; an expired key stays until sign-in removes it, so a listed key still
means not signed in. A missing file, unreadable JSON, or no ux_guardrails key
allows the write. A file at ~/.claude/guardrails-skip (or GUARDRAILS_SKIP_FILE)
also allows the write: the PM created it to skip this check. This hook does not
call the MCP and does not create that file.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, payload, rel, root, warn

SERVER = "ux_guardrails"
CACHE_ENV = "MCP_NEEDS_AUTH_CACHE"
SKIP_ENV = "GUARDRAILS_SKIP_FILE"
BLOCK_MSG = (
    "Guardrails is not signed in; run /mcp in Claude Code, choose ux_guardrails, "
    "sign in (VPN on), then reconnect or start a new session; prototype work stops until then. "
    "To skip this save check, the PM can create ~/.claude/guardrails-skip and delete it after sign-in."
)


def cache_path() -> str:
    override = os.environ.get(CACHE_ENV)
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".claude", "mcp-needs-auth-cache.json")


def skip_path() -> str:
    override = os.environ.get(SKIP_ENV)
    if override:
        return override
    return os.path.join(os.path.expanduser("~"), ".claude", "guardrails-skip")


def skipped() -> bool:
    """True when the PM's skip file exists. Agents do not create it."""
    try:
        return os.path.isfile(skip_path())
    except Exception:
        return False


def needs_auth(path: str) -> bool:
    """True only when the cache lists ux_guardrails. Fail open otherwise."""
    try:
        import json
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except Exception:
        return False
    return isinstance(data, dict) and SERVER in data


def _under_prototypes(path: str, rroot: str) -> bool:
    if not isinstance(path, str) or not path:
        return False
    if os.path.isabs(path):
        try:
            full = os.path.realpath(path)
            proto = os.path.realpath(os.path.join(rroot, "prototypes"))
            if full == proto or full.startswith(proto + os.sep):
                return True
        except Exception:
            pass
        relative = rel(path)
    else:
        relative = path.replace("\\", "/")
    relative = os.path.normpath(relative).replace("\\", "/")
    return relative == "prototypes" or relative.startswith("prototypes/")


def _paths(tool_input: dict) -> list[str]:
    out = []
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            out.append(value)
    return out


def main() -> None:
    try:
        body = payload()
        paths = _paths(body.get("tool_input") or {})
        live = root()
        if not any(_under_prototypes(path, live) for path in paths):
            sys.exit(0)
        if skipped():
            sys.exit(0)
        if needs_auth(cache_path()):
            block(BLOCK_MSG)
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"require_guardrails_auth_for_prototypes skipped: {exc}")


if __name__ == "__main__":
    main()
