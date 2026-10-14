#!/usr/bin/env python3
"""Parse Claude Code session JSONL transcripts.

Generic reader for ``~/.claude/projects/*/*.jsonl``. ``session_usage.py`` and
``/todo reconcile`` both use it. A later chat-harvest plan can reuse the same
user-turn iterator; keep this module free of workbench-specific policy.

A user turn is a ``type: user`` record that is the PM's own message: not
``isMeta``, not ``isSidechain``, and not a tool result. Each turn carries
``timestamp``, ``session_id`` (the JSONL file stem), and ``entrypoint``.

Surface labels (Claude Code 2.1.299, startup function ``T`` / product map ``Qg``):

- ``cli`` — interactive terminal. Set when ``CLAUDE_CODE_ENTRYPOINT`` is unset
  and the process is interactive.
- ``sdk-cli`` — non-interactive. The same function sets ``sdk-cli`` when the
  process is non-interactive (``claude -p`` and the CLI SDK). If the env var
  was already ``cli``, non-interactive mode rewrites it to ``sdk-cli``.
- ``claude-vscode`` — VS Code / Cursor extension panel. The extension sets
  ``CLAUDE_CODE_ENTRYPOINT=claude-vscode`` before spawn; ``Qg`` maps that to
  the ``claude_code_vscode`` product surface. It is not rewritten to ``sdk-cli``.

Observed on this machine alongside those fields: ``cli`` turns use
``promptSource=typed`` / ``turnOrigin=human``; ``sdk-cli`` turns use
``promptSource=sdk`` / ``turnOrigin=sdk`` / ``permissionMode=dontAsk``;
``claude-vscode`` turns use ``turnOrigin=human``. ``userType`` is ``external``
on all three and does not distinguish them.

Unknown entrypoints are returned unchanged so a new value is not mislabeled.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


# Named surfaces. Anything else is kept as the raw entrypoint string.
SURFACE_BY_ENTRYPOINT = {
    "cli": "terminal",
    "sdk-cli": "headless",
    "claude-vscode": "panel",
}


@dataclass(frozen=True)
class UserTurn:
    """One PM message from a Claude Code session transcript."""

    timestamp: str
    session_id: str
    entrypoint: str
    text: str
    uuid: str
    path: str
    project: str
    cwd: str


def surface_from_entrypoint(entrypoint: str) -> str:
    """Map a transcript ``entrypoint`` to a usage surface label.

    Known values become ``terminal``, ``headless``, or ``panel``. Any other
    non-empty value is returned as-is. Empty stays empty.
    """
    value = (entrypoint or "").strip()
    if not value:
        return ""
    return SURFACE_BY_ENTRYPOINT.get(value, value)


def record_entrypoint(obj: dict) -> str:
    return (obj.get("entrypoint") or "").strip()


def message_text(obj: dict) -> str:
    """Plain text from a transcript record's ``message.content``."""
    msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    content = msg.get("content")
    if content is None:
        content = obj.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def is_tool_result(obj: dict) -> bool:
    if obj.get("toolUseResult") is not None or obj.get("sourceToolAssistantUUID"):
        return True
    msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    content = msg.get("content")
    if isinstance(content, list) and content:
        if all(isinstance(block, dict) and block.get("type") == "tool_result" for block in content):
            return True
    return False


def is_human_turn(obj: dict) -> bool:
    """True for the PM's own user message, not meta, sidechain, or tool output."""
    typ = obj.get("type")
    msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
    role = msg.get("role") or typ
    if typ != "user" and role != "user":
        return False
    if obj.get("isMeta") or obj.get("isSidechain"):
        return False
    if is_tool_result(obj):
        return False
    text = message_text(obj).strip()
    if not text:
        return False
    if text.startswith("<local-command-stdout") or text.startswith("<local-command-stderr"):
        return False
    return True


def iter_records(path: Path) -> Iterator[dict]:
    """Yield JSON objects from one JSONL file. Malformed lines are skipped."""
    try:
        handle = path.open(encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                yield obj


def session_files(
    projects_dirs: list[Path] | None = None,
    *,
    projects_root: Path | None = None,
) -> list[Path]:
    """JSONL session files.

    ``projects_dirs`` are Claude project directories (each holding ``*.jsonl``).
    When omitted, every ``*.jsonl`` under ``~/.claude/projects/`` is returned
    (or under ``projects_root`` when that is passed).
    """
    if projects_dirs:
        found: list[Path] = []
        for directory in projects_dirs:
            directory = Path(directory)
            if directory.is_dir():
                found.extend(sorted(directory.glob("*.jsonl")))
        return found
    root = projects_root or (Path.home() / ".claude" / "projects")
    if not root.is_dir():
        return []
    return sorted(root.glob("*/*.jsonl"))


def iter_user_turns(
    files: list[Path] | None = None,
    *,
    projects_dirs: list[Path] | None = None,
    projects_root: Path | None = None,
) -> Iterator[UserTurn]:
    """Iterate the PM's own messages (user turns only).

    Each item has ``timestamp``, ``session_id``, and ``entrypoint``, plus the
    text and the file it came from so callers can cite evidence.
    """
    if files is None:
        files = session_files(projects_dirs, projects_root=projects_root)
    for path in files:
        project = path.parent.name
        session_id = path.stem
        for obj in iter_records(path):
            if not is_human_turn(obj):
                continue
            yield UserTurn(
                timestamp=(obj.get("timestamp") or ""),
                session_id=(obj.get("sessionId") or session_id),
                entrypoint=record_entrypoint(obj),
                text=message_text(obj),
                uuid=(obj.get("uuid") or ""),
                path=str(path),
                project=project,
                cwd=(obj.get("cwd") or ""),
            )


def index_message_surfaces(
    files: list[Path],
    needed: set[tuple[str, str]] | None = None,
) -> tuple[dict[tuple[str, str], str], dict[str, str]]:
    """Map ``(session_id, message_uuid)`` to a surface label.

    ``session_id`` is the JSONL stem (what ``session_usage`` stores). The
    second dict maps that stem to the session's entrypoint for rows whose
    own record omitted the field. When ``needed`` is set, only those keys
    are stored.
    """
    by_message: dict[tuple[str, str], str] = {}
    by_session: dict[str, str] = {}
    for path in files:
        session_id = path.stem
        for obj in iter_records(path):
            entrypoint = record_entrypoint(obj)
            if entrypoint and session_id not in by_session:
                by_session[session_id] = entrypoint
            uuid = obj.get("uuid") or ""
            if not uuid or not entrypoint:
                continue
            key = (session_id, uuid)
            if needed is not None and key not in needed:
                continue
            by_message[key] = surface_from_entrypoint(entrypoint)
    return by_message, by_session
