#!/usr/bin/env python3
"""Save the current clipboard (or stdin text) into the live workspace inbox/.

Resolves the live root the same way as pull_clips.py (PM_LIVE_ROOT,
~/.pm-workbench/live-root, else the kit next to this script). Used by:
  - macOS: Cocoa NSServices app from install_clipboard_service.sh (right-click)
  - macOS fallback: Capture Clipboard.command
  - any OS: python3 scripts/capture_clipboard.py --gui (copy text first)

Windows has no macOS-style Services menu for selected text in Slack/etc.
Copy, then run this script (or paste into Claude Code). Chrome uses the
Workbench Clipper on both platforms.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone

# Reuse live-root resolution from the clipper bridge.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pull_clips import resolve_live_root  # noqa: E402

CATEGORIES = [
    ("discovery", "Discovery signal (customer / support / feedback)"),
    ("meetings", "Meeting notes / summary"),
    ("slack", "Slack communication"),
    ("captures", "Just capture it (classify later)"),
    ("competitive", "Competitive"),
    ("documents", "Internal document"),
    ("metrics", "Metric / dashboard reading"),
]

CATEGORY_IDS = {c[0] for c in CATEGORIES}


def read_clipboard() -> str:
    if sys.platform == "darwin":
        try:
            out = subprocess.check_output(["pbpaste"], stderr=subprocess.DEVNULL)
            return out.decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
    if sys.platform == "win32":
        try:
            # PowerShell Get-Clipboard
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"],
                stderr=subprocess.DEVNULL,
            )
            return out.decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""
    # Linux: try xclip / xsel
    for cmd in (["xclip", "-selection", "clipboard", "-o"], ["xsel", "--clipboard", "--output"]):
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
            return out.decode("utf-8", errors="replace")
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    return ""


def choose_category_gui() -> str | None:
    """macOS choose-from-list; returns category id or None if cancelled."""
    if sys.platform != "darwin":
        return None
    labels = [c[1] for c in CATEGORIES]
    # AppleScript list
    listed = ", ".join(f'"{label}"' for label in labels)
    script = f'''
set theChoices to {{{listed}}}
set thePick to choose from list theChoices with prompt "Save clipboard to PM Workbench as:" default items {{"{dict(CATEGORIES)['captures']}"}}
if thePick is false then
    return ""
end if
return item 1 of thePick
'''
    try:
        out = subprocess.check_output(["osascript", "-e", script], stderr=subprocess.DEVNULL)
        picked = out.decode("utf-8").strip()
    except subprocess.CalledProcessError:
        return None
    if not picked:
        return None
    for cid, label in CATEGORIES:
        if label == picked:
            return cid
    return None


def choose_category_tty() -> str | None:
    print("Save to PM Workbench as:")
    for i, (cid, label) in enumerate(CATEGORIES, 1):
        print(f"  {i}) {label}")
    try:
        raw = input(f"Category [1-{len(CATEGORIES)}]: ").strip()
    except EOFError:
        return None
    if raw.isdigit() and 1 <= int(raw) <= len(CATEGORIES):
        return CATEGORIES[int(raw) - 1][0]
    if raw in CATEGORY_IDS:
        return raw
    return None


def write_capture(live_root: str, category: str, body: str, *, title: str = "", source_url: str = "") -> str:
    if category not in CATEGORY_IDS:
        raise ValueError(f"unknown category: {category}")
    text = (body or "").strip()
    if not text:
        raise ValueError("clipboard / input is empty")

    dest_dir = os.path.join(live_root, "inbox", category)
    os.makedirs(dest_dir, exist_ok=True)
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H-%M-%S")
    slug = (title or "clipboard").lower()
    slug = "".join(ch if ch.isalnum() else "-" for ch in slug).strip("-")[:40] or "clipboard"
    path = os.path.join(dest_dir, f"{stamp}-{slug}.md")
    # uniquify
    n = 1
    base, ext = os.path.splitext(path)
    while os.path.exists(path):
        path = f"{base}-{n}{ext}"
        n += 1

    front = [
        "---",
        f"captured: {now.isoformat().replace('+00:00', 'Z')}",
        f"category: {category}",
        f"title: {(title or 'Clipboard capture').replace(chr(10), ' ')}",
        f"source_url: {source_url}",
        "capture_kind: clipboard",
        "extract_source: clipboard",
        "access_path: PM Workbench clipboard capture — text the PM copied from a desktop app (Slack, Mail, etc.); not fetched by the model",
        f"landing: {live_root}/inbox/{category}/",
        "---",
        "",
        text,
        "",
    ]
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(front))
    return path


def notify(message: str) -> None:
    if sys.platform != "darwin":
        return
    try:
        subprocess.run(
            ["osascript", "-e", f'display notification {message!r} with title "PM Workbench"'],
            check=False,
            capture_output=True,
            timeout=5,
        )
    except Exception:
        pass


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", help="live workspace root")
    parser.add_argument("--category", choices=sorted(CATEGORY_IDS), help="inbox category")
    parser.add_argument("--title", default="", help="optional short title")
    parser.add_argument("--source-url", default="", help="optional source URL")
    parser.add_argument("--gui", action="store_true", help="use macOS category picker when category omitted")
    parser.add_argument("--stdin", action="store_true", help="read body from stdin instead of clipboard")
    args = parser.parse_args(argv)

    live = resolve_live_root(args.root)
    if args.stdin or not sys.stdin.isatty():
        # Service often pipes selected text on stdin; prefer that when present.
        if args.stdin:
            body = sys.stdin.read()
        else:
            piped = sys.stdin.read() if not sys.stdin.isatty() else ""
            body = piped if piped.strip() else read_clipboard()
    else:
        body = read_clipboard()

    if not (body or "").strip():
        msg = "Clipboard is empty — copy something first (Slack, Mail, Notes…)."
        if args.gui and sys.platform == "darwin":
            subprocess.run(["osascript", "-e", f'display alert "PM Workbench" message {msg!r}'], check=False)
        else:
            print(msg, file=sys.stderr)
        return 1

    category = args.category
    if not category:
        if args.gui:
            category = choose_category_gui() or choose_category_tty()
        else:
            category = choose_category_tty()
    if not category:
        print("Cancelled.", file=sys.stderr)
        return 2

    try:
        path = write_capture(live, category, body, title=args.title, source_url=args.source_url)
    except ValueError as err:
        print(str(err), file=sys.stderr)
        return 1

    rel = os.path.relpath(path, live)
    print(f"Saved: {rel}")
    print(f"(in {live} — process with /capture process-inbox)")
    notify(f"Saved to {rel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
