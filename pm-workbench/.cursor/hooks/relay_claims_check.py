#!/usr/bin/env python3
"""afterAgentResponse: record replies that carry unsourced absence/person claims.

afterAgentResponse is observe-only (Cursor returns an empty response), and the
stop hook does not fire on turns started by a subagent-completion notice. So a
flagged reply is recorded under its conversation; the next stop that fires in
that conversation sends the agent back to correct it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    add_relay_failure,
    claims_verdict,
    emit,
    log_decision,
    project_root,
    read_stdin_json,
)


def main() -> int:
    payload = read_stdin_json()
    root = project_root(payload)
    text = payload.get("text") or ""
    session_id = payload.get("conversation_id") or payload.get("session_id") or ""
    verdict = claims_verdict(text, root)
    row = {
        "hook": "afterAgentResponse",
        "conversation_id": session_id,
        "generation_id": payload.get("generation_id"),
        "text_chars": len(text),
        "claims_ok": verdict["ok"],
        "payload_keys": sorted(payload.keys()),
    }
    if verdict["ok"]:
        log_decision(root, {**row, "decision": "pass" if verdict["flagged"] else "skip"})
    else:
        add_relay_failure(
            root,
            session_id,
            {
                "generation_id": payload.get("generation_id"),
                "found": verdict["found"],
                "table": verdict["table"],
                "excerpt": text[:400],
            },
        )
        log_decision(
            root,
            {**row, "decision": "record", "claims_found": verdict["found"], "claim_table": verdict["table"]},
        )
    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
