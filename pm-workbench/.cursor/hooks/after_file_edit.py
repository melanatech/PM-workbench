#!/usr/bin/env python3
"""afterFileEdit: run design + number gates on shared artifacts and the claim check
on outputs .md files; record status."""
from __future__ import annotations

import sys
from pathlib import Path

# Allow importing _common from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    claims_verdict,
    emit,
    is_claim_checked,
    is_shared_artifact,
    load_config,
    log_decision,
    project_root,
    read_stdin_json,
    record_gate,
    rel_to_root,
    run_design_check,
    run_number_check,
)


def main() -> int:
    payload = read_stdin_json()
    root = project_root(payload)
    config = load_config(root)

    file_path = payload.get("file_path") or ""
    if not file_path:
        log_decision(
            root,
            {
                "hook": "afterFileEdit",
                "decision": "skip",
                "reason": "no file_path",
            },
        )
        emit({})
        return 0

    path = Path(file_path)
    rel = rel_to_root(path, root)
    shared = is_shared_artifact(rel, config)
    claim_scoped = is_claim_checked(rel, config)

    if not shared and not claim_scoped:
        log_decision(
            root,
            {
                "hook": "afterFileEdit",
                "decision": "skip",
                "path": rel,
                "reason": "not a shared artifact or claim-checked md",
                "conversation_id": payload.get("conversation_id"),
                "payload_keys": sorted(payload.keys()),
            },
        )
        emit({})
        return 0

    if shared:
        design_status, design_msg = run_design_check(root, path)
        number_status, number_msg = run_number_check(root, path, config)
    else:
        design_status, design_msg = "n/a", "plain md"
        number_status, number_msg = "n/a", "plain md (number gate applies to shared artifacts only)"
    claims_status = "n/a"
    claims_msg = ""
    if claim_scoped:
        try:
            verdict = claims_verdict(
                path.read_text(encoding="utf-8", errors="replace"), root, mode="file"
            )
        except OSError as exc:
            verdict = {"ok": False, "flagged": True, "found": {}, "table": f"unreadable: {exc}"}
        if verdict["flagged"] or not verdict["ok"]:
            claims_status = "pass" if verdict["ok"] else "fail"
            claims_msg = f"{verdict['table']}; found {verdict['found']}"
    messages = []
    if claims_status == "fail":
        messages.append(f"claims: {claims_msg}")
    if design_status == "fail":
        messages.append(f"design: {design_msg}")
    elif design_status not in {"n/a"}:
        messages.append(f"design={design_status}: {design_msg}")
    if number_status == "fail":
        messages.append(f"number: {number_msg}")
    elif number_status not in {"n/a"}:
        messages.append(f"number={number_status}: {number_msg}")

    rec = record_gate(
        root, payload, path, design_status, number_status, messages, claims=claims_status
    )

    ok = rec.get("ok")
    log_decision(
        root,
        {
            "hook": "afterFileEdit",
            "decision": "pass" if ok else "fail",
            "path": rel,
            "design": design_status,
            "number": number_status,
            "claims": claims_status,
            "ok": ok,
            "messages": messages,
            "conversation_id": payload.get("conversation_id"),
            "payload_keys": sorted(payload.keys()),
        },
    )

    # afterFileEdit has no documented agent-facing output fields; status is for stop.
    emit({})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
