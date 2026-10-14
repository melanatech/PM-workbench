#!/usr/bin/env python3
"""Detect unlinked workspace paths in markdown / chat text.

Shared by check_reply_links (Stop) and check_md_links (PostToolUse).
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Known top-level dirs / files that appear in kit replies
KNOWN_PREFIXES = (
    "inbox/", "archive/", "outputs/", "registers/", "state/", "logs/",
    "learning/", "reference/", "prototypes/", "drafts/", "repos/",
    "scripts/", "tools/", "fixtures/", ".claude/",
)
KNOWN_FILES = (
    "CLAUDE.md", "BACKLOG.md", "EVOLVING.md", "SETUP.md", "START HERE.md",
    "CONNECTIONS.md", "SOURCE-POLICY.md", "AGENTS.md", "SKILLS.md",
)
EXT = r"(?:md|csv|txt|json|yml|yaml|html|htm|pdf|js|jsx|ts|tsx|py|sh|css|png|jpg|jpeg|webp|xlsx|xlsm|docx|vtt)"

# Strip fenced code blocks before scanning
FENCE_RE = re.compile(r"```[\s\S]*?```", re.M)
# YAML frontmatter (sources: […] stays plain paths — metadata, not prose)
FRONTMATTER_RE = re.compile(r"\A---\n[\s\S]*?\n---\n", re.M)
# Existing markdown links — their targets are already linked
LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")
# Backtick path: `foo/bar.md` or `inbox/documents/`
BT_PATH_RE = re.compile(
    rf"`((?:{'|'.join(re.escape(p) for p in KNOWN_PREFIXES)})[^`\n]+?/?|"
    rf"(?:{'|'.join(re.escape(f) for f in KNOWN_FILES)}))`"
)
# Bare path with slash (not already in a link): outputs/daily/foo.md
BARE_PATH_RE = re.compile(
    rf"(?<!\]\()"
    rf"(?<![`/\w])"
    rf"((?:{'|'.join(re.escape(p) for p in KNOWN_PREFIXES)})"
    rf"[A-Za-z0-9_./\-[\] ()%+-]+?"
    rf"(?:/{EXT}|\.(?:{EXT})|/))"
    rf"(?![`\w])",
    re.I,
)


def strip_fences(text: str) -> str:
    text = FRONTMATTER_RE.sub("", text, count=1)
    return FENCE_RE.sub("", text)


def linked_targets(text: str) -> set[str]:
    out = set()
    for _, href in LINK_RE.findall(text):
        h = href.strip().split()[0].split("#")[0]
        if h.startswith(("http://", "https://", "mailto:", "file://")):
            continue
        out.add(h.lstrip("./"))
        if h.endswith("/"):
            out.add(h.rstrip("/"))
        else:
            out.add(h + "/")
    return out


def _normalize_candidate(raw: str) -> str:
    s = raw.strip().rstrip(".,;:)")
    # Drop trailing punctuation inside path noise
    while s and s[-1] in ".,;:":
        s = s[:-1]
    return s.lstrip("./")


def resolve_exists(root: Path, rel: str) -> bool:
    if not rel or "*" in rel or "?" in rel:
        return False
    if rel.startswith(("http://", "https://", "~/")):
        return False
    # Ignore shell-ish
    if " " in rel and not Path(root / rel).exists():
        # allow "START HERE.md"
        if rel not in KNOWN_FILES and not any(rel.startswith(p) for p in KNOWN_PREFIXES):
            return False
    try:
        p = (root / rel).resolve()
        root_r = root.resolve()
        if not str(p).startswith(str(root_r)):
            return False
        return p.exists()
    except (OSError, ValueError):
        return False


def find_unlinked_paths(text: str, root: str | Path) -> list[str]:
    """Return sorted unique relative paths that exist but are not linked."""
    root_p = Path(root)
    cleaned = strip_fences(text)
    # Also drop inline code that looks like shell: `npm run …`
    # (BT_PATH_RE only matches known prefixes, so OK)

    already = linked_targets(cleaned)
    found: set[str] = set()

    for m in BT_PATH_RE.finditer(cleaned):
        cand = _normalize_candidate(m.group(1))
        if cand and resolve_exists(root_p, cand):
            found.add(cand if not cand.endswith("/") else cand)
            # Prefer trailing slash for dirs in report
            if (root_p / cand.rstrip("/")).is_dir():
                found.discard(cand.rstrip("/"))
                found.add(cand.rstrip("/") + "/")

    for m in BARE_PATH_RE.finditer(cleaned):
        cand = _normalize_candidate(m.group(1))
        if not cand:
            continue
        # Skip if this span is inside a markdown link target already handled
        if cand in already or cand.rstrip("/") in already or (cand + "/") in already:
            continue
        if resolve_exists(root_p, cand):
            if (root_p / cand.rstrip("/")).is_dir():
                found.add(cand.rstrip("/") + "/")
            else:
                found.add(cand.rstrip("/"))

    unlinked = []
    for p in sorted(found):
        variants = {p, p.rstrip("/"), p.rstrip("/") + "/", p.lstrip("./")}
        if variants & already:
            continue
        unlinked.append(p)
    return unlinked


def file_relative_href(from_file: str, target: str) -> str:
    """Href relative to the markdown file's directory for in-file links."""
    from_dir = Path(from_file).parent
    tgt = Path(target)
    try:
        rel = os.path.relpath(tgt, from_dir).replace(os.sep, "/")
    except ValueError:
        rel = target
    if target.endswith("/") and not rel.endswith("/"):
        rel += "/"
    return rel
