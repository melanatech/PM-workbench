#!/usr/bin/env python3
"""stop: block claiming done when shared artifacts fail design/number gates, an
outputs .md fails the claim check, or an earlier reply relayed unsourced claims."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    emit,
    gate_failures_for_session,
    log_decision,
    pop_relay_failures,
    project_root,
    read_stdin_json,
)

# Must match hooks.json loop_limit
LOOP_LIMIT = 3


def main() -> int:
    payload = read_stdin_json()
    root = project_root(payload)

    status = payload.get("status") or "completed"
    loop_count = int(payload.get("loop_count") or 0)
    session_id = (
        payload.get("conversation_id")
        or payload.get("session_id")
        or None
    )

    # Only enforce on completed agent turns (not aborted/error)
    if status != "completed":
        log_decision(
            root,
            {
                "hook": "stop",
                "decision": "allow",
                "reason": f"status={status}",
                "loop_count": loop_count,
                "session_id": session_id,
            },
        )
        emit({})
        return 0

    failures = gate_failures_for_session(root, session_id)
    relays = pop_relay_failures(root, session_id)
    if not failures and not relays:
        log_decision(
            root,
            {
                "hook": "stop",
                "decision": "allow",
                "reason": "no failing shared artifacts",
                "loop_count": loop_count,
                "session_id": session_id,
            },
        )
        emit({})
        return 0

    lines = []
    for f in failures:
        path = f.get("path")
        reason = f.get("fail_reason")
        design = f.get("design")
        number = f.get("number")
        claims = f.get("claims", "n/a")
        msgs = "; ".join(f.get("messages") or []) or "(no detail)"
        lines.append(
            f"- `{path}`: {reason}; design={design}, number={number}, claims={claims}; {msgs}"
        )
    for r in relays:
        found = r.get("found") or {}
        quoted = "; ".join(
            f'"{s}"' for s in (found.get("absence", []) + found.get("people", []) + found.get("wrong_pm", []))
        )
        who = (
            f"{r['source']} returned" if r.get("source") else "an earlier reply in this chat stated"
        )
        lines.append(f"- {who} ({r.get('ts')}) {quoted} with {r.get('table')}")
    detail = "\n".join(lines)
    relay_step = (
        "3) Claims in a reply or `.md` deliverable: for every absence claim (no ticket, no PRD, "
        "empty, stale, needs a PRD) and every named person or assignee, check the source yourself "
        "(Jira fetch/JQL, Confluence page + version, or file:line; for absence, the artifact's own "
        "links and Sources section). Then correct the claim to the PM in this reply or add a "
        "`## Claim table` (| Claim | Source | Checked how |). A worker's word is not a source.\n"
    )

    # loop_count = how many follow-ups already fired. With loop_limit=3,
    # Cursor accepts follow-ups while loop_count is 0,1,2. On the last allowed
    # follow-up (loop_count == LOOP_LIMIT - 1) tell the agent to report plainly.
    if loop_count >= LOOP_LIMIT:
        log_decision(
            root,
            {
                "hook": "stop",
                "decision": "allow",
                "reason": "loop_limit reached; no further followup",
                "loop_count": loop_count,
                "session_id": session_id,
                "failures": [f.get("path") for f in failures],
            },
        )
        emit({})
        return 0

    last_loop = loop_count >= (LOOP_LIMIT - 1)

    if last_loop:
        followup = (
            "GATE STILL FAILING after repeated fix attempts. "
            "Do NOT tell the PM the artifact is ready. "
            "Report the failing check(s) to the PM plainly, with paths and messages:\n"
            f"{detail}"
        )
    else:
        followup = (
            "Shared-artifact gate failed. Do NOT tell the PM it is ready. "
            "Run the checks, fix the artifact, then continue:\n"
            "1) HTML design: `python3 scripts/check_design_preserved.py <path> --git HEAD` "
            "when git has the file; otherwise "
            "`--before state/hooks/design-baselines/<same-rel-path>`. "
            "design=skipped is a FAIL. Do not redesign unless the PM asked. "
            "Only if the PM explicitly accepts a redesign: "
            "`python3 scripts/accept_design_baseline.py <path>`.\n"
            "2) Numbers: `python3 scripts/check_number_consistency.py --ledger "
            "<artifact-stem>-number-ledger.md <artifact>` "
            "(ledger sits beside the artifact unless declared in "
            "`.cursor/hooks/shared-artifacts.json`)\n"
            f"{relay_step}"
            "Re-edit the artifact only after its checks pass. Failing items:\n"
            f"{detail}"
        )

    log_decision(
        root,
        {
            "hook": "stop",
            "decision": "followup",
            "loop_count": loop_count,
            "last_loop": last_loop,
            "session_id": session_id,
            "failures": [f.get("path") for f in failures],
            "relay_failures": len(relays),
        },
    )
    emit({"followup_message": followup})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
