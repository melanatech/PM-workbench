#!/usr/bin/env python3
"""Run an approved /todo dispatch plan with parallel ``claude -p`` workers.

Each worker writes only its own draft under ``outputs/todo-drafts/``.
Up to 5 run at once. Register updates are not done here: ``todo_register.py``
holds ``state/todo-register.lock`` for the whole read-modify-write, so if a
worker (or a later ``update``) touches the register, those writes serialize.

``claude -p`` uses the Claude Code login from the panel. Complete ``/login``
in the Claude Code panel before the first headless run; otherwise the CLI
prints "Not logged in" and this script reports that instead of writing drafts.

Usage (from the live workspace):
  python3 scripts/dispatch_todos.py outputs/todo-drafts/2026-10-14-dispatch-plan.md
  python3 scripts/dispatch_todos.py PLAN --unattended
  python3 scripts/dispatch_todos.py PLAN --yes --max 5 --claude ~/.local/bin/claude
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

FENCE = re.compile(r"```todo-plan\s*\n(.*?)\n```", re.S)
APPROVED_LINE = re.compile(r"(?m)^Approved:\s*yes\s*$", re.I)
MAX_DEFAULT = 5


def resolve_claude(explicit: str = "") -> str:
    if explicit:
        candidate = Path(os.path.expanduser(explicit))
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
        found = shutil.which(explicit)
        return found or ""
    local = Path.home() / ".local" / "bin" / "claude"
    if local.is_file() and os.access(local, os.X_OK):
        return str(local)
    env = (os.environ.get("CLAUDE_BIN") or "claude").strip()
    if os.path.isfile(env) and os.access(env, os.X_OK):
        return env
    return shutil.which(env) or ""


def load_plan(path: Path) -> tuple[str, dict]:
    text = path.read_text(encoding="utf-8")
    match = FENCE.search(text)
    if not match:
        raise SystemExit(f"dispatch: {path} has no ```todo-plan fence")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as error:
        raise SystemExit(f"dispatch: plan JSON is invalid: {error}")
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise SystemExit("dispatch: plan JSON needs an items list")
    return text, payload


def plan_approved(text: str, payload: dict, force: bool) -> bool:
    if force:
        return True
    if APPROVED_LINE.search(text):
        return True
    return bool(payload.get("approved"))


def register_notes(root: Path) -> dict[str, dict[str, str]]:
    path = root / "registers" / "todos.csv"
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8", newline="") as handle:
        return {row.get("id") or "": row for row in csv.DictReader(handle)}


def worker_prompt(item: dict, row: dict[str, str], today: str) -> str:
    files = item.get("files") or []
    file_lines = "\n".join(f"- {path}" for path in files) or "- (none listed)"
    note = (row.get("note") or item.get("note") or "").strip()
    links = (row.get("links") or item.get("links") or "").strip()
    description = (row.get("description") or item.get("description") or "").strip()
    output = item.get("output") or ""
    return (
        "You are the pm-workbench todo-worker in work mode. "
        "You write one draft file and nothing else.\n"
        f"Today: {today}\n"
        f"To-do {item.get('id')}: {description}\n"
        f"Deliverable: {item.get('deliverable') or 'analysis'}\n"
        f"Links: {links or '(none)'}\n"
        f"Note: {note or '(none)'}\n"
        "Read only these files, at most 12:\n"
        f"{file_lines}\n"
        "Write the draft to this path and nowhere else. Do not edit "
        "registers/todos.csv, do not write any other to-do's draft, and do not "
        "send, post, or contact anyone.\n"
        f"OUTPUT_PATH: {output}\n"
        "The draft starts with the line `DRAFT — not sent`. "
        "If a fact is missing, put `[NEEDS INPUT: ...]` at the top and still "
        "write a provisional draft.\n"
    )


def select_items(payload: dict, *, unattended: bool, limit: int) -> tuple[list[dict], list[dict]]:
    chosen = []
    skipped = []
    for item in payload.get("items") or []:
        gaps = item.get("gaps") or []
        if unattended and gaps:
            skipped.append(item)
            continue
        chosen.append(item)
        if len(chosen) >= limit:
            break
    return chosen, skipped


def run_workers(
    items: list[dict],
    *,
    root: Path,
    claude: str,
    timeout: int,
) -> list[dict]:
    """Start every worker before waiting, so they run concurrently."""
    notes = register_notes(root)
    today = date.today().isoformat()
    running: list[tuple[dict, subprocess.Popen]] = []
    for item in items:
        output = root / (item.get("output") or "")
        output.parent.mkdir(parents=True, exist_ok=True)
        prompt = worker_prompt(item, notes.get(item.get("id") or "", {}), today)
        proc = subprocess.Popen(
            [claude, "-p", prompt, "--permission-mode", "dontAsk"],
            cwd=str(root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        running.append((item, proc))
    results = []
    for item, proc in running:
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            code = 124
        else:
            code = proc.returncode
        blob = f"{stderr or ''}\n{stdout or ''}"
        login = "not logged in" in blob.lower()
        output = root / (item.get("output") or "")
        results.append({
            "id": item.get("id") or "",
            "output": item.get("output") or "",
            "returncode": code,
            "login_required": login,
            "wrote": output.is_file(),
            "stderr": (stderr or "")[:400],
        })
    return results


def write_sweep_summary(root: Path, plan_date: str, results: list[dict], skipped: list[dict]) -> Path:
    path = root / "outputs" / "todo-drafts" / f"{plan_date}-sweep.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Sweep {plan_date}",
        "",
        "Unattended: drafts only where the plan had no gaps. Status was not changed.",
        "",
        "| id | draft | result |",
        "|---|---|---|",
    ]
    for result in results:
        status = "wrote" if result["wrote"] else f"failed ({result['returncode']})"
        lines.append(f"| {result['id']} | {result['output']} | {status} |")
    for item in skipped:
        lines.append(f"| {item.get('id')} | {item.get('output') or '—'} | skipped (gaps) |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", help="path to the dispatch plan markdown")
    parser.add_argument("--root", default=".", help="live workspace root (default: cwd)")
    parser.add_argument("--yes", action="store_true", help="dispatch even if the plan is not marked approved")
    parser.add_argument(
        "--unattended",
        action="store_true",
        help="nobody to approve: draft only items with no gaps; do not change status",
    )
    parser.add_argument("--max", type=int, default=MAX_DEFAULT, help="parallel workers (default 5)")
    parser.add_argument("--claude", default="", help="claude binary (default: ~/.local/bin/claude)")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    plan_path = Path(args.plan)
    if not plan_path.is_file():
        plan_path = root / args.plan
    if not plan_path.is_file():
        print(f"dispatch: plan not found: {args.plan}", file=sys.stderr)
        return 2
    text, payload = load_plan(plan_path)
    if args.max < 1:
        print("dispatch: --max must be at least 1", file=sys.stderr)
        return 2
    limit = min(args.max, MAX_DEFAULT) if args.max > MAX_DEFAULT else args.max
    if args.max > MAX_DEFAULT:
        print(f"dispatch: capping parallel workers at {MAX_DEFAULT}")
        limit = MAX_DEFAULT
    if not plan_approved(text, payload, force=args.yes or args.unattended):
        print("dispatch: plan is not approved. Set `Approved: yes` or pass --yes.", file=sys.stderr)
        print("Unattended sweep passes --unattended and drafts only items with no gaps.", file=sys.stderr)
        return 1
    items, skipped = select_items(payload, unattended=args.unattended, limit=limit)
    if not items and not skipped:
        print("dispatch: plan has no items")
        return 1
    if not items:
        print(f"dispatch: no items without gaps ({len(skipped)} skipped)")
        if (payload.get("mode") == "sweep") or args.unattended:
            summary = write_sweep_summary(root, payload.get("date") or date.today().isoformat(), [], skipped)
            print(f"sweep_summary={summary.relative_to(root)}")
        return 0
    claude = resolve_claude(args.claude)
    if not claude:
        print(
            "dispatch: claude CLI not found. Install it or pass --claude ~/.local/bin/claude. "
            "`claude -p` also needs /login in the Claude Code panel first.",
            file=sys.stderr,
        )
        return 2
    results = run_workers(items, root=root, claude=claude, timeout=args.timeout)
    failed = [result for result in results if result["returncode"] != 0 or not result["wrote"]]
    login = [result for result in results if result["login_required"]]
    print(f"dispatched={len(results)} failed={len(failed)} skipped_gaps={len(skipped)}")
    for result in results:
        state = "wrote" if result["wrote"] and result["returncode"] == 0 else "failed"
        print(f"  {result['id']} {state} {result['output']}")
    if login:
        print(
            "claude -p is not logged in. Run /login in the Claude Code panel, then retry. "
            "See .claude/CLAUDE.local.md.",
            file=sys.stderr,
        )
    if (payload.get("mode") == "sweep") or args.unattended:
        summary = write_sweep_summary(root, payload.get("date") or date.today().isoformat(), results, skipped)
        print(f"sweep_summary={summary.relative_to(root)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
