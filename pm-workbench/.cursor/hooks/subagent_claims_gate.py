#!/usr/bin/env python3
"""subagentStop: send a worker back when its result carries unsourced claims or
failing files; file the worker's failing files under the parent conversation.

Payload (Cursor agent-exec): conversation_id, subagent_id, subagent_type, status,
summary (worker's last assistant message), parent_conversation_id, modified_files,
loop_count, task, description. `followup_message` continues the subagent; Cursor
only applies it when status == "completed".
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    add_relay_failure,
    claims_followup_text,
    load_status,
    claims_verdict,
    emit,
    log_decision,
    normalize_rel,
    project_root,
    read_stdin_json,
    refile_for_parent,
)
from dispatch_inject import DISPATCH_BLOCK_REF, MARKER, build_block  # noqa: E402

# Must match hooks.json loop_limit
LOOP_LIMIT = 2


def worker_transcript_path(payload: dict) -> tuple[str | None, str]:
    """IDE payloads send agent_transcript_path=null; derive the worker transcript
    from the parent transcript_path + child_conversation_id:
    <agent-transcripts>/<parent>/<parent>.jsonl -> <agent-transcripts>/<parent>/subagents/<child>.jsonl
    """
    direct = payload.get("agent_transcript_path")
    if direct:
        return direct, "agent_transcript_path"
    parent_tx = payload.get("transcript_path")
    child = payload.get("child_conversation_id")
    if parent_tx and child:
        return str(Path(parent_tx).parent / "subagents" / f"{child}.jsonl"), "derived_subagent_transcript"
    # Live IDE payloads (2026-11-02) send transcript_path=null too; use the
    # on-disk layout ~/.cursor/projects/<slug>/agent-transcripts/<parent>/subagents/<child>.jsonl
    parent = payload.get("parent_conversation_id") or payload.get("conversation_id")
    if parent and child:
        hits = sorted(
            (Path.home() / ".cursor" / "projects").glob(
                f"*/agent-transcripts/{parent}/subagents/{child}.jsonl"
            )
        )
        if hits:
            return str(hits[0]), "globbed_subagent_transcript"
    return None, "none"


def last_assistant_text(path: str | None, wait_s: float = 6.0) -> str:
    """The IDE payload has no `summary`; read the worker's final assistant text
    from agent_transcript_path (JSONL of {role, message: {content: [...]}}).
    The transcript can land on disk just after the hook fires, so poll briefly."""
    if not path:
        return ""
    deadline = time.monotonic() + wait_s
    while True:
        text = _last_text_now(path)
        if text or time.monotonic() >= deadline:
            return text
        time.sleep(0.5)


def _last_text_now(path: str) -> str:
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("role") != "assistant":
            continue
        content = (row.get("message") or {}).get("content") or []
        texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        if any(t.strip() for t in texts):
            return "\n".join(texts)
    return ""


def _line_count(path: str | None) -> int | None:
    try:
        return len(Path(path).read_text(encoding="utf-8").splitlines()) if path else None
    except OSError:
        return None


def main() -> int:
    payload = read_stdin_json()
    root = project_root(payload)
    status = payload.get("status") or ""
    loop_count = int(payload.get("loop_count") or 0)
    summary = payload.get("summary") or ""
    summary_source = "summary"
    worker_transcript, transcript_how = worker_transcript_path(payload)
    lines_at_hook = _line_count(worker_transcript)
    if not summary:
        summary = last_assistant_text(worker_transcript)
        summary_source = transcript_how if summary else "none"
    parent_id = payload.get("parent_conversation_id") or None
    child_id = payload.get("child_conversation_id") or None
    modified = [
        r for r in (normalize_rel(m, root) for m in (payload.get("modified_files") or [])) if r
    ]
    # The IDE never sends modified_files; afterFileEdit inside a worker records
    # under the worker's own conversation id, which is child_conversation_id here.
    if child_id and child_id != parent_id:
        child_arts = ((load_status(root).get("sessions") or {}).get(child_id) or {}).get("artifacts") or {}
        modified += [p for p in child_arts if p not in modified]

    failing_files = refile_for_parent(root, parent_id, modified)
    verdict = claims_verdict(summary, root)
    if not verdict["ok"] and status == "completed":
        # The IDE drops subagentStop followup_message, so the coordinator's own
        # stop hook is the one that can send work back: file it there.
        add_relay_failure(
            root,
            parent_id or "unknown",
            {
                "source": f"worker {child_id or payload.get('subagent_id')}",
                "found": verdict["found"],
                "table": verdict["table"],
                "excerpt": summary[:400],
            },
        )

    base = {
        "hook": "subagentStop",
        "status": status,
        "loop_count": loop_count,
        "subagent_id": payload.get("subagent_id"),
        "subagent_type": payload.get("subagent_type"),
        "conversation_id": payload.get("conversation_id"),
        "parent_conversation_id": parent_id,
        "refiled_under": parent_id or "pending",
        "modified_files": modified[:20],
        "failing_files": failing_files,
        "claims_ok": verdict["ok"],
        "claims_found": verdict["found"],
        "claim_table": verdict["table"],
        "summary_chars": len(summary),
        "summary_source": summary_source,
        "worker_transcript": worker_transcript,
        "parent_transcript_path": payload.get("transcript_path"),
        "transcript_lines_at_hook": lines_at_hook,
        "transcript_lines_after_read": _line_count(worker_transcript),
        "dispatch_block_in_task": MARKER in (payload.get("task") or ""),
        "child_conversation_id": payload.get("child_conversation_id"),
        "payload_keys": sorted(payload.keys()),
    }

    if status != "completed":
        log_decision(root, {**base, "decision": "allow", "reason": f"status={status}"})
        emit({})
        return 0
    if verdict["ok"] and not failing_files:
        log_decision(root, {**base, "decision": "allow", "reason": "claims sourced or none; files ok"})
        emit({})
        return 0
    if loop_count >= LOOP_LIMIT:
        log_decision(root, {**base, "decision": "allow", "reason": "loop_limit reached; parent stop gate holds file failures"})
        emit({})
        return 0

    parts = []
    if not verdict["ok"]:
        parts.append(claims_followup_text(verdict, root))
    if failing_files:
        parts.append(
            "These files you modified are failing the workbench gates (see "
            "`state/hooks/gate-status.json`): "
            + ", ".join(f"`{p}`" for p in failing_files)
            + ". Fix them (design check, number ledger, or claim table) before returning."
        )
    if loop_count == LOOP_LIMIT - 1:
        parts.append(
            "Last attempt: if you still cannot source a claim, say so plainly in your result "
            "and mark it `unverified` in the claim table. Do not present it as fact."
        )
    task = payload.get("task") or ""
    if MARKER not in task and DISPATCH_BLOCK_REF not in task:
        # preToolUse does not reach Tasks dispatched via CallDynamicTool, so the
        # worker may never have seen the block; deliver it with the send-back.
        parts.append("The workbench rules you were dispatched without:\n" + build_block(root, task))
    followup = "\n\n".join(parts)
    log_decision(root, {**base, "decision": "followup", "followup_preview": followup[:300]})
    emit({"followup_message": followup})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
