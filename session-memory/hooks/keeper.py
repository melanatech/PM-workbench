#!/usr/bin/env python3
"""Stop hook: record what the user decided, constrained, corrected or rejected in this exchange.

Returns at once after starting a detached worker (`keeper.py --worker <job.json>`). The worker reads only
the latest exchange, asks the headless model for register operations, and appends them under a lock.
Every 10th capture it audits active entries against the user's last 20 prompts; past ~1,500 active words
it consolidates. Fails open everywhere.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

AUDIT_EVERY = 10
WORD_CAP = 1500


def start(payload):
    fd, job = tempfile.mkstemp(prefix="sm-job-", suffix=".json", dir=c.project_dir(payload))
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    if os.environ.get("SESSION_MEMORY_SYNC") == "1":
        return worker(job)
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "--worker", job],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True, env={**os.environ, "SESSION_MEMORY_INTERNAL": "0"})


def capture_prompt(exchange, active):
    user, reply, errors = exchange
    correction = bool(c.CORRECTION_WORDS.search(user))
    return (c.instructions() + "\n\n# Task: capture\n"
            + ("The user's message contains a correction signal: check EVERY active entry for conflict, even if "
               "worded differently; the newer statement wins (supersede).\n" if correction else "")
            + "\n## Active entries\n" + (c.render(active) or "(none)")
            + f"\n\n## Latest exchange\nUSER: {user[:4000]}\n\nASSISTANT: {reply[:3000]}"
            + (f"\n\nTOOL ERRORS: {errors[:500]}" if errors else "")
            + '\n\nReply with JSON only: {"ops": [...]}')


def audit_prompt(prompts, active):
    return (c.instructions() + "\n\n# Task: audit\nCompare the active entries with the user's last prompts. "
            "Supersede or drop any entry the user has since contradicted or moved away from, even if never stated "
            "as a correction. Use {\"op\": \"drop\", \"ids\": [...]} or a supersede op. Change nothing that still holds."
            "\n\n## Active entries\n" + c.render(active)
            + "\n\n## User's last prompts (oldest first)\n" + "\n".join(f"- {p[:600]}" for p in prompts)
            + '\n\nReply with JSON only: {"ops": [...]}')


def consolidate_prompt(active):
    return (c.instructions() + "\n\n# Task: consolidate\nThe active entries are too long. Merge overlapping entries "
            "with supersede ops (list every merged id). Check for contradictions while merging; the newer wins. "
            "Keep the user's wording.\n\n## Active entries\n" + c.render(active)
            + '\n\nReply with JSON only: {"ops": [...]}')


def run_ops(path, prompt, turn, timeout=60):
    data = c.parse_json(c.ask_model(prompt, timeout=timeout))
    if data is None:
        return None
    with c.locked(path, wait=20) as got:
        if not got:
            return None
        entries = c.load_entries(path)
        new = c.apply_ops(entries, data.get("ops"), turn)
        c.append_entries(path, new)
    return new


def worker(job):
    try:
        payload = json.load(open(job, encoding="utf-8"))
    except (OSError, ValueError):
        return
    finally:
        try:
            os.remove(job)
        except OSError:
            pass
    rows = c.transcript_entries(payload.get("transcript_path"))
    turns = c.exchanges(rows)
    if not turns:
        return
    user = turns[-1][0]
    path = c.register_path(payload)
    if len(user.strip()) < 20 and not c.CORRECTION_WORDS.search(user):
        c.log_event(payload, "capture-skipped", reason="short prompt")
        return
    active = c.active_entries(c.load_entries(path))
    new = run_ops(path, capture_prompt(turns[-1], active), len(turns))
    if new is None:
        c.log_event(payload, "capture-failed", reason="no model reply (cap, timeout or error)")
        return
    goal = next((e["text"] for e in reversed(c.active_entries(c.load_entries(path))) if e["section"] == "Goal"), None)
    rec = c.update_index(payload, captures_add=1, **({"goal": goal} if goal else {})) or {}
    c.log_event(payload, "capture", added=len(new), superseded=sum(len(e["supersedes"]) for e in new))
    if rec.get("captures", 0) % AUDIT_EVERY == 0:
        audit(payload, turns)
    active = c.active_entries(c.load_entries(path))
    if c.word_count(active) > WORD_CAP:
        merged = run_ops(path, consolidate_prompt(active), len(turns))
        c.log_event(payload, "consolidate", ok=merged is not None)


def audit(payload, turns=None):
    path = c.register_path(payload)
    active = c.active_entries(c.load_entries(path))
    if not active:
        return
    if turns is None:
        turns = c.exchanges(c.transcript_entries(payload.get("transcript_path")))
    new = run_ops(path, audit_prompt([t[0] for t in turns[-20:]], active), len(turns))
    c.log_event(payload, "audit", changed=len(new or []), ok=new is not None)


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        worker(sys.argv[2])
        return 0
    payload = c.read_payload()
    if payload is None or payload.get("stop_hook_active"):
        return 0
    start(payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
