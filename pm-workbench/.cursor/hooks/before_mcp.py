#!/usr/bin/env python3
"""beforeMCPExecution: ask the PM before Atlassian/Slack writes; allow reads."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    emit,
    is_atlassian_read,
    is_atlassian_write,
    is_slack_server,
    is_slack_write,
    log_decision,
    project_root,
    read_stdin_json,
    summarize_mcp_write,
)


def main() -> int:
    payload = read_stdin_json()
    root = project_root(payload)

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input")
    server = payload.get("mcp_server_name") or ""

    # Atlassian writes → ask
    if is_atlassian_write(tool_name):
        summary = summarize_mcp_write(tool_name, tool_input)
        msg = (
            "Approval needed before writing to Atlassian (Jira/Confluence). "
            f"About to run: {summary}"
        )
        log_decision(
            root,
            {
                "hook": "beforeMCPExecution",
                "decision": "ask",
                "tool_name": tool_name,
                "mcp_server_name": server,
                "summary": summary,
            },
        )
        emit(
            {
                "permission": "ask",
                "user_message": msg,
                "agent_message": "Waiting for the PM to approve this Atlassian write.",
            }
        )
        return 0

    # Explicit Atlassian reads → allow
    if is_atlassian_read(tool_name):
        log_decision(
            root,
            {
                "hook": "beforeMCPExecution",
                "decision": "allow",
                "tool_name": tool_name,
                "mcp_server_name": server,
                "reason": "atlassian read",
            },
        )
        emit({"permission": "allow"})
        return 0

    # Slack writes → ask
    if is_slack_server(payload) and is_slack_write(tool_name):
        summary = summarize_mcp_write(tool_name, tool_input)
        msg = (
            "Approval needed before writing to Slack. "
            f"About to run: {summary}"
        )
        log_decision(
            root,
            {
                "hook": "beforeMCPExecution",
                "decision": "ask",
                "tool_name": tool_name,
                "mcp_server_name": server,
                "summary": summary,
            },
        )
        emit(
            {
                "permission": "ask",
                "user_message": msg,
                "agent_message": "Waiting for the PM to approve this Slack write.",
            }
        )
        return 0

    # Everything else (other MCP, Slack reads) → allow
    log_decision(
        root,
        {
            "hook": "beforeMCPExecution",
            "decision": "allow",
            "tool_name": tool_name,
            "mcp_server_name": server,
            "reason": "not a gated write",
        },
    )
    emit({"permission": "allow"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
