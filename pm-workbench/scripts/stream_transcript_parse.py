#!/usr/bin/env python3
"""Pure helpers mirroring Workbench Clipper Stream transcript scrape (v0.6+).

Keep in sync with tools/workbench-clipper/background.js:
  - DURATION_RE / parse_speaker_label
  - format_transcript (merge consecutive same-speaker rows)
  - missing_positions / incomplete when any gap in 1..setsize
"""
from __future__ import annotations

import re
from typing import Any

DURATION_RE = re.compile(
    r"\s+(?:(\d+)\s+hours?\s+)?(?:(\d+)\s+minutes?\s+)?(\d+)\s+seconds?\s*$",
    re.I,
)


def parse_speaker_label(label: str) -> tuple[str, str]:
    """Return (speaker, time as h:mm:ss or m:ss)."""
    if not label:
        return "", ""
    m = DURATION_RE.search(label)
    if not m:
        return label.strip(), ""
    speaker = label[: m.start()].strip()
    h = int(m.group(1) or 0)
    minute = int(m.group(2) or 0)
    sec = int(m.group(3) or 0)
    if h > 0:
        time = f"{h}:{minute:02d}:{sec:02d}"
    else:
        time = f"{minute}:{sec:02d}"
    return speaker, time


def missing_positions(by_pos: dict[int, Any], set_size: int) -> list[int]:
    if not set_size:
        return []
    return [i for i in range(1, set_size + 1) if i not in by_pos]


def format_transcript(by_pos: dict[int, dict[str, str]]) -> str:
    """Merge consecutive rows from the same speaker into one paragraph."""
    positions = sorted(by_pos)
    parts: list[str] = []
    prev_speaker: str | None = None
    buf: list[str] = []
    buf_time = ""

    def flush() -> None:
        nonlocal buf, buf_time
        if not buf:
            return
        if prev_speaker:
            head = f"**{prev_speaker}** [{buf_time}]: " if buf_time else f"**{prev_speaker}**: "
        else:
            head = ""
        parts.append(head + " ".join(buf))
        buf = []
        buf_time = ""

    for pos in positions:
        row = by_pos[pos]
        speaker = row.get("speaker") or None
        text = row.get("text") or ""
        time = row.get("time") or ""
        if speaker != prev_speaker:
            flush()
            prev_speaker = speaker
            buf_time = time
            buf = [text]
        else:
            if not buf_time and time:
                buf_time = time
            buf.append(text)
    flush()
    return "\n\n".join(parts)


def parse_vtt(text: str) -> str:
    """Turn WebVTT into Speaker [time]: cue lines (best-effort)."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    i = 0
    if lines and lines[0].strip().upper().startswith("WEBVTT"):
        i = 1
    while i < len(lines):
        line = lines[i].strip()
        i += 1
        if not line or "-->" not in line:
            # cue id line then timing
            if i < len(lines) and "-->" in lines[i]:
                line = lines[i].strip()
                i += 1
            else:
                continue
        # 00:01:02.000 --> 00:01:05.000
        start = line.split("-->")[0].strip()
        # drop millis
        if "." in start:
            start = start.split(".", 1)[0]
        # normalize leading hours
        parts_t = start.split(":")
        if len(parts_t) == 3 and parts_t[0] == "00":
            start = f"{int(parts_t[1])}:{parts_t[2]}"
        cue_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            cue_lines.append(lines[i].strip())
            i += 1
        if not cue_lines:
            continue
        body = " ".join(cue_lines)
        speaker = ""
        # <v Speaker>text</v> or Speaker: text
        vm = re.match(r"<v(?:\s+([^>]+))?>(.*)</v>", body, re.I | re.S)
        if vm:
            speaker = (vm.group(1) or "").strip()
            body = (vm.group(2) or "").strip()
        elif ": " in body[:80]:
            speaker, body = body.split(": ", 1)
            speaker = speaker.strip()
            body = body.strip()
        if speaker:
            out.append(f"**{speaker}** [{start}]: {body}")
        else:
            out.append(f"[{start}] {body}")
    return "\n\n".join(out)
