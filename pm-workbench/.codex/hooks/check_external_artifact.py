#!/usr/bin/env python3
"""PostToolUse: external drafts may keep claims, not workspace-only labels.

Watches files under outputs/external/ and any file whose frontmatter says
``audience: external``. Blocks register ids, workspace paths, /Users/ paths,
and internal tags ([NEEDS INPUT], [hypothesis], [external::training]).

Alias rows in reference/context/workspace-aliases.md are classified by how an
outside reader should meet the phrase, not banned as a set:

- ``internal_only`` and an unclassified row block when the phrase appears.
- ``expand`` and ``neutralize`` block until ``scripts/publish.py`` rewrites them.
- ``preserve`` is left alone.

A file still marked ``status: template`` contributes no aliases.
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
from dataclasses import dataclass

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


TREATMENTS = ("internal_only", "expand", "preserve", "neutralize")
_TREATMENT_LIST = "internal_only, expand, preserve, or neutralize"


@dataclass(frozen=True)
class Alias:
    """One alias row. ``treatment`` is empty when the row is unclassified."""

    phrases: tuple[str, ...]
    path: str
    meaning: str
    treatment: str
    external_value: str


def load_aliases(workspace: str | os.PathLike) -> list[Alias]:
    """Read the live alias table. A template file contributes nothing."""
    path = os.path.join(workspace, "reference", "context", "workspace-aliases.md")
    return load_alias_file(path)


def load_alias_file(path: str | os.PathLike) -> list[Alias]:
    if not os.path.isfile(path):
        return []
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    except OSError:
        return []
    if TEMPLATE_RE.search(text):
        return []
    return _parse_alias_table(text)


def load_alias_phrases(workspace: str | os.PathLike) -> list[str]:
    """Phrases that must not appear raw in an external artifact.

    ``preserve`` is omitted. ``internal_only``, ``expand``, ``neutralize``,
    and unclassified rows are included so an untransformed alias still fails.
    """
    return blocking_phrases(load_aliases(workspace))


def blocking_phrases(aliases: list[Alias]) -> list[str]:
    phrases: list[str] = []
    for alias in aliases:
        if alias.treatment == "preserve":
            continue
        phrases.extend(alias.phrases)
    return phrases


def alias_publish_problems(text: str, aliases: list[Alias]) -> list[str]:
    """Name each alias that cannot be published as written.

    ``expand`` and ``neutralize`` with an ``external_value`` are not problems:
    :func:`apply_alias_treatments` rewrites them. ``preserve`` is not a problem.
    """
    problems: list[str] = []
    seen: set[str] = set()
    for alias in aliases:
        for phrase in alias.phrases:
            key = phrase.casefold()
            if key in seen or not _phrase_in(text, phrase):
                continue
            seen.add(key)
            if alias.treatment == "preserve":
                continue
            if alias.treatment == "internal_only":
                problems.append(f'alias "{phrase}" is internal_only and cannot be published')
            elif alias.treatment in ("expand", "neutralize"):
                if not _usable_external_value(alias.external_value):
                    problems.append(
                        f'alias "{phrase}" is {alias.treatment} but has no external_value'
                    )
            else:
                problems.append(
                    f'alias "{phrase}" needs an external_treatment ({_TREATMENT_LIST})'
                )
    return problems


def apply_alias_treatments(text: str, aliases: list[Alias]) -> str:
    """Replace ``expand`` and ``neutralize`` phrases with ``external_value``."""
    jobs: list[tuple[str, str]] = []
    for alias in aliases:
        if alias.treatment not in ("expand", "neutralize"):
            continue
        if not _usable_external_value(alias.external_value):
            continue
        for phrase in alias.phrases:
            jobs.append((phrase, alias.external_value))
    jobs.sort(key=lambda item: len(item[0]), reverse=True)
    rendered = text
    for phrase, value in jobs:
        pattern = rf"(?i)(?<!\w){re.escape(phrase)}(?!\w)"
        rendered = re.sub(pattern, lambda _match, value=value: value, rendered)
    return rendered


def describe_alias_hit(item: str, aliases: list[Alias]) -> str:
    """Explain a blocked alias. Other labels are returned unchanged."""
    folded = item.casefold()
    for alias in aliases:
        if folded not in {phrase.casefold() for phrase in alias.phrases}:
            continue
        if alias.treatment == "internal_only":
            return f"{item} — internal_only; remove it before an outside reader sees it"
        if alias.treatment in ("expand", "neutralize"):
            return (
                f"{item} — {alias.treatment}; run scripts/publish.py "
                "so the external_value replaces it"
            )
        return f"{item} — needs an external_treatment ({_TREATMENT_LIST})"
    return item


def _parse_alias_table(text: str) -> list[Alias]:
    """Parse the Phrase table. Extra columns are treatment and value.

    A three-column row has an empty treatment, which blocks publishing.
    Lines inside fenced code blocks, and any table whose header is not
    ``Phrase``, are not aliases. A blank line ends the Phrase table.
    """
    visible: list[str] = []
    fenced = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            visible.append(line)
    header_at = None
    for index, line in enumerate(visible):
        if not line.startswith("|"):
            continue
        cells = _table_cells(line)
        if cells and cells[0].strip().strip("`").casefold() == "phrase":
            header_at = index
            break
    aliases: list[Alias] = []
    rows = visible if header_at is None else visible[header_at + 1 :]
    for line in rows:
        if header_at is not None and not line.startswith("|"):
            if line.strip() == "":
                break
            continue
        if not line.startswith("|"):
            continue
        cells = _table_cells(line)
        if not cells:
            continue
        raw_phrase = cells[0].strip()
        if not raw_phrase or _is_separator(raw_phrase) or raw_phrase.strip("`").casefold() == "phrase":
            continue
        phrases = _phrases_from_cell(raw_phrase)
        if not phrases:
            continue
        path = cells[1].replace("`", "").strip() if len(cells) > 1 else ""
        meaning = cells[2].strip() if len(cells) > 2 else ""
        treatment = _clean_treatment(cells[3]) if len(cells) > 3 else ""
        external_value = _clean_value(cells[4]) if len(cells) > 4 else ""
        aliases.append(Alias(phrases, path, meaning, treatment, external_value))
    return aliases


def _table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _is_separator(cell: str) -> bool:
    return bool(cell) and set(cell) <= set("-: ")


def _phrases_from_cell(cell: str) -> tuple[str, ...]:
    if cell.strip().startswith("["):
        return ()
    phrases: list[str] = []
    for part in cell.split("/"):
        phrase = part.strip().strip("`")
        if len(phrase) >= 3:
            phrases.append(phrase)
    return tuple(phrases)


def _clean_treatment(cell: str) -> str:
    token = cell.strip().strip("`").casefold().replace(" ", "")
    if token in TREATMENTS:
        return token
    return ""


def _clean_value(cell: str) -> str:
    return cell.strip().strip("`")


def _usable_external_value(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    return not text.casefold().startswith("[needs input")


def _phrase_in(text: str, phrase: str) -> bool:
    return re.search(rf"(?i)(?<!\w){re.escape(phrase)}(?!\w)", text) is not None


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
        aliases = load_aliases(root())
        found = find_banned(text, blocking_phrases(aliases))
        if not found:
            sys.exit(0)
        lines = [
            f"EXTERNAL ARTIFACT BLOCKED in {relative}",
            "These labels cannot ship to an outside reader:",
        ]
        lines.extend(f"  - {describe_alias_hit(item, aliases)}" for item in found)
        lines.append(
            "Rewrite a register id, workspace path, or internal tag as a neutral citation "
            "(meeting name and date, uploaded file name, Jira key, Confluence page, "
            "Slack channel and date, or dashboard name and as-of date), or run scripts/publish.py. "
            "An alias is classified by external_treatment: internal_only (remove it), "
            "expand or neutralize (publish.py replaces it with external_value), "
            "or preserve (leave a phrase an outside reader understands). "
            "An unclassified alias blocks publishing until you classify it."
        )
        block("\n".join(lines))
    except SystemExit:
        raise
    except Exception as exc:
        warn(f"check_external_artifact skipped: {exc}")


if __name__ == "__main__":
    main()
