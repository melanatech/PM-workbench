#!/usr/bin/env python3
"""Classify a capture as full, summary, or excerpt.

Markers: an AI-summary header, a Slack-style "N replies" / "View thread"
with the replies absent, truncation ("…" or "Show more"), and a recap that
has no speaker or timestamp structure. Frontmatter `fidelity:` wins.

A summary or excerpt asks for the full thread only when the text would
create a decision, commitment, owner, date, or risk. Unattended runs label
and never wait.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

FIDELITY_VALUES = ("full", "summary", "excerpt")

_FRONT_FIDELITY = re.compile(r"(?im)^fidelity:\s*(full|summary|excerpt)\s*$")
_AI = re.compile(
    r"(?i)\bai[ -](?:generated )?summary\b|\bai-generated\b|\bmeeting recap\b"
)
_VIEW_THREAD = re.compile(r"(?i)\bview thread\b")
_N_REPLIES = re.compile(r"(?i)\b\d+\s+replies\b")
_SHOW_MORE = re.compile(r"(?i)\bshow more\b")
_SPEAKER = re.compile(
    r"(?m)^(?:\d{4}-\d{2}-\d{2}\s+)?"
    r"(?:\d{1,2}:\d{2}\s+)?"
    r"(?P<name>[A-Z][\w.'-]{0,30}(?:\s[A-Z][\w.'-]{0,30})?):\s+\S"
)
# Field labels in a recap are not speakers. "Decision:" must not look like dialogue.
_LABELS = {
    "decision",
    "owner",
    "due",
    "risk",
    "summary",
    "action",
    "note",
    "status",
    "date",
    "deadline",
    "commitment",
}
_TIMESTAMP = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}:\d{2}\b")
_MATERIAL = re.compile(
    r"(?i)\b("
    r"decision|decided|decide|"
    r"commitment|committed|"
    r"owner|"
    r"due|"
    r"deadline|"
    r"risk"
    r")\b"
)


def _speaker_names(body: str) -> list[str]:
    names = []
    for match in _SPEAKER.finditer(body or ""):
        name = match.group("name").split()[0].lower()
        if name in _LABELS:
            continue
        names.append(match.group("name"))
    return names


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    end = text.find("\n---", 3)
    if end == -1:
        return text
    return text[end + 4 :]


def classify_fidelity(text: str) -> str:
    """Return full, summary, or excerpt."""
    raw = text or ""
    explicit = _FRONT_FIDELITY.search(raw)
    if explicit:
        return explicit.group(1).lower()
    body = _strip_frontmatter(raw)
    speakers = _speaker_names(body)
    has_timestamps = bool(_TIMESTAMP.search(body))
    preview = bool(_VIEW_THREAD.search(body) or _N_REPLIES.search(body))
    truncated = bool(_SHOW_MORE.search(body) or "…" in body)
    ai_summary = bool(_AI.search(body))
    replies_present = len(speakers) >= 2

    if preview and not replies_present:
        return "excerpt"
    if truncated and not replies_present:
        return "excerpt"
    if ai_summary and not (replies_present and has_timestamps):
        return "summary"
    if replies_present and has_timestamps:
        return "full"
    if replies_present and not ai_summary and not preview and not truncated:
        return "full"
    return "summary"


def is_material(text: str) -> bool:
    """True when the text would create a decision, commitment, owner, date, or risk."""
    return bool(_MATERIAL.search(text or ""))


def fidelity_gate(text: str, *, unattended: bool = False) -> dict:
    """Decide whether to ask for the full thread.

    action is proceed, proceed-labeled, or ask.
    Unattended runs never ask.
    """
    fidelity = classify_fidelity(text)
    material = is_material(text)
    ask = fidelity != "full" and material and not unattended
    if fidelity == "full":
        action = "proceed"
    elif ask:
        action = "ask"
    else:
        action = "proceed-labeled"
    return {
        "fidelity": fidelity,
        "material": material,
        "ask": ask,
        "action": action,
        "tag": f"source_fidelity={fidelity}",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify capture fidelity")
    parser.add_argument("path", nargs="?", help="capture file; stdin when omitted")
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="label and never ask (scheduled runs)",
    )
    args = parser.parse_args(argv)
    if args.path:
        text = Path(args.path).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()
    json.dump(fidelity_gate(text, unattended=args.unattended), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
