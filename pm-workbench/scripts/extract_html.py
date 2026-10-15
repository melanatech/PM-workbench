#!/usr/bin/env python3
"""Extract visible HTML text and static data embedded in JavaScript.

Many saved internal pages render from top-level JS arrays, leaving almost no
text in the DOM. When visible text is sparse, preserve those data assignments
without executing the page.
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.in_script = False
        self.script_type = ""
        self.visible: list[str] = []
        self.scripts: list[tuple[str, str]] = []
        self._script_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"style", "template", "noscript", "svg"}:
            self.hidden_depth += 1
        if tag == "script":
            self.in_script = True
            self.script_type = dict(attrs).get("type") or ""
            self._script_parts = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self.in_script:
            self.scripts.append((self.script_type, "".join(self._script_parts)))
            self.in_script = False
            self.script_type = ""
            self._script_parts = []
        if tag in {"style", "template", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self._script_parts.append(data)
        elif not self.hidden_depth:
            text = " ".join(data.split())
            if text:
                self.visible.append(text)


_ASSIGNMENT = re.compile(
    r"\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*([\[{])"
)


def balanced_value(script: str, start: int) -> str | None:
    pairs = {"[": "]", "{": "}"}
    stack = [pairs[script[start]]]
    quote = ""
    escaped = False
    line_comment = False
    block_comment = False
    i = start + 1
    while i < len(script):
        char = script[i]
        nxt = script[i + 1] if i + 1 < len(script) else ""
        if line_comment:
            if char == "\n":
                line_comment = False
        elif block_comment:
            if char == "*" and nxt == "/":
                block_comment = False
                i += 1
        elif quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
        elif char in {'"', "'", "`"}:
            quote = char
        elif char == "/" and nxt == "/":
            line_comment = True
            i += 1
        elif char == "/" and nxt == "*":
            block_comment = True
            i += 1
        elif char in pairs:
            stack.append(pairs[char])
        elif stack and char == stack[-1]:
            stack.pop()
            if not stack:
                return script[start : i + 1]
        i += 1
    return None


def embedded_data(scripts: list[tuple[str, str]]) -> list[str]:
    blocks: list[str] = []
    for script_type, script in scripts:
        if script_type.lower() in {"application/json", "application/ld+json"}:
            value = script.strip()
            if value:
                blocks.append(value)
            continue
        for match in _ASSIGNMENT.finditer(script):
            value = balanced_value(script, match.start(2))
            if value and len(value) >= 40:
                blocks.append(f"const {match.group(1)} = {value};")
    return blocks


def extract(source: Path) -> str:
    parser = PageParser()
    parser.feed(source.read_text(encoding="utf-8", errors="replace"))
    visible = "\n".join(parser.visible).strip()
    blocks = embedded_data(parser.scripts)
    data_text = "\n\n".join(blocks)
    sparse = len(visible) < 500 and len(data_text) > max(80, len(visible) * 2)
    if sparse:
        return f"{visible}\n\n## Embedded JavaScript data\n\n{data_text}\n"
    return visible + "\n"


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: extract_html.py <source.html> <output.txt>", file=sys.stderr)
        return 1
    source, output = map(Path, sys.argv[1:])
    text = extract(source)
    if not text.strip():
        print("HTML extract produced no readable text.", file=sys.stderr)
        return 2
    output.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
