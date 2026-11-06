#!/usr/bin/env python3
"""Check that an edit to an existing HTML artifact kept its design.

Usage (from the live workspace or the kit):
  python3 scripts/check_design_preserved.py <file.html> --git <ref>
  python3 scripts/check_design_preserved.py <file.html> --before <old.html>

``--git`` reads the previous version with ``git show <ref>:<path>`` from the
repo that holds the file (``HEAD`` before committing, ``<sha>~1`` after).

Compares three things between the previous and the current file:
1. Every ``<style>`` block, whitespace-normalized.
2. Stylesheet and script ``src``/``href`` assets, in order.
3. The markup skeleton: tag and class names under ``<body>`` to ``--depth``
   levels (default 3). Text is ignored, and repeated siblings with the same
   tag and class count once, so more cards or rows of an existing kind pass.

Exit 0 when all three match, 1 when any changed (the design changed: stop
unless the PM asked for a design change), 2 on usage errors. Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "source", "track", "wbr",
}


class _Shape(HTMLParser):
    def __init__(self, depth: int) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = depth
        self.styles: list[str] = []
        self.assets: list[str] = []
        self.root: dict = {"sig": "body", "kids": []}
        self._stack: list[dict] = []
        self._in_body = False
        self._in_style = False
        self._in_script = False
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "style":
            self._in_style, self._buf = True, []
            return
        if tag == "script":
            if a.get("src"):
                self.assets.append(f"script:{a['src']}")
            self._in_script = True
            return
        if tag == "link" and "stylesheet" in (a.get("rel") or ""):
            self.assets.append(f"css:{a.get('href', '')}")
        if tag == "body":
            self._in_body, self._stack = True, [self.root]
            return
        if not self._in_body or self._in_script or not self._stack:
            return
        cls = ".".join(sorted((a.get("class") or "").split()))
        node = {"sig": tag + (f".{cls}" if cls else ""), "kids": []}
        level = len(self._stack)
        if level <= self.depth:
            parent = self._stack[-1]
            if node["sig"] not in [k["sig"] for k in parent["kids"]]:
                parent["kids"].append(node)
            else:
                node = next(k for k in parent["kids"] if k["sig"] == node["sig"])
        if tag not in VOID:
            self._stack.append(node)

    def handle_endtag(self, tag):
        if tag == "style" and self._in_style:
            self.styles.append(" ".join("".join(self._buf).split()))
            self._in_style = False
            return
        if tag == "script":
            self._in_script = False
            return
        if tag == "body":
            self._in_body = False
            return
        if self._in_body and not self._in_script and len(self._stack) > 1:
            self._stack.pop()

    def handle_data(self, data):
        if self._in_style:
            self._buf.append(data)


def _lines(node: dict, indent: int = 0) -> list[str]:
    out = []
    for kid in node["kids"]:
        out.append("  " * indent + kid["sig"])
        out.extend(_lines(kid, indent + 1))
    return out


def shape(text: str, depth: int) -> _Shape:
    p = _Shape(depth)
    p.feed(text)
    p.close()
    return p


def _git_previous(path: Path, ref: str) -> str:
    top = subprocess.run(
        ["git", "-C", str(path.parent), "rev-parse", "--show-toplevel"],
        capture_output=True, text=True,
    )
    if top.returncode:
        raise SystemExit(f"error: {path} is not in a git repo")
    rel = path.resolve().relative_to(Path(top.stdout.strip()).resolve())
    shown = subprocess.run(
        ["git", "-C", top.stdout.strip(), "show", f"{ref}:{rel.as_posix()}"],
        capture_output=True, text=True,
    )
    if shown.returncode:
        raise SystemExit(f"error: git show {ref}:{rel} failed: {shown.stderr.strip()}")
    return shown.stdout


def compare(before: str, after: str, depth: int = 3) -> list[str]:
    old, new = shape(before, depth), shape(after, depth)
    problems = []
    if old.styles != new.styles:
        o = set(re.split(r"(?<=\})", " ".join(old.styles)))
        n = set(re.split(r"(?<=\})", " ".join(new.styles)))
        problems.append(
            f"<style> changed: {len(n - o)} rule(s) added or edited, {len(o - n)} removed"
        )
    if old.assets != new.assets:
        problems.append(f"assets changed: {old.assets} -> {new.assets}")
    old_sk, new_sk = _lines(old.root), _lines(new.root)
    if old_sk != new_sk:
        gone = [s.strip() for s in old_sk if s not in new_sk][:8]
        added = [s.strip() for s in new_sk if s not in old_sk][:8]
        problems.append(f"markup skeleton changed: removed {gone}, added {added}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--git", metavar="REF", help="previous version from git")
    src.add_argument("--before", metavar="FILE", help="previous version on disk")
    ap.add_argument("--depth", type=int, default=3)
    args = ap.parse_args(argv)

    path = Path(args.file)
    if not path.is_file():
        print(f"error: {path} not found", file=sys.stderr)
        return 2
    try:
        before = (
            _git_previous(path, args.git) if args.git
            else Path(args.before).read_text(encoding="utf-8")
        )
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    problems = compare(before, path.read_text(encoding="utf-8"), args.depth)
    if problems:
        print(f"FAIL design changed in {path}:")
        for p in problems:
            print(f"  - {p}")
        print("Stop. Restore the previous design unless the PM asked for a design change.")
        return 1
    print(f"PASS design preserved in {path} (style, assets, skeleton depth {args.depth})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
