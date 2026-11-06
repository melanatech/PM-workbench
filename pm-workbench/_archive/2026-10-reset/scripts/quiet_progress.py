#!/usr/bin/env python3
"""Detect a play-by-play status reply during a multi-agent batch.

Allowed while work is in flight: one line `Batch: N of M on disk`, or the
closing `## Output index`. Narrating timers, waiting, and each agent finish
is chatter.
"""
from __future__ import annotations

import re

PATTERNS = (
    r"\bstill running\b",
    r"\bwaiting on\b",
    r"\bagent (finished|completed|stopped)\b",
    r"\bbackground (task|work)\b",
    r"\btimers?\b",
    r"\btask-notification\b",
    r"\bkeep (going|polling)\b",
)
BATCH_LINE = re.compile(r"^Batch: \d+ of \d+ on disk\.?\s*$", re.I)


def chatter_hits(text: str) -> list[str]:
    body = text or ""
    if "## Output index" in body:
        return []
    if BATCH_LINE.match(body.strip()):
        return []
    hits = [pat for pat in PATTERNS if re.search(pat, body, re.I)]
    if len(hits) >= 2:
        return hits
    if len(hits) == 1 and len(body) < 280 and not re.search(r"(?m)^#{1,3} ", body):
        return hits
    return []
