#!/usr/bin/env python3
"""Fail when a kit file names a specific person, company, project, or internal system.

The kit is public and generic. Anything about one PM's company, team, projects,
metrics, tools, channels, or tables belongs in the live workspace instead:
gitignored local files (`.claude/CLAUDE.local.md`, `reference/context/*.md`
without `.example`) or a live-only folder such as `.claude-live/`. Kit files say
"the PM" and point at those local files.

Terms come from two places, so the public kit never has to list them:
  - built-in patterns (emails, home-directory paths, private wiki or dashboard URLs)
  - `.claude/kit-private-terms.txt` (gitignored), one term per line. A plain line
    matches as a case-insensitive whole word; `re:` starts a regex; `#` is a comment.
    The PM name, email, and usernames in `.cursor/hooks/pm-identity.json` are added.

Usage:
  python3 scripts/check_kit_generic.py                 # every kit file git would track
  python3 scripts/check_kit_generic.py PATH [PATH ...] # only these (others are ignored)
  python3 scripts/check_kit_generic.py --staged        # files staged for commit
Exit 0 when clean, 1 on any hit.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
REPO = KIT.parent if (KIT.parent / ".git").exists() else KIT
TERMS_FILE = KIT / ".claude" / "kit-private-terms.txt"
IDENTITY_FILE = KIT / ".cursor" / "hooks" / "pm-identity.json"

TEXT_SUFFIXES = {
    ".md", ".py", ".json", ".yml", ".yaml", ".html", ".js", ".jsx", ".ts", ".tsx",
    ".sh", ".css", ".toml", ".txt", ".csv", ".example", ".command", "",
}
SKIP_NAMES = {"kit-private-terms.txt", "CLAUDE.local.md", "settings.local.json", "pm-identity.json"}
SKIP_PARTS = {".git", "__pycache__", "node_modules", "build"}

BUILTIN = [
    ("email address", re.compile(r"\b[\w.+-]+@(?!example\.)[\w-]+\.(?:com|net|org|io|co)\b", re.I)),
    ("home-directory path", re.compile(r"/Users/(?!(?:someone|you|me|x|name|user|example|<[^>/]+>)/)[A-Za-z][\w.-]*/")),
    ("private wiki URL", re.compile(r"https?://(?!(?:yourcompany|your-company|example|acme|lumenly)\.)[\w-]+\.atlassian\.net/(?:wiki|browse)/\S+", re.I)),
    ("private dashboard URL", re.compile(r"https?://[\w.-]*(?:quicksight\.aws|sharepoint\.com|tableau\.[\w.-]+/#/|lookerstudio)\S*", re.I)),
    ("internal hostname", re.compile(r"https?://[\w.-]+\.(?:int|corp|internal)\.[\w.-]+", re.I)),
]

EMAIL_OK = re.compile(r"@(?:example|company|yourco|yourcompany|lumenly)\.", re.I)


def _plain(term: str) -> re.Pattern:
    body = re.escape(term)
    left = r"(?<![\w-])" if term[:1].isalnum() else ""
    right = r"(?![\w])" if term[-1:].isalnum() else ""
    return re.compile(left + body + right, re.I)


def load_terms() -> list[tuple[str, re.Pattern]]:
    terms: list[tuple[str, re.Pattern]] = []
    if TERMS_FILE.is_file():
        for raw in TERMS_FILE.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("re:"):
                pat = line[3:].strip()
                terms.append((pat, re.compile(pat, re.I)))
            else:
                terms.append((line, _plain(line)))
    if IDENTITY_FILE.is_file():
        try:
            ident = json.loads(IDENTITY_FILE.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            ident = {}
        name = str(ident.get("name") or "").strip()
        extra = [name, *name.split()[:1], str(ident.get("email") or "")]
        extra += [str(u) for u in ident.get("username_examples") or []]
        aid = str(ident.get("jira_account_id") or "")
        if aid:
            extra.append(aid.split(":")[0] + ":")
        for t in extra:
            t = t.strip()
            if len(t) >= 3:
                terms.append((t, _plain(t)))
    return terms


def plain_terms() -> list[str]:
    """Plain (non-regex) private terms, for tests that check substrings."""
    return [label for label, _ in load_terms() if not any(c in label for c in "\\()[]|?*+")]


def kit_files(staged: bool = False) -> list[Path]:
    root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=KIT, text=True).strip())
    if staged:
        cmd = ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]
    else:
        cmd = ["git", "ls-files", "--cached", "--others", "--exclude-standard"]
    out = subprocess.check_output(cmd, cwd=root, text=True)
    return [root / rel for rel in out.splitlines() if rel.strip()]


def wanted(path: Path) -> bool:
    if not path.is_file() or path.name in SKIP_NAMES:
        return False
    if any(part in SKIP_PARTS for part in path.parts):
        return False
    return path.suffix.lower() in TEXT_SUFFIXES


def in_kit(path: Path) -> bool:
    """True for files in the kit's git repo (the kit folder and the published site around it)."""
    try:
        path.resolve().relative_to(REPO)
    except ValueError:
        return False
    return True


def scan_text(text: str, terms: list[tuple[str, re.Pattern]]) -> list[tuple[int, str, str]]:
    hits: list[tuple[int, str, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for label, pat in BUILTIN:
            for m in pat.finditer(line):
                if label == "email address" and EMAIL_OK.search(m.group(0)):
                    continue
                hits.append((line_no, label, m.group(0)))
        for label, pat in terms:
            m = pat.search(line)
            if m:
                hits.append((line_no, label, m.group(0)))
    return hits


def scan(paths: list[Path], terms: list[tuple[str, re.Pattern]] | None = None) -> list[str]:
    terms = load_terms() if terms is None else terms
    out: list[str] = []
    for path in paths:
        path = path.resolve()
        if not in_kit(path) or not wanted(path):
            continue
        rel = path.relative_to(REPO)
        try:
            kit_rel = path.relative_to(KIT)
        except ValueError:
            kit_rel = None
        if kit_rel and kit_rel.parts and kit_rel.parts[0] in {"inbox", "archive", "state", "logs", "registers", "repos", "outputs"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, label, found in scan_text(text, terms):
            out.append(f"{rel}:{line_no}: {found!r} ({label})")
    return out


FIX = (
    "The kit is public and generic. Say \"the PM\" and use neutral examples, or move the "
    "specific content to the live workspace: `.claude/CLAUDE.local.md`, a local "
    "`reference/context/*.md` (for workflow specifics, `reference/context/workflow-notes.md` "
    "under the workflow's heading), or `.claude-live/`."
)


def main(argv: list[str]) -> int:
    staged = "--staged" in argv
    args = [a for a in argv if not a.startswith("--")]
    paths = [Path(a) for a in args] if args else kit_files(staged=staged)
    hits = scan(paths)
    if hits:
        print("Kit files name a specific person, company, project, or internal system:")
        for h in hits:
            print("  " + h)
        print(FIX)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
