#!/usr/bin/env python3
"""PostToolUse: external drafts may keep claims, not workspace-only labels.

Watches files under outputs/external/ and any file whose frontmatter says
``audience: external``. Blocks register ids, workspace paths, /Users/ paths,
internal tags ([NEEDS INPUT], [hypothesis], [external::training]), and
codename phrases from reference/context/workspace-aliases.md.

A file still marked ``status: template`` contributes no codenames.
Neutral citations (meeting name and date, uploaded file name, Jira key,
Confluence title, Slack channel and date, dashboard name and as-of date)
are not labels and are allowed.

Fails open on an internal error so a broken hook cannot block other work.
"""
from __future__ import annotations

import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, rel, block, warn  # noqa: E402

REGISTER_RE = re.compile(r"\b(?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5}\b")
USERS_RE = re.compile(r"/Users/[A-Za-z0-9_./\-]+")
TAG_RE = re.compile(
    r"\[(?:NEEDS INPUT[^\]]*|hypothesis[^\]]*|external::training)\]",
    re.I,
)
_PATH_PREFIX = (
    r"(?:inbox|archive|outputs|registers|state|logs|learning|reference|"
    r"prototypes|drafts|repos|scripts|tools|fixtures|\.claude)/"
)
_PATH_EXT = r"(?:md|csv|txt|json|yml|yaml|html|htm|pdf|py|docx|pptx|xlsx|png)"
PATH_RE = re.compile(
    rf"(?<![\w./])({_PATH_PREFIX}"
    rf"(?:[A-Za-z0-9_.\-]+/)*"
    rf"[A-Za-z0-9_.\- ]*?\.{_PATH_EXT})"
)
FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---", re.S)
TEMPLATE_RE = re.compile(r"(?m)^status:\s*template\s*$")
TEXT_EXT = {".md", ".html", ".htm", ".xml", ".txt"}


def audience_is_external(text: str) -> bool:
    match = FRONTMATTER_RE.match(text)
    if not match:
        return False
    return re.search(r"(?m)^audience:\s*external\s*$", match.group(1)) is not None


def load_alias_phrases(workspace: str | os.PathLike) -> list[str]:
    path = os.path.join(workspace, "reference", "context", "workspace-aliases.md")
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return []
    if TEMPLATE_RE.search(text):
        return []
    phrases: list[str] = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.strip().strip("|").split("|")[0].strip()
        if not cell or cell.casefold() == "phrase" or set(cell) <= set("-: "):
            continue
        if cell.startswith("["):
            continue
        for part in cell.split("/"):
            phrase = part.strip().strip("`")
            if len(phrase) >= 3:
                phrases.append(phrase)
    return phrases


def find_banned(text: str, phrases: list[str] | None = None) -> list[str]:
    """Return workspace-only labels in ``text``. Claims and neutral citations pass."""
    found: list[str] = []
    for match in REGISTER_RE.finditer(text):
        found.append(match.group(0))
    for match in PATH_RE.finditer(text):
        found.append(match.group(1))
    for match in USERS_RE.finditer(text):
        found.append(match.group(0))
    for match in TAG_RE.finditer(text):
        found.append(match.group(0))
    for phrase in phrases or []:
        if re.search(rf"(?i)(?<!\w){re.escape(phrase)}(?!\w)", text):
            found.append(phrase)
    seen: set[str] = set()
    unique: list[str] = []
    for item in found:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def external_text(path: str, relative: str) -> str | None:
    """Return text to scan, or None when this write is not an external artifact."""
    suffix = os.path.splitext(path)[1].lower()
    under_external = relative.startswith("outputs/external/")
    if suffix == ".docx":
        if not under_external:
            return None
        try:
            with zipfile.ZipFile(path) as archive:
                return archive.read("word/document.xml").decode("utf-8", errors="replace")
        except (KeyError, zipfile.BadZipFile, OSError):
            return ""
    if suffix not in TEXT_EXT:
        return None
    try:
        text = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return None
    if under_external or audience_is_external(text):
        return text
    return None


def main() -> None:
    try:
        incoming = payload()
        path = (incoming.get("tool_input", {}) or {}).get("file_path") or ""
        relative = rel(path)
        full = path if os.path.isabs(path) else os.path.join(root(), relative)
        if not os.path.isfile(full):
            sys.exit(0)
        text = external_text(full, relative)
        if text is None:
            sys.exit(0)
        found = find_banned(text, load_alias_phrases(root()))
        if not found:
            sys.exit(0)
        lines = [
            f"EXTERNAL ARTIFACT BLOCKED in {relative}",
            "Workspace-only labels cannot ship to an outside reader:",
        ]
        lines.extend(f"  - {item}" for item in found)
        lines.append(
            "Rewrite them as neutral citations (meeting name and date, uploaded file name, "
            "Jira key, Confluence page, Slack channel and date, or dashboard name and as-of date) "
            "or run scripts/publish.py. Claims stay; these labels do not."
        )
        block("\n".join(lines))
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"check_external_artifact skipped: {exc}")


if __name__ == "__main__":
    main()
