---
description: Pick up an earlier session's work by matching its goal (session memory)
argument-hint: <words from the earlier session's goal>
---

Find the earlier session to pick up.

1. Run `python3 SESSION_MEMORY_DIR/pickup.py --cwd "$PWD" $ARGUMENTS` and read its output: matching sessions, newest first, with goal, last activity and register path.
2. If there is no match, say so in one line and stop. If there are several, ask which one in one line.
3. For the chosen session: read its register, recap Where it stands in three or four lines, and list its Constraints, Corrections and Don't retry entries so the user can drop stale ones.
4. Carry the kept entries forward by running `python3 SESSION_MEMORY_DIR/pickup.py --cwd "$PWD" --adopt <session-id> --keep <entry ids>`.
