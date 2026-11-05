#!/usr/bin/env python3
"""UserPromptSubmit hook: stale-session notice, related-work detector, reading reminder, reading-tally reset.

One script so two hooks never race on the same prompt. Notice-first: nothing here blocks or erases a
prompt. The stale-session check saves a "Where it stands" snapshot and tells the user, in one line, that a
fresh chat can pick the work up. `!force` at the start of a prompt suppresses the notice (logged).
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

REMINDER = (
    "Session memory: send reading-heavy fact-finding (long documents, many sources, web research) to the "
    "session-reader subagent, or to the project's own heavy-read agent where one exists, and work from its cited "
    "answer. Exception: judgment work (strategy, vision, roadmap, narrative, the partner skill, \"help me think\") "
    "reads its chosen sources in full in this conversation; do not delegate that reading."
)


def tally_path(payload):
    return os.path.join(c.project_dir(payload), f"{payload['session_id']}.reading.json")


def reset_tally(payload):
    path = tally_path(payload)
    try:
        state = json.load(open(path, encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    state.update({"tokens": 0, "sources": [], "noticed": False, "logged": False})
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def stale_notice(payload, rows, prompt):
    if prompt.lstrip().startswith("!force"):
        c.log_event(payload, "guard-override")
        return None
    stamp, tokens = c.last_usage(rows)
    when = c.parse_ts(stamp)
    if not when:
        return None
    idle = (datetime.datetime.now(datetime.timezone.utc) - when.astimezone(datetime.timezone.utc)).total_seconds() / 60
    if idle < c.env_int("SESSION_MEMORY_IDLE_MINUTES", 60) or tokens < c.env_int("SESSION_MEMORY_MIN_TOKENS", 80000):
        return None
    path = c.register_path(payload)
    turns = c.exchanges(rows)[-10:]
    text = c.ask_model(c.instructions() + "\n\n# Task: snapshot\nWrite a 'Where it stands' snapshot (3-5 lines) "
                       "from these exchanges.\n\n" + "\n\n".join(f"USER: {u[:1500]}\nASSISTANT: {a[:1500]}" for u, a, _ in turns)
                       + '\n\nReply with JSON only: {"ops": [{"op": "add", "section": "Where it stands", "text": "..."}]}')
    data = c.parse_json(text)
    saved = False
    if data:
        with c.locked(path, wait=10) as got:
            if got:
                entries = c.load_entries(path)
                c.append_entries(path, c.apply_ops(entries, data.get("ops"), len(c.exchanges(rows))))
                saved = True
    c.update_index(payload, held_prompt=prompt[:4000])
    c.log_event(payload, "guard-notice", idle_minutes=int(idle), context_tokens=tokens, snapshot=saved)
    hours = f"{idle / 60:.1f} h" if idle >= 90 else f"{int(idle)} min"
    return (f"This chat was idle {hours} and holds about {tokens // 1000}k tokens, so this prompt re-reads all of it "
            f"at full price. {'Where it stands is saved; ' if saved else ''}a new chat will offer to pick this work up. "
            "Start the next prompt with !force to skip this notice.")


def detect(payload, prompt):
    index = c.read_index(payload)
    cutoff = datetime.datetime.now() - datetime.timedelta(days=14)
    candidates = []
    for sid, rec in index.items():
        when = c.parse_ts(rec.get("last"))
        if sid != payload["session_id"] and rec.get("goal") and when and when.replace(tzinfo=None) >= cutoff:
            candidates.append((rec.get("last"), sid, rec))
    candidates = sorted(candidates, reverse=True)[:8]
    if not candidates:
        return None
    lines = []
    for _, sid, rec in candidates:
        active = c.active_entries(c.load_entries(c.register_path(payload, sid)))
        decisions = [e["text"][:200] for e in active if e["section"] == "Decisions"][-3:]
        lines.append(f"- {sid}: goal={rec['goal'][:200]!r}; last={rec.get('last')}; decisions={decisions}")
    reply = c.ask_model("Does this new prompt continue one of these earlier sessions? Prefer none when in doubt.\n\n"
                        f"PROMPT: {prompt[:2000]}\n\nSESSIONS:\n" + "\n".join(lines)
                        + '\n\nReply with JSON only: {"session": "<id>"} or {"session": "none"}', timeout=15)
    data = c.parse_json(reply) or {}
    match = data.get("session")
    if match not in {sid for _, sid, _ in candidates}:
        c.log_event(payload, "detector", match=None)
        return None
    c.update_index(payload, offered=match)
    c.log_event(payload, "detector", match=match)
    reg = c.register_path(payload, match)
    return (f"This prompt may continue earlier session {match} (goal: {index[match]['goal'][:200]}). Before anything "
            "else, ask the user in one line whether to pick that work up. If yes: read the register at "
            f"{reg}, recap Where it stands in three or four lines, list its Constraints, Corrections and Don't retry "
            "entries so the user can drop stale ones, and carry the kept ones forward. If no: ignore this note.")


def main():
    payload = c.read_payload()
    if payload is None:
        return 0
    prompt = payload.get("prompt") or ""
    reset_tally(payload)
    rows = c.transcript_entries(payload.get("transcript_path"))
    parts, user_line = [REMINDER], None
    first = not any(r.get("type") == "assistant" for r in rows)
    if first and len(prompt) >= 30 and not c.read_index(payload).get(payload["session_id"], {}).get("offered"):
        note = detect(payload, prompt)
        if note:
            parts.insert(0, note)
    elif not first:
        notice = stale_notice(payload, rows, prompt)
        if notice:
            user_line = notice
            parts.insert(0, "Tell the user this in one line, then answer their prompt: " + notice)
    c.emit_context("UserPromptSubmit", "\n\n".join(parts), user_line)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
