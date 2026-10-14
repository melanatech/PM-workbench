#!/usr/bin/env python3
"""Check that a prototype's displayed quantities come from one fixture.

Usage (from the live workspace or the kit):
  python3 scripts/check_prototype_data.py <prototype-dir>

Three checks, all reported. Exit 1 if any FAIL, 0 if every check PASSes or
SKIPs, 2 on usage errors.

1. Quantity-like literals in src/**/*.{js,jsx,tsx,html} outside src/data/,
   plus a root index.html when that file exists. A comment containing
   ``quantity-ok`` on the same line, or on the nearest preceding non-empty
   line, allows a genuine constant.
2. ``node src/data/invariants.js`` when that file exists. Node is
   /usr/local/bin/node, then PATH. If node is missing, this check SKIPs
   with a message and does not fail the run.
3. The same ``data-metric`` id rendered in more than one component must use
   the same selector imported from a ``selectors`` module. A literal, a
   different selector, or a local copy fails.

Stdlib only.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

NODE_CANDIDATE = "/usr/local/bin/node"
ALLOW_MARK = "quantity-ok"
SOURCE_EXTS = {".js", ".jsx", ".tsx", ".html"}
SKIP_DIRS = {"node_modules", "dist", "build", "qa-screenshots"}

QNAME = re.compile(
    r"(count|total|totals|sum|score|rating|stock|qty|quantity|amount|"
    r"percent|percentage|duration|points|minutes|hours|days|sessions|"
    r"tickets|tasks|price|cost|balance)$",
    re.I,
)
LAYOUT_ATTRS = {
    "width",
    "height",
    "style",
    "class",
    "classname",
    "id",
    "key",
    "tabindex",
    "rowspan",
    "colspan",
    "span",
    "step",
    "min",
    "max",
    "rows",
    "cols",
    "size",
    "maxlength",
    "minlength",
    "opacity",
    "src",
    "href",
    "role",
    "type",
    "name",
    "htmlfor",
    "for",
    "viewbox",
    "cx",
    "cy",
    "r",
    "x",
    "y",
    "x1",
    "x2",
    "y1",
    "y2",
    "stroke-width",
    "strokewidth",
    "fill",
    "stroke",
    "d",
}
VISIBLE_ATTRS = {
    "title",
    "alt",
    "label",
    "placeholder",
    "aria-label",
    "aria-description",
    "aria-valuetext",
}
CSS_BEFORE = re.compile(
    r"(?:width|height|padding|margin|top|left|right|bottom|gap|flex|opacity|"
    r"font|font-size|font-weight|line-height|z-index|border|radius|inset|"
    r"transition|animation|duration|min-width|max-width|min-height|max-height|"
    r"fontsize|fontweight|lineheight|zindex|minwidth|maxwidth|minheight|maxheight)"
    r"\s*:\s*['\"]?\s*$",
    re.I,
)
NUMBER = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
CURRENCY = re.compile(rf"[$€£]\s?{NUMBER}")
PERCENT = re.compile(r"\b\d+(?:\.\d+)?\s*%")
DURATION = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:milliseconds?|seconds?|minutes?|hours?|days?|weeks?|"
    r"ms|secs?|mins?|hrs?)\b",
    re.I,
)
THOUSANDS = re.compile(r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b")
ISO_DATE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
JSX_TEXT = re.compile(rf"(?<!=)>\s*({NUMBER})\s*<")
JSX_EXPR = re.compile(rf"\{{\s*({NUMBER})\s*\}}")
STRING_NUM = re.compile(rf"""(?P<q>['"`])\s*({NUMBER})\s*(?P=q)""")
NAMED_ASSIGN = re.compile(
    rf"(?<![=!<>])\b([A-Za-z_][\w]*)\s*=\s*({NUMBER})(?!\w)"
)
NAMED_PROP = re.compile(
    rf"(?<![=!<>])\b([A-Za-z_][\w]*)\s*:\s*({NUMBER})(?!\w)"
)
HELPER_ARG = re.compile(rf"\b(?:money|pct|format|sum)\s*\(\s*({NUMBER})")
TEMPLATE_NUM = re.compile(rf"\$\{{\s*({NUMBER})\s*\}}")

IMPORT_NAMED = re.compile(
    r"import\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]",
    re.DOTALL,
)
IMPORT_NS = re.compile(
    r"import\s*\*\s*as\s+(\w+)\s*from\s*['\"]([^'\"]+)['\"]"
)
PAIRED_METRIC = re.compile(
    r"""<(?P<tag>[A-Za-z][\w.]*)\b"""
    r"""(?P<open>[^>]*?\bdata-metric\s*=\s*(?P<q>["'])(?P<id>[^"']+)(?P=q)[^>]*)>"""
    r"""(?P<body>.*?)</(?P=tag)\s*>""",
    re.DOTALL,
)
SELF_METRIC = re.compile(
    r"""<(?P<tag>[A-Za-z][\w.]*)\b"""
    r"""(?P<open>[^>]*?\bdata-metric\s*=\s*(?P<q>["'])(?P<id>[^"']+)(?P=q)[^>]*)/>""",
    re.DOTALL,
)
CALL = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\(")
DOT_CALL = re.compile(
    r"\b([A-Za-z_$][\w$]*)\s*\.\s*([A-Za-z_$][\w$]*)\s*\("
)
IGNORE_CALLS = {
    "format",
    "sum",
    "ratio",
    "assertInvariant",
    "money",
    "pct",
    "String",
    "Number",
    "Boolean",
    "Math",
    "Array",
    "Object",
    "JSON",
    "console",
    "parseInt",
    "parseFloat",
    "Date",
    "document",
    "window",
    "map",
    "filter",
    "reduce",
    "forEach",
    "find",
    "some",
    "every",
    "includes",
    "slice",
    "concat",
    "join",
    "keys",
    "values",
    "entries",
    "toString",
    "toFixed",
    "toLocaleString",
    "push",
    "pop",
    "sort",
    "flat",
    "flatMap",
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "function",
    "return",
}


def resolve_node() -> str | None:
    """Prefer /usr/local/bin/node, then whatever `node` is on PATH."""
    if os.path.isfile(NODE_CANDIDATE) and os.access(NODE_CANDIDATE, os.X_OK):
        return NODE_CANDIDATE
    return shutil.which("node")


def iter_source_files(proto: Path):
    src = proto / "src"
    if src.is_dir():
        for path in sorted(src.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in SOURCE_EXTS:
                continue
            parts = path.relative_to(proto).parts
            if any(part in SKIP_DIRS for part in parts):
                continue
            if len(parts) >= 2 and parts[0] == "src" and parts[1] == "data":
                continue
            yield path
    root_index = proto / "index.html"
    if root_index.is_file():
        yield root_index


def _expand_allow(original: str, comment_lines: set[int]) -> set[int]:
    lines = original.split("\n")
    nonempty = [idx for idx, line in enumerate(lines, start=1) if line.strip()]
    allowed = set(comment_lines)
    for mark_line in comment_lines:
        for idx in nonempty:
            if idx > mark_line:
                allowed.add(idx)
                break
    return allowed


def prepare_source(text: str, html: bool) -> tuple[str, str, set[int]]:
    """Blank comments (and then style) without changing length or newlines.

    Returns comment-blanked text, style-blanked text, and 1-based lines
    covered by a ``quantity-ok`` comment.
    """
    chars = list(text)
    n = len(chars)
    mark_lines: set[int] = set()
    i = 0
    line = 1
    in_script = not html

    def blank_until(start: int, end: int) -> None:
        for k in range(start, min(end, n)):
            if chars[k] != "\n":
                chars[k] = " "

    while i < n:
        ch = chars[i]
        if ch == "\n":
            line += 1
            i += 1
            continue

        if html and not in_script and text.startswith("<script", i):
            end = text.find(">", i)
            if end < 0:
                break
            i = end + 1
            in_script = True
            continue
        if html and in_script and text.startswith("</script", i):
            in_script = False
            i += len("</script")
            continue

        if html and not in_script and text.startswith("<!--", i):
            start_line = line
            j = i + 4
            buf: list[str] = []
            while j < n and not text.startswith("-->", j):
                buf.append(text[j])
                if text[j] == "\n":
                    line += 1
                j += 1
            if ALLOW_MARK in "".join(buf):
                mark_lines.add(start_line)
                mark_lines.add(line)
            end = j + 3 if j < n else j
            blank_until(i, end)
            i = end
            continue

        if not in_script:
            i += 1
            continue

        if ch in ("'", '"', "`"):
            quote = ch
            i += 1
            while i < n:
                if chars[i] == "\\":
                    i += 2
                    continue
                if chars[i] == "\n":
                    line += 1
                    if quote != "`":
                        i += 1
                        break
                if chars[i] == quote:
                    i += 1
                    break
                i += 1
            continue

        if ch == "/" and i + 1 < n and chars[i + 1] == "/":
            if i > 0 and chars[i - 1] == ":":
                i += 2
                continue
            buf = []
            j = i + 2
            while j < n and chars[j] != "\n":
                buf.append(text[j])
                j += 1
            if ALLOW_MARK in "".join(buf):
                mark_lines.add(line)
            blank_until(i, j)
            i = j
            continue

        if ch == "/" and i + 1 < n and chars[i + 1] == "*":
            start_line = line
            buf = []
            j = i + 2
            while j + 1 < n and not (chars[j] == "*" and chars[j + 1] == "/"):
                buf.append(text[j])
                if chars[j] == "\n":
                    line += 1
                j += 1
            end = j + 2 if j + 1 < n else n
            if ALLOW_MARK in "".join(buf):
                mark_lines.add(start_line)
                mark_lines.add(line)
            blank_until(i, end)
            i = end
            continue

        i += 1

    comment_blanked = "".join(chars)
    return comment_blanked, _blank_styles(comment_blanked), _expand_allow(text, mark_lines)


def _blank_styles(text: str) -> str:
    chars = list(text)
    n = len(chars)

    def blank_range(start: int, end: int) -> None:
        for k in range(start, min(end, n)):
            if chars[k] != "\n":
                chars[k] = " "

    for match in re.finditer(r"<style\b[^>]*>.*?</style>", text, flags=re.I | re.DOTALL):
        blank_range(match.start(), match.end())
    for match in re.finditer(
        r"""\bstyle\s*=\s*(["']).*?\1""", text, flags=re.DOTALL
    ):
        blank_range(match.start(), match.end())

    cursor = 0
    while True:
        found = text.find("style={{", cursor)
        if found < 0:
            break
        brace = text.find("{", found)
        depth = 0
        pos = brace
        while pos < n:
            if text[pos] == "{":
                depth += 1
            elif text[pos] == "}":
                depth -= 1
                if depth == 0:
                    pos += 1
                    break
            pos += 1
        blank_range(found, pos)
        cursor = pos
    return "".join(chars)


def _line_col(text: str, index: int) -> tuple[int, int]:
    line = text.count("\n", 0, index) + 1
    last_nl = text.rfind("\n", 0, index)
    col = index + 1 if last_nl < 0 else index - last_nl
    return line, col


def _tag_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "<" and i + 1 < n and (text[i + 1].isalpha() or text[i + 1] in "/!"):
            j = text.find(">", i + 1)
            if j < 0:
                break
            spans.append((i, j + 1))
            i = j + 1
        else:
            i += 1
    return spans


def _span_at(spans: list[tuple[int, int]], pos: int) -> tuple[int, int] | None:
    for start, end in spans:
        if start <= pos < end:
            return start, end
        if start > pos:
            return None
    return None


def _attribute_name(text: str, tag: tuple[int, int], pos: int) -> str | None:
    prefix = text[tag[0] : pos]
    eq = prefix.rfind("=")
    if eq < 0:
        return None
    match = re.search(r"([A-Za-z_:][\w:.-]*)$", prefix[:eq].rstrip())
    if not match:
        return None
    return match.group(1).lower()


def _css_context(text: str, pos: int) -> bool:
    window = text[max(0, pos - 48) : pos]
    return CSS_BEFORE.search(window) is not None


class _Hit:
    def __init__(self, start: int, end: int, snippet: str):
        self.start = start
        self.end = end
        self.snippet = snippet


def _consider(hits: list[_Hit], start: int, end: int, snippet: str) -> None:
    snippet = " ".join(snippet.split())
    if not snippet:
        return
    hits.append(_Hit(start, end, snippet[:80]))


def find_literals(text: str, allowed_lines: set[int]) -> list[tuple[int, int, str]]:
    spans = _tag_spans(text)
    hits: list[_Hit] = []

    def keep_line(start: int) -> bool:
        line, _col = _line_col(text, start)
        return line not in allowed_lines

    for match in CURRENCY.finditer(text):
        if keep_line(match.start()):
            _consider(hits, match.start(), match.end(), match.group(0))
    for match in PERCENT.finditer(text):
        if not keep_line(match.start()) or _css_context(text, match.start()):
            continue
        tag = _span_at(spans, match.start())
        if tag and _attribute_name(text, tag, match.start()) in LAYOUT_ATTRS:
            continue
        _consider(hits, match.start(), match.end(), match.group(0))
    for match in DURATION.finditer(text):
        if not keep_line(match.start()) or _css_context(text, match.start()):
            continue
        _consider(hits, match.start(), match.end(), match.group(0))
    for match in THOUSANDS.finditer(text):
        if keep_line(match.start()):
            _consider(hits, match.start(), match.end(), match.group(0))
    for match in ISO_DATE.finditer(text):
        if keep_line(match.start()):
            _consider(hits, match.start(), match.end(), match.group(0))
    for match in JSX_TEXT.finditer(text):
        if keep_line(match.start(1)):
            _consider(hits, match.start(1), match.end(1), match.group(1))
    for match in JSX_EXPR.finditer(text):
        if not keep_line(match.start(1)) or _span_at(spans, match.start()):
            continue
        _consider(hits, match.start(1), match.end(1), match.group(1))
    for match in STRING_NUM.finditer(text):
        if not keep_line(match.start(2)):
            continue
        tag = _span_at(spans, match.start())
        if tag:
            attr = _attribute_name(text, tag, match.start())
            if attr in LAYOUT_ATTRS or (
                attr and attr not in VISIBLE_ATTRS and not QNAME.search(attr)
            ):
                continue
        _consider(hits, match.start(2), match.end(2), match.group(2))
    for pattern in (NAMED_ASSIGN, NAMED_PROP):
        for match in pattern.finditer(text):
            if not keep_line(match.start()) or not QNAME.search(match.group(1)):
                continue
            if _css_context(text, match.start(2)):
                continue
            _consider(hits, match.start(), match.end(), match.group(0))
    for match in HELPER_ARG.finditer(text):
        if keep_line(match.start(1)):
            _consider(hits, match.start(1), match.end(1), match.group(1))
    for match in TEMPLATE_NUM.finditer(text):
        if keep_line(match.start(1)):
            _consider(hits, match.start(1), match.end(1), match.group(1))

    hits.sort(key=lambda hit: (hit.start, -(hit.end - hit.start)))
    kept: list[_Hit] = []
    last_end = -1
    for hit in hits:
        if hit.start < last_end:
            continue
        kept.append(hit)
        last_end = hit.end

    found = []
    for hit in kept:
        line, col = _line_col(text, hit.start)
        found.append((line, col, hit.snippet))
    found.sort()
    return found


def scan_literals(proto: Path) -> tuple[str, str]:
    files = list(iter_source_files(proto))
    if not (proto / "src").is_dir() and not (proto / "index.html").is_file():
        return (
            "SKIP",
            "SKIP literals — no src/ directory and no root index.html",
        )
    problems = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        _comments, scanned, allowed = prepare_source(
            text, path.suffix.lower() == ".html"
        )
        rel = path.relative_to(proto).as_posix()
        for line, col, snippet in find_literals(scanned, allowed):
            problems.append(f"  {rel}:{line}:{col}: quantity literal {snippet}")
    if problems:
        return "FAIL", "FAIL literals\n" + "\n".join(problems)
    return "PASS", "PASS literals"


def run_invariants(proto: Path, node: str | None) -> tuple[str, str]:
    script = proto / "src" / "data" / "invariants.js"
    if not script.is_file():
        return (
            "SKIP",
            "SKIP invariants — src/data/invariants.js not present",
        )
    if not node:
        return (
            "SKIP",
            "SKIP invariants — node is not available "
            "(looked for /usr/local/bin/node, then PATH). "
            "Install Node and re-run to execute src/data/invariants.js. "
            "This skip is not a pass of the invariants.",
        )
    try:
        proc = subprocess.run(
            [node, "src/data/invariants.js"],
            cwd=proto,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except OSError as exc:
        return "FAIL", f"FAIL invariants\n  could not run node: {exc}"
    if proc.returncode == 0:
        return "PASS", "PASS invariants"
    detail = (proc.stdout or "") + (proc.stderr or "")
    lines = [f"  {line}" for line in detail.strip().splitlines() if line.strip()]
    body = "\n".join(lines) if lines else f"  node exited {proc.returncode}"
    return "FAIL", "FAIL invariants\n" + body


def _selectors_module(spec: str) -> bool:
    base = spec.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    name = base.split("/")[-1]
    for ext in (".js", ".jsx", ".ts", ".tsx"):
        if name.endswith(ext):
            name = name[: -len(ext)]
            break
    return name == "selectors"


def _selector_bindings(text: str) -> tuple[dict[str, str], set[str]]:
    bindings: dict[str, str] = {}
    namespaces: set[str] = set()
    for match in IMPORT_NAMED.finditer(text):
        if not _selectors_module(match.group(2)):
            continue
        for part in match.group(1).split(","):
            part = part.strip()
            if not part or part.startswith("type "):
                continue
            if " as " in part:
                original, alias = [piece.strip() for piece in part.split(" as ", 1)]
                bindings[alias] = original
            else:
                bindings[part] = part
    for match in IMPORT_NS.finditer(text):
        if _selectors_module(match.group(2)):
            namespaces.add(match.group(1))
    return bindings, namespaces


def _metric_source(element: str, bindings: dict[str, str], namespaces: set[str]) -> str:
    selectors: list[str] = []
    locals_: list[str] = []
    dotted = {(m.start(), m.group(1), m.group(2)) for m in DOT_CALL.finditer(element)}
    for _start, namespace, name in sorted(dotted):
        if namespace in namespaces and name not in IGNORE_CALLS:
            selectors.append(name)
    dotted_spans = []
    for match in DOT_CALL.finditer(element):
        dotted_spans.append((match.start(), match.end()))
    for match in CALL.finditer(element):
        if any(start <= match.start() < end for start, end in dotted_spans):
            continue
        name = match.group(1)
        if name in bindings:
            selectors.append(bindings[name])
        elif name not in IGNORE_CALLS:
            locals_.append(name)
    if selectors:
        return "selector:" + "+".join(sorted(set(selectors)))
    if locals_:
        return "local:" + "+".join(sorted(set(locals_)))
    _comments, scanned, _allowed = prepare_source(element, html=False)
    if find_literals(scanned, set()):
        return "literal"
    return "unspecified"


def _occurrences(text: str) -> list[tuple[str, int, str]]:
    found = []
    seen = set()
    for pattern in (PAIRED_METRIC, SELF_METRIC):
        for match in pattern.finditer(text):
            if match.start() in seen:
                continue
            seen.add(match.start())
            element = match.group("open") + match.groupdict().get("body", "")
            line, _col = _line_col(text, match.start())
            found.append((match.group("id"), line, element))
    return found


def scan_cross_screen(proto: Path) -> tuple[str, str]:
    files = list(iter_source_files(proto))
    if not files:
        return (
            "SKIP",
            "SKIP cross-screen — no component files to compare",
        )
    by_metric: dict[str, list[tuple[str, int, str]]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        comment_blanked, _styled, _allowed = prepare_source(
            text, path.suffix.lower() == ".html"
        )
        bindings, namespaces = _selector_bindings(comment_blanked)
        rel = path.relative_to(proto).as_posix()
        for metric_id, line, element in _occurrences(comment_blanked):
            source = _metric_source(element, bindings, namespaces)
            by_metric.setdefault(metric_id, []).append((rel, line, source))

    problems = []
    for metric_id in sorted(by_metric):
        sites = by_metric[metric_id]
        files_hit = {rel for rel, _line, _source in sites}
        if len(files_hit) < 2:
            continue
        sources = [source for _rel, _line, source in sites]
        agreed = (
            sources[0].startswith("selector:")
            and all(source == sources[0] for source in sources)
        )
        if agreed:
            continue
        rows = [f'  metric "{metric_id}" uses different selectors or copies:']
        for rel, line, source in sites:
            label = _source_label(source)
            rows.append(f"    {rel}:{line}: {label}")
        problems.append("\n".join(rows))
    if problems:
        return "FAIL", "FAIL cross-screen\n" + "\n".join(problems)
    return "PASS", "PASS cross-screen"


def _source_label(source: str) -> str:
    if source.startswith("selector:"):
        return "selector " + source.split(":", 1)[1]
    if source.startswith("local:"):
        return "local copy " + source.split(":", 1)[1]
    if source == "literal":
        return "literal"
    return "no selector"


def run(proto: Path) -> tuple[int, str]:
    if not proto.is_dir():
        return 2, f"not a directory: {proto}"
    sections = [
        scan_literals(proto)[1],
        run_invariants(proto, resolve_node())[1],
        scan_cross_screen(proto)[1],
    ]
    failed = any(section.startswith("FAIL") for section in sections)
    lines = [f"check_prototype_data: {proto}"]
    lines.extend(sections)
    lines.append("result: fail" if failed else "result: pass")
    return (1 if failed else 0), "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check prototype quantities against one fixture of raw records."
    )
    parser.add_argument("prototype_dir", help="Path to the prototype directory")
    args = parser.parse_args(argv)
    code, report = run(Path(args.prototype_dir).resolve())
    stream = sys.stderr if code == 2 else sys.stdout
    stream.write(report)
    if code == 2 and not report.endswith("\n"):
        stream.write("\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
