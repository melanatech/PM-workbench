#!/usr/bin/env python3
"""Number-consistency gate for external artifacts (HTML / markdown).

Usage:
  python3 scripts/check_number_consistency.py \\
    --ledger path/to/number-ledger.md \\
    [--source path/to/result.csv ...] \\
    artifact.html artifact-slack.md

What this script detects:
  - Every candidate count/percent in artifact visible text appears in the
    ledger markdown and/or a source file (saved query result or supplement).
    Digit strings are compared after stripping commas.
  - Prints each number with a short context line for the human/agent
    population and nearby-distinction pass.

Sources (preferred for hooks + manual):
  Declare saved-result paths in the ledger under a ``## Gate sources`` heading
  (markdown list or one path per line). The script loads those automatically,
  so ``--ledger <ledger> <artifact>`` matches a full manual run. Extra
  ``--source`` flags still append.

What it does not detect (agent must still do these):
  - Conflicting population labels on the same digit.
  - Missing nearby distinctions between comparable counts.
  - Whether a ratio's denominator is named in prose.

Skips (noise, not metrics): day-of-month next to a month name (``Oct 5`` or
``5 Oct``); lone chart-axis round scales are still checked unless they appear
in ledger/sources.

Exit 0 = every extracted number is traced. Exit 1 = untraced number(s).
Exit 2 = usage error. Stdlib only.
"""
from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

_MIN_ABS = 3
_NUM_RE = re.compile(
    r"(?<![\w./-])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{4,}|\d{1,3})(?![\w./-])"
)
_MONTH = (
    r"(?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
)
_DAY_AFTER_MONTH = re.compile(_MONTH + r"\s+$", re.I)
_DAY_BEFORE_MONTH = re.compile(r"^\s*" + _MONTH + r"\b", re.I)
_GATE_SOURCES_HEADING = re.compile(
    r"^#{1,3}\s+Gate sources\b.*$", re.I | re.M
)
_SKIP_TAGS = {"script", "style"}


class _VisibleText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attr = {k.lower(): (v or "") for k, v in attrs}
            chart = attr.get("type") == "application/json" or attr.get("id", "").startswith("chart-data")
            if not chart:
                self._skip += 1
            return
        if tag in _SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in _SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _artifact_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".html", ".htm"}:
        p = _VisibleText()
        p.feed(raw)
        return " ".join(p.parts)
    # Slack drafts: drop the workbench "draft, do not post" header line only.
    lines = raw.splitlines()
    if lines and lines[0].strip().lower().startswith("draft,"):
        raw = "\n".join(lines[1:])
    return raw


def _norm(token: str) -> str:
    return token.replace(",", "")


def _is_day_of_month(text: str, start: int, display: str) -> bool:
    if "." in display or "," in display:
        return False
    if not display.isdigit() or not (1 <= int(display) <= 31):
        return False
    prefix = text[max(0, start - 16) : start]
    if _DAY_AFTER_MONTH.search(prefix):
        return True
    suffix = text[start + len(display) : start + len(display) + 16]
    if _DAY_BEFORE_MONTH.search(suffix):
        return True
    # Chart axis tick runs: "10 11 12 13 14" (day numbers only).
    window = text[max(0, start - 24) : start + len(display) + 24]
    if re.search(r"(?:\b\d{1,2}\s+){3,}\d{1,2}(?:\s+\d{1,2}){2,}", window):
        return True
    return False


def _parse_gate_sources(ledger_text: str) -> list[Path]:
    """Paths listed under ``## Gate sources`` in the ledger (workspace-relative or absolute).

    Accepts markdown list items (``- path`` / ``* path``), bare paths, or
    backtick-wrapped paths. Stops at the next markdown heading. Resolves
    relative paths against the process cwd (project root when hooks/agents run).
    """
    m = _GATE_SOURCES_HEADING.search(ledger_text)
    if not m:
        return []
    rest = ledger_text[m.end() :]
    next_h = re.search(r"^#{1,3}\s+\S", rest, re.M)
    body = rest[: next_h.start()] if next_h else rest
    out: list[Path] = []
    seen: set[str] = set()
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("<!--"):
            continue
        if s.startswith("|") or s.startswith("```"):
            continue
        # Strip list markers and trailing commentary after path.
        s = re.sub(r"^[-*+]\s+", "", s)
        s = re.sub(r"^\d+\.\s+", "", s)
        # First path-like token; allow backticks.
        token_m = re.match(r"`([^`]+)`|(\S+)", s)
        if not token_m:
            continue
        token = (token_m.group(1) or token_m.group(2) or "").strip().rstrip(".,;")
        if not token or token.lower().startswith("path"):
            continue
        # Skip prose lines that are not paths.
        if " " in token and not token.startswith("/") and "/" not in token:
            continue
        if not re.search(r"[./]", token) and not Path(token).suffix:
            continue
        p = Path(token)
        if not p.is_absolute():
            p = Path.cwd() / p
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _extract(text: str) -> list[tuple[str, str, int]]:
    out: list[tuple[str, str, int]] = []
    for m in _NUM_RE.finditer(text):
        display = m.group(1)
        if _is_day_of_month(text, m.start(), display):
            continue
        norm = _norm(display)
        try:
            val = float(norm)
        except ValueError:
            continue
        if abs(val) < _MIN_ABS and "." not in norm:
            continue
        out.append((display, norm, m.start()))
    return out


def _context(text: str, start: int, width: int = 56) -> str:
    a = max(0, start - width // 3)
    b = min(len(text), start + width)
    return re.sub(r"\s+", " ", text[a:b]).strip()


def _collect_norms(text: str) -> set[str]:
    """Extract digit tokens; also split slash-joined pairs like ``1307/449``."""
    norms = {_norm(m.group(1)) for m in _NUM_RE.finditer(text)}
    # Ledger tables often write all/PS as 1307/449 — slash blocks _NUM_RE.
    for a, b in re.findall(
        r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d{4,}|\d{1,3})/(\d{1,3}(?:,\d{3})+|\d{4,}|\d{1,3})(?![\w.])",
        text,
    ):
        norms.add(_norm(a))
        norms.add(_norm(b))
    return norms


def _collect_norms_from_path(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    # CSV commas are field separators, not thousand markers — split fields first.
    if path.suffix.lower() == ".csv":
        norms: set[str] = set()
        for line in text.splitlines():
            for field in line.split(","):
                field = field.strip().strip('"')
                norms |= _collect_norms(field)
        return norms
    return _collect_norms(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ledger", required=True, type=Path)
    ap.add_argument(
        "--source",
        action="append",
        default=[],
        type=Path,
        help="Saved result CSV/MD whose numbers also count as traced (repeatable; "
        "usually unnecessary when the ledger has a Gate sources section)",
    )
    ap.add_argument("artifacts", nargs="+", type=Path)
    args = ap.parse_args(argv)

    if not args.ledger.is_file():
        print(f"ERROR: ledger not found: {args.ledger}", file=sys.stderr)
        return 2

    ledger_text = args.ledger.read_text(encoding="utf-8")
    ledger_sources = _parse_gate_sources(ledger_text)
    # CLI --source appends; Gate sources are the default shared set.
    all_sources: list[Path] = []
    seen_src: set[str] = set()
    for src in ledger_sources + list(args.source):
        key = str(src.resolve()) if src.exists() else str(src)
        if key in seen_src:
            continue
        seen_src.add(key)
        all_sources.append(src)

    traced = _collect_norms(ledger_text)
    for src in all_sources:
        if not src.is_file():
            print(f"ERROR: source not found: {src}", file=sys.stderr)
            return 2
        traced |= _collect_norms_from_path(src)

    if not traced:
        print("ERROR: no numbers found in ledger/sources", file=sys.stderr)
        return 2

    print(
        f"Traced token set: {len(traced)} "
        f"(ledger={args.ledger.name}, "
        f"gate_sources={len(ledger_sources)}, cli_sources={len(args.source)})"
    )
    print(
        "Population labels and nearby distinctions: human/agent pass on "
        "context lines below. This script fails only on untraced numbers."
    )
    print()

    missing: list[str] = []
    for art in args.artifacts:
        if not art.is_file():
            print(f"ERROR: artifact not found: {art}", file=sys.stderr)
            return 2
        text = _artifact_text(art)
        found = _extract(text)
        print(f"== {art} ({len(found)} candidate numbers) ==")
        seen: set[str] = set()
        for display, norm, start in found:
            ctx = _context(text, start)
            key = f"{norm}|{ctx}"
            if key in seen:
                continue
            seen.add(key)
            ok = norm in traced
            mark = "OK" if ok else "MISSING"
            print(f"  [{mark}] {display:>10}  |  {ctx}")
            if not ok:
                missing.append(f"{art}: {display} — {ctx}")
        print()

    if missing:
        print(f"FAIL: {len(missing)} number(s) not traced to ledger/sources:")
        for line in missing:
            print(f"  - {line}")
        return 1

    print(
        "PASS: every extracted artifact number appears in the ledger or source files."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
