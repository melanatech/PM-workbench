#!/usr/bin/env python3
"""PostToolUse hook on Read, Grep, Glob, WebFetch, WebSearch and Skill: the reading budget, as a notice.

Tallies what lands in the main conversation since the last user prompt (about 4 characters per token).
Past 25,000 tokens or 4 distinct sources in one turn it adds one line of context suggesting the rest go to a
reader subagent. It never blocks. It is off for the rest of the session once the partner skill is used
(judgment work reads in full in the main conversation), and it skips calls marked as a subagent's.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

READ_TOOLS = {"Read", "Grep", "Glob", "WebFetch", "WebSearch"}
SUBAGENT_KEYS = ("agent_id", "agent_type", "subagent_type", "parent_tool_use_id")


def is_partner(payload):
    name, ti = payload.get("tool_name"), payload.get("tool_input") or {}
    if name == "Skill":
        return "partner" in json.dumps(ti).lower()
    return name == "Read" and str(ti.get("file_path", "")).replace("\\", "/").endswith("skills/partner/SKILL.md")


def source_of(payload):
    ti = payload.get("tool_input") or {}
    return str(ti.get("file_path") or ti.get("url") or ti.get("query") or ti.get("pattern") or ti.get("path") or "")


def main():
    payload = c.read_payload()
    if payload is None or any(payload.get(k) for k in SUBAGENT_KEYS):
        return 0
    path = os.path.join(c.project_dir(payload), f"{payload['session_id']}.reading.json")
    try:
        state = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        state = {"tokens": 0, "sources": [], "noticed": False}
    if is_partner(payload):
        state["partner"] = True
    if payload.get("tool_name") in READ_TOOLS:
        state["tokens"] = state.get("tokens", 0) + len(json.dumps(payload.get("tool_response") or "")) // 4
        src = source_of(payload)
        if src and src not in state.setdefault("sources", []):
            state["sources"].append(src)
    over = state.get("tokens", 0) > c.env_int("SESSION_MEMORY_READ_TOKENS", 25000) or \
        len(state.get("sources", [])) > c.env_int("SESSION_MEMORY_READ_SOURCES", 4)
    notify = over and not state.get("noticed") and not state.get("partner")
    if notify:
        state["noticed"] = True
    if over and not state.get("logged"):
        state["logged"] = True
        c.log_event(payload, "reading-over", tokens=state["tokens"], sources=len(state["sources"]),
                    partner=bool(state.get("partner")), noticed=notify)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)
    if notify:
        c.emit_context("PostToolUse", f"Reading this turn: about {state['tokens'] // 1000}k tokens from "
                       f"{len(state['sources'])} sources. If this is fact-finding, send the rest to the session-reader "
                       "subagent (or the project's heavy-read agent) and work from its cited answer. If it is judgment "
                       "work that must read in full here, carry on.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
