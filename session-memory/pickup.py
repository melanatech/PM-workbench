#!/usr/bin/env python3
"""Helper for /pickup: find an earlier session by goal words, or copy kept entries into the current session.

  python3 pickup.py --cwd "$PWD" words from the goal
  python3 pickup.py --cwd "$PWD" --adopt <old-session-id> --keep e3 e7 [--session <current-id>]

The current session id comes from --session, else the newest register in this project.
"""
import argparse
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks"))
import common as c  # noqa: E402


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
        words = [w.lower() for w in args.words]
        hits = sorted(((rec.get("last", ""), sid, rec) for sid, rec in index.items()
                       if rec.get("goal") and all(w in rec["goal"].lower() for w in words)), reverse=True)
        for last, sid, rec in hits[:8]:
            print(f"{sid}\tlast={last}\tgoal={rec['goal'][:160]}\tregister={c.register_path(payload, sid)}")
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
