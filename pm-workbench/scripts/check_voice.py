#!/usr/bin/env python3
"""Judge whether a team-facing draft sounds like a person on the team.

This is a read of the prose, not a phrase list. The rubric is the External
writing section of ``reference/context/writing-style.md`` when that file has
one. Otherwise a short generic rubric is used.

  python3 scripts/check_voice.py <file> [<file> ...]
  python3 scripts/check_voice.py --root <live> <file>

Exit 0 when the draft passes, or when the judge could not run (that case is
printed, and the draft is still saved). Exit 1 when the judge fails the draft.
A write hook turns that failure into a block so the file is not saved. A check
that did not run is not a failure.

Set CHECK_VOICE_REPLY to a JSON reply to skip the model (tests).
Set CHECK_VOICE_DISABLE=1 to skip the check.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_RUBRIC = """
Sound like a person on the team talking: specific, spoken, worth reading.
Fail prose that performs structure or sharpness instead of saying the thing:
a memo cadence, a heading that announces the move the next lines will make,
a sentence that exists to set up its own opposite, or a throat-clearing open.
A direct statement can stand, including a scope cut, an exclusion, or a
tradeoff named as a cost.
""".strip()

TEAM_PREFIXES = (
    "outputs/prds/",
    "outputs/external/",
    "outputs/weekly/",
    "outputs/strategy/",
    "drafts/",
)
TEXT_EXT = {".md", ".html", ".htm", ".txt"}
MIN_EDIT_CHARS = 240
MAX_DRAFT_CHARS = 60_000

FENCE_RE = re.compile(r"```.*?```", re.S)
FRONT_RE = re.compile(r"\A---\r?\n.*?\r?\n---\r?\n?", re.S)
TAG_RE = re.compile(r"<[^>]+>")
AUDIENCE_RE = re.compile(r"(?m)^audience:\s*(external|team)\s*$", re.I)
SECTION_RE = re.compile(
    r"^## External writing\b[^\n]*\n(.*?)(?=^## |\Z)",
    re.M | re.S,
)
TEMPLATE_RE = re.compile(r"(?m)^status:\s*template\s*$")


@dataclass
class Note:
    quote: str
    why: str


@dataclass
class Verdict:
    """``ok`` is True on a pass. ``unavailable`` means the judge did not run."""

    ok: bool
    notes: list[Note]
    unavailable: str = ""


def is_team_facing(relative: str, text: str = "") -> bool:
    rel = relative.replace(os.sep, "/").lstrip("./")
    if Path(rel).suffix.lower() not in TEXT_EXT:
        return False
    if any(rel.startswith(prefix) for prefix in TEAM_PREFIXES):
        return True
    return _audience(text)


def _audience(text: str) -> bool:
    return bool(text and AUDIENCE_RE.search(text))


def _external_section(text: str) -> str:
    match = SECTION_RE.search(text)
    body = match.group(1).strip() if match else ""
    if len(body) < 40:
        return ""
    return "## External writing\n" + body


def rubric_for(workspace: Path) -> str:
    """Live External writing wins. Otherwise the kit example, then a short default."""
    live = workspace / "reference" / "context" / "writing-style.md"
    if live.is_file():
        text = live.read_text(encoding="utf-8", errors="replace")
        if not TEMPLATE_RE.search(text):
            section = _external_section(text)
            if section:
                return section
    example = Path(__file__).resolve().parents[1] / "reference" / "context" / "writing-style.example.md"
    if example.is_file():
        section = _external_section(example.read_text(encoding="utf-8", errors="replace"))
        if section:
            return section
    return DEFAULT_RUBRIC


def prose_of(text: str) -> str:
    body = FRONT_RE.sub("", text, count=1)
    body = FENCE_RE.sub(" ", body)
    if "<" in body and ">" in body:
        body = TAG_RE.sub(" ", body)
    body = re.sub(r"[ \t]+\n", "\n", body)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    if len(body) > MAX_DRAFT_CHARS:
        body = body[:MAX_DRAFT_CHARS]
    return body


def _prompt(rubric: str, draft: str) -> str:
    return (
        "Judge this team-facing draft. Read it. Decide whether a teammate would "
        "hear a person on the team talking.\n\n"
        f"Rubric:\n{rubric}\n\n"
        "Fail the draft when the writing performs structure or sharpness instead of "
        "saying the thing: a memo cadence, a heading that announces the move the next "
        "lines will make, a sentence that exists to set up its own opposite, or a "
        "throat-clearing open. Pass a direct statement, including a scope cut, an "
        "exclusion, or a tradeoff named as a cost. Pass the structure the document "
        "type requires: a section, a table, a test case, a ticket key, or a workspace "
        "id in a working draft. Those are not the problem.\n\n"
        'Return JSON only, no markdown:\n{"pass": true}\nor\n'
        '{"pass": false, "notes": [{"quote": "the sentence", "why": "one short clause"}]}\n\n'
        "List every problem in this draft. Quote each one once. Do not stop after a sample, "
        "and do not rewrite the draft.\n\n"
        f"Draft:\n{draft}\n"
    )


def _parse(raw: str | None) -> Verdict:
    if not raw or not raw.strip():
        return Verdict(False, [], unavailable="the judge returned nothing")
    match = re.search(r"\{.*\}", raw, re.S)
    if not match:
        return Verdict(False, [], unavailable="the judge did not return JSON")
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return Verdict(False, [], unavailable="the judge returned unreadable JSON")
    if data.get("pass") is True:
        return Verdict(True, [])
    notes: list[Note] = []
    for item in data.get("notes") or []:
        if not isinstance(item, dict):
            continue
        quote = str(item.get("quote") or "").strip()
        why = str(item.get("why") or "").strip()
        if quote or why:
            notes.append(Note(quote or "(the draft)", why or "reads as a memo"))
    return Verdict(False, notes)


def _claude_bin() -> str | None:
    forced = os.environ.get("VOICE_CHECK_CLAUDE")
    if forced:
        return forced
    found = shutil.which("claude")
    local = Path.home() / ".local" / "bin" / "claude"
    if found and "gocode/shims" in found and local.exists():
        return str(local)
    return found


def _lean_cwd() -> str:
    path = os.path.join(tempfile.gettempdir(), "claude-lean-call")
    os.makedirs(path, exist_ok=True)
    return path


def ask_model(prompt: str) -> str | None:
    if "CHECK_VOICE_REPLY" in os.environ:
        return os.environ.get("CHECK_VOICE_REPLY") or None
    binary = _claude_bin()
    if not binary:
        return None
    model = os.environ.get("VOICE_CHECK_MODEL", "sonnet")
    env = {**os.environ, "SESSION_MEMORY_INTERNAL": "1"}
    try:
        result = subprocess.run(
            # A check answers one prompt. No tools, no project context, and not saved as a session.
            [binary, "-p", prompt, "--tools", "", "--strict-mcp-config", "--disable-slash-commands",
             "--system-prompt", "Answer the prompt. Reply with JSON only.",
             "--no-session-persistence", "--model", model, "--permission-mode", "dontAsk"],
            capture_output=True,
            text=True,
            timeout=150,
            cwd=_lean_cwd(),
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout


DRAFT_OVERRIDE = (
    "This file is a working draft, not the share copy. Ignore any line in the "
    "rubric that bans workspace ids, ticket keys, or a status line. Do not flag "
    "a required section, a table, or a one-line scope cut. Flag a sentence that "
    "exists to sound sharp, a heading that announces its own move, or an opening "
    "that clears its throat."
)


def evaluate(text: str, rubric: str, ask=ask_model, relative: str = "") -> Verdict:
    draft = prose_of(text)
    if len(draft) < 24:
        return Verdict(True, [])
    rel = relative.replace(os.sep, "/")
    if rel.startswith(("outputs/prds/", "drafts/")) or "/outputs/prds/" in f"/{rel}" or "/drafts/" in f"/{rel}":
        rubric = rubric + "\n\n" + DRAFT_OVERRIDE
    raw = ask(_prompt(rubric, draft))
    return _parse(raw)


def report(relative: str, verdict: Verdict) -> str:
    if verdict.unavailable:
        return (
            f"voice check did not run on {relative}: {verdict.unavailable}. "
            "Save the file. This is not a voice failure."
        )
    if verdict.ok:
        return f"voice check passed: {relative}"
    lines = [
        f"VOICE in {relative}",
        "This draft does not sound like a person on the team. Every problem found is listed below.",
    ]
    if not verdict.notes:
        lines.append("  - the piece reads as a memo. Say the thing in a spoken sentence.")
    for note in verdict.notes:
        lines.append(f"  - {note.quote} ({note.why})")
    lines.append(
        "Fix every note above, then run the check once more to confirm. "
        "A plain scope cut or a named tradeoff can stand. "
        "Rubric: reference/context/writing-style.md § External writing."
    )
    return "\n".join(lines)


def judge(text: str, workspace: Path, ask=ask_model, relative: str = "") -> Verdict:
    if os.environ.get("CHECK_VOICE_DISABLE") == "1":
        return Verdict(True, [])
    return evaluate(text, rubric_for(workspace), ask=ask, relative=relative)


def check_file(path: Path, workspace: Path, ask=ask_model) -> Verdict:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        relative = str(path.resolve().relative_to(workspace.resolve()))
    except ValueError:
        relative = path.name
    return judge(text, workspace, ask=ask, relative=relative)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    workspace = Path.cwd()
    if args[:1] == ["--root"]:
        if len(args) < 3:
            print("usage: check_voice.py --root <live> <file> ...", file=sys.stderr)
            return 2
        workspace = Path(args[1]).expanduser().resolve()
        args = args[2:]
    if not args:
        print("usage: check_voice.py <file> ...", file=sys.stderr)
        return 2
    failed = False
    for raw in args:
        path = Path(raw)
        if not path.is_file():
            path = workspace / raw
        if not path.is_file():
            print(f"voice check did not run: {raw} is not a file")
            continue
        verdict = check_file(path, workspace)
        print(report(str(raw), verdict))
        if not verdict.ok and not verdict.unavailable:
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
