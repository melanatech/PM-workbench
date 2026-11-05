#!/usr/bin/env python3
"""SessionStart hook.

source=compact: wait up to 10 s for the keeper's lock, then print the preface and this session's active
entries, so decisions, constraints and corrections survive the summary. Superseded and dropped entries are
never printed.
source=startup: if a weekly review report is waiting (and not yet offered), offer it in one line.
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as c  # noqa: E402

PREFACE = (
    "The conversation was just compacted. These decisions, constraints and corrections from earlier in this "
    "session still apply and take precedence over the summary. If one conflicts with something said more "
    "recently, the more recent statement wins; point out the conflict in one line. "
    "Precedence: within this session, the newer statement wins. For a durable fact the project keeps in its own "
    "memory file (for example reference/context/pm-brain.md), the newer of the two wins: if an entry below is "
    "newer, follow the project's own rule for saving a PM correction (CLAUDE.md) so the file agrees; if the file "
    "was updated after the entry, the file wins. Session memory never edits that file itself."
)


def restore(payload):
    path = c.register_path(payload)
    with c.locked(path, wait=10):
        active = c.active_entries(c.load_entries(path))
    if not active:
        return
    c.log_event(payload, "restore", entries=len(active))
    c.emit_context("SessionStart", PREFACE + "\n\n" + c.render(active))


def offer_review(payload):
    reports = sorted(glob.glob(os.path.join(c.data_home(), "reviews", "*.md")))
    if not reports:
        return
    latest = reports[-1]
    marker = latest + ".offered"
    if os.path.exists(marker):
        return
    open(marker, "w").close()
    c.emit_context("SessionStart", "A session-memory weekly review is waiting at "
                   f"{latest}. Offer it to the user in one line before starting; do nothing else with it unless asked.")


def main():
    payload = c.read_payload()
    if payload is None:
        return 0
    source = payload.get("source")
    if source == "compact":
        restore(payload)
    elif source == "startup":
        offer_review(payload)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
