#!/usr/bin/env python3
"""Helper for /pickup: find an earlier session by words, or copy kept entries into the current session.

  python3 pickup.py --cwd "$PWD" words from the work
  python3 pickup.py --cwd "$PWD" --adopt <old-session-id> --keep e3 e7 [--session <current-id>]

Search covers the stored goal and every register line, including a goal a later to-do replaced.
One or two words must all match. Three or more match when at least half of them appear.
The current session id comes from --session, else the newest register in this project.
--cwd can be any folder inside the project: registers are keyed by the project (CLAUDE_PROJECT_DIR,
else the nearest parent holding .claude), not by the folder a session happened to be in.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks"))
import common as c  # noqa: E402

STOP = {"the", "a", "an", "of", "to", "and", "for", "in", "on", "is", "it", "its", "how", "this", "that",
        "with", "from", "be", "or", "at", "by", "as"}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--cwd", default=os.getcwd())
    parser.add_argument("--adopt")
    parser.add_argument("--keep", nargs="*", default=[])
    parser.add_argument("--session")
    parser.add_argument("words", nargs="*")
    args = parser.parse_args(argv)
    payload = {"cwd": args.cwd, "session_id": args.session or "unknown"}
    index = c.read_index(payload)
    if not args.adopt:
        words = [w.lower() for w in args.words if w.lower() not in STOP]
        if not words:
            words = [w.lower() for w in args.words]
        need = len(words) if len(words) <= 2 else (len(words) + 1) // 2
        hits = []
        for sid, rec in index.items():
            blob = "\n".join([rec.get("goal") or "", *(rec.get("goals") or [])] +
                             [e.get("text") or "" for e in c.load_entries(c.register_path(payload, sid))]).lower()
            matched = [w for w in words if w in blob]
            if words and len(matched) >= need:
                hits.append((len(matched), rec.get("last", ""), sid, rec, matched))
        for _score, last, sid, rec, matched in sorted(hits, reverse=True)[:8]:
            print(f"{sid}\tlast={last}\tmatched={','.join(matched)}\tgoal={(rec.get('goal') or '')[:160]}"
                  f"\tregister={c.register_path(payload, sid)}")
        if not hits:
            print("no matching session")
        return 0
    current = args.session
    if not current:
        regs = sorted(glob.glob(os.path.join(c.project_dir(payload), "*.jsonl")), key=os.path.getmtime)
        regs = [r for r in regs if os.path.basename(r)[:-6] != args.adopt]
        if not regs:
            print("no current session register; pass --session", file=sys.stderr)
            return 2
        current = os.path.basename(regs[-1])[:-6]
    old = {e["id"]: e for e in c.active_entries(c.load_entries(c.register_path(payload, args.adopt)))}
    path = c.register_path(payload, current)
    with c.locked(path, wait=10):
        entries = c.load_entries(path)
        new = []
        for eid in args.keep:
            if eid in old:
                new.append({**old[eid], "id": c.next_id(entries + new), "supersedes": [],
                            "source": f"{args.adopt}:{eid}", "date": c.now_iso()})
        c.append_entries(path, new)
    c.update_index({**payload, "session_id": current}, picked_from=args.adopt)
    print(f"carried {len(new)} entries from {args.adopt} into {current}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
