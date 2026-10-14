#!/usr/bin/env python3
"""Git metadata for repos/: keys on the default branch, a cursor, a snapshot.

Reads key prefixes from reference/context/systems-map.md when the workspace
has one, otherwise systems-map.example.md. Bracket placeholders are not
prefixes. Does not read source files. If fetch fails or there is no remote,
uses the local log and says so.

  python3 scripts/repo_activity.py --root <live> [--since YYYY-MM-DD]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

DEFAULT_WINDOW_DAYS = 14
STALE_DAYS = 7
PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
OPEN_STATUSES = {"to do", "todo", "in progress"}
IN_PROGRESS = {"in progress"}
DONE_STATUSES = {"done", "complete", "completed", "closed"}

_LOG_FORMAT = "%H%x1f%cI%x1f%P%x1f%s%x1f%b%x1e"


def parse_systems_map(text: str) -> dict:
    """Return prefixes and pair groups from a systems-map markdown table."""
    rows = _ticket_rows(text or "")
    prefixes: list[str] = []
    for row in rows:
        prefix = (row.get("key prefix") or "").strip()
        if PREFIX_RE.fullmatch(prefix) and prefix not in prefixes:
            prefixes.append(prefix)
    return {"prefixes": prefixes, "pairs": _pair_groups(rows, prefixes), "rows": rows}


def extract_keys(text: str, prefixes: list[str]) -> list[str]:
    if not text or not prefixes:
        return []
    pattern = re.compile(
        r"\b(" + "|".join(re.escape(prefix) for prefix in prefixes) + r")-(\d+)\b"
    )
    found: list[str] = []
    for match in pattern.finditer(text):
        key = f"{match.group(1)}-{match.group(2)}"
        if key not in found:
            found.append(key)
    return found


def locate_systems_map(root: Path) -> tuple[str, str]:
    """Prefer the workspace map. Fall back to the kit example."""
    live = root / "reference" / "context" / "systems-map.md"
    example = root / "reference" / "context" / "systems-map.example.md"
    if live.is_file():
        return "reference/context/systems-map.md", live.read_text(encoding="utf-8")
    if example.is_file():
        return "reference/context/systems-map.example.md", example.read_text(encoding="utf-8")
    return "", ""


def code_vs_board(
    activity: dict,
    tickets: list[dict],
    *,
    stale_days: int = STALE_DAYS,
    today: date | None = None,
) -> list[dict]:
    """Four Tier 2 drift checks. Local proposals only; nothing is written to a tracker.

    1. merged_but_open — To Do or In Progress, but a default-branch commit names the key.
    2. stale_in_progress — In Progress with no commit in stale_days.
    3. key_not_on_board — a key in a commit (or branch name) is absent from the board.
    4. done_without_commits — Done with no commits (low priority; may be non-code work).
    """
    if not tickets:
        return []
    today = today or date.today()
    by_key: dict[str, list[dict]] = {}
    for commit in activity.get("commits") or []:
        for key in commit.get("keys") or []:
            by_key.setdefault(key, []).append(commit)
    branch_only = []
    for branch in activity.get("branch_keys") or []:
        for key in branch.get("keys") or []:
            if key not in by_key:
                branch_only.append((key, branch))

    board_keys = {(ticket.get("key") or "").strip() for ticket in tickets}
    board_keys.discard("")
    checks: list[dict] = []

    for ticket in tickets:
        key = (ticket.get("key") or "").strip()
        if not key:
            continue
        status = _norm_status(ticket.get("status"))
        commits = by_key.get(key) or []
        merged = [item for item in commits if item.get("on_default_branch")]
        if status in OPEN_STATUSES and merged:
            latest = max(merged, key=lambda item: item.get("date") or "")
            checks.append(
                _drift(
                    "merged_but_open",
                    key,
                    "normal",
                    f"{latest.get('repo')}@{_short(latest.get('sha'))} on the default branch "
                    f"({latest.get('date')}); board status {ticket.get('status')}",
                )
            )
        if status in IN_PROGRESS:
            dates = [_as_date(item.get("date")) for item in commits]
            dates = [item for item in dates if item]
            latest_date = max(dates) if dates else None
            if latest_date is None or (today - latest_date).days > stale_days:
                if latest_date is None:
                    evidence = (
                        f"no commits naming {key} in the scanned window; "
                        f"In Progress with none in {stale_days} days"
                    )
                else:
                    evidence = (
                        f"latest commit naming {key} is {latest_date.isoformat()}, "
                        f"more than {stale_days} days before {today.isoformat()}"
                    )
                checks.append(_drift("stale_in_progress", key, "normal", evidence))
        if status in DONE_STATUSES and not commits:
            checks.append(
                _drift(
                    "done_without_commits",
                    key,
                    "low",
                    f"{key} is {ticket.get('status')} and no commit in the scan names it; "
                    "may be non-code work",
                )
            )

    seen = {item["key"] for item in checks if item["check"] == "key_not_on_board"}
    for key, commits in sorted(by_key.items()):
        if key in board_keys or key in seen:
            continue
        latest = max(commits, key=lambda item: item.get("date") or "")
        checks.append(
            _drift(
                "key_not_on_board",
                key,
                "normal",
                f"{latest.get('repo')}@{_short(latest.get('sha'))} names {key}; "
                "the key is not on the board snapshot",
            )
        )
        seen.add(key)
    for key, branch in branch_only:
        if key in board_keys or key in seen:
            continue
        checks.append(
            _drift(
                "key_not_on_board",
                key,
                "normal",
                f"branch {branch.get('branch')} in {branch.get('repo')} names {key}; "
                "the key is not on the board snapshot",
            )
        )
    return checks


def run_activity(
    root: Path,
    *,
    since: str | None = None,
    today: date | None = None,
    stale_days: int = STALE_DAYS,
    tickets: list[dict] | None = None,
    fetch: bool = True,
) -> dict:
    """Scan repos/, write the snapshot and cursor, and return the snapshot."""
    root = Path(root)
    today = today or datetime.now(timezone.utc).date()
    since_value, since_source = _resolve_since(root, since, today)
    source_rel, map_text = locate_systems_map(root)
    parsed = parse_systems_map(map_text)
    prefixes = parsed["prefixes"]
    prefix_note = ""
    if not prefixes:
        prefix_note = (
            "systems-map has no real key prefixes (placeholders are skipped); no keys parsed"
        )

    repos_dir = root / "repos"
    repo_reports = []
    commits: list[dict] = []
    branch_keys: list[dict] = []
    for name, worktree in _discover_repos(repos_dir):
        fetch_info = (
            _fetch(worktree, since_value) if fetch else {"fetch": "skipped", "note": "fetch disabled"}
        )
        branch = _default_branch(worktree)
        repo_commits = _log_commits(worktree, name, branch, since_value, prefixes, on_default=True)
        commits.extend(repo_commits)
        for other in _local_branches(worktree):
            if other == branch:
                continue
            named = extract_keys(other, prefixes)
            if named:
                branch_keys.append({"repo": f"repos/{name}", "branch": other, "keys": named})
            commits.extend(
                _log_commits(
                    worktree,
                    name,
                    other,
                    since_value,
                    prefixes,
                    on_default=False,
                    exclude_branch=branch,
                )
            )
        repo_reports.append(
            {
                "name": name,
                "path": f"repos/{name}",
                "default_branch": branch,
                "fetch": fetch_info["fetch"],
                "note": fetch_info["note"],
            }
        )

    snapshot = {
        "generated": today.isoformat(),
        "since": since_value,
        "since_source": since_source,
        "prefixes": prefixes,
        "prefix_source": source_rel,
        "prefix_note": prefix_note,
        "pairs": [list(pair) for pair in parsed["pairs"]],
        "repos": repo_reports,
        "commits": commits,
        "branch_keys": branch_keys,
    }
    if tickets is not None:
        snapshot["drift"] = {
            "stale_days": stale_days,
            "tier": 2,
            "checks": code_vs_board(snapshot, tickets, stale_days=stale_days, today=today),
        }

    out_dir = root / "state" / "repo-activity"
    out_dir.mkdir(parents=True, exist_ok=True)
    rel = f"state/repo-activity/{today.isoformat()}.json"
    path = root / rel
    path.write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")
    cursor = {
        "since": today.isoformat(),
        "snapshot": rel,
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / "repo-activity-cursor.json").write_text(
        json.dumps(cursor, indent=2) + "\n", encoding="utf-8"
    )
    snapshot["snapshot"] = rel
    return snapshot


def _drift(check: str, key: str, priority: str, evidence: str) -> dict:
    return {
        "check": check,
        "key": key,
        "tier": 2,
        "priority": priority,
        "batch": "code-vs-board",
        "evidence": evidence,
        "tracker_write": False,
    }


def _norm_status(status: str | None) -> str:
    return re.sub(r"\s+", " ", (status or "").strip().lower())


def _as_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _short(sha: str | None) -> str:
    return (sha or "")[:12]


def _ticket_rows(text: str) -> list[dict]:
    rows: list[dict] = []
    header: list[str] | None = None
    in_section = False
    for line in text.splitlines():
        if line.startswith("## Ticket projects"):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section or not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(re.fullmatch(r"[:\- ]*", cell) for cell in cells):
            continue
        if header is None:
            header = [cell.lower() for cell in cells]
            continue
        rows.append(dict(zip(header, cells)))
    return rows


def _pair_groups(rows: list[dict], prefixes: list[str]) -> list[tuple[str, str]]:
    found: set[tuple[str, str]] = set()
    known = set(prefixes)
    for row in rows:
        convention = row.get("link convention") or ""
        if not re.search(r"pair|linked", convention, re.I):
            continue
        mentioned = [prefix for prefix in prefixes if re.search(rf"\b{re.escape(prefix)}\b", convention)]
        own = (row.get("key prefix") or "").strip()
        if own in known and own not in mentioned:
            mentioned.append(own)
        unique = sorted(set(mentioned))
        for index, left in enumerate(unique):
            for right in unique[index + 1 :]:
                found.add((left, right))
    return sorted(found)


def _resolve_since(root: Path, since: str | None, today: date) -> tuple[str, str]:
    if since:
        if not DATE_RE.fullmatch(since):
            raise ValueError(f"since must be YYYY-MM-DD, got {since!r}")
        return since, "argument"
    cursor_path = root / "state" / "repo-activity-cursor.json"
    if cursor_path.is_file():
        try:
            cursor = json.loads(cursor_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cursor = {}
        stamped = cursor.get("since") or ""
        if DATE_RE.fullmatch(stamped):
            return stamped, "cursor"
    default = (today - timedelta(days=DEFAULT_WINDOW_DAYS)).isoformat()
    return default, "default-14d"


def _discover_repos(repos_dir: Path) -> list[tuple[str, Path]]:
    if not repos_dir.is_dir():
        return []
    found = []
    for child in sorted(repos_dir.iterdir(), key=lambda path: path.name):
        if child.name.startswith("."):
            continue
        target = child.resolve()
        if target.is_dir() and _is_git(target):
            found.append((child.name, target))
    return found


def _is_git(path: Path) -> bool:
    proc = _run(path, ["rev-parse", "--is-inside-work-tree"])
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def _fetch(repo: Path, since: str) -> dict:
    remotes = _run(repo, ["remote"])
    if remotes.returncode != 0 or not remotes.stdout.strip():
        return {"fetch": "local-log", "note": "no remote; used local log"}
    try:
        proc = _run(
            repo,
            ["fetch", f"--shallow-since={since}", "--no-tags", "origin"],
            timeout=20,
        )
    except subprocess.TimeoutExpired:
        return {"fetch": "local-log", "note": "fetch failed (timeout); used local log"}
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "non-zero exit").strip().splitlines()
        tail = detail[-1][:180] if detail else "non-zero exit"
        return {"fetch": "local-log", "note": f"fetch failed ({tail}); used local log"}
    return {"fetch": "ok", "note": "fetched --shallow-since"}


def _default_branch(repo: Path) -> str:
    head = _run(repo, ["rev-parse", "--abbrev-ref", "HEAD"])
    name = head.stdout.strip()
    if head.returncode == 0 and name and name != "HEAD":
        return name
    return "main"


def _local_branches(repo: Path) -> list[str]:
    proc = _run(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def _log_commits(
    repo: Path,
    name: str,
    branch: str,
    since: str,
    prefixes: list[str],
    *,
    on_default: bool,
    exclude_branch: str | None = None,
) -> list[dict]:
    args = ["log", branch, f"--since={since}", f"--format={_LOG_FORMAT}", "--max-count=200"]
    if exclude_branch:
        args.extend(["--not", exclude_branch])
    proc = _run(repo, args)
    if proc.returncode != 0:
        return []
    commits = []
    for record in proc.stdout.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        parts = record.split("\x1f")
        if len(parts) < 5:
            continue
        sha, committed, parents, subject, body = parts[0], parts[1], parts[2], parts[3], parts[4]
        keys = extract_keys(f"{subject}\n{body}", prefixes)
        if not keys:
            continue
        parent_ids = [item for item in parents.split() if item]
        commits.append(
            {
                "repo": f"repos/{name}",
                "sha": sha,
                "subject": subject.replace("\n", " ").strip(),
                "date": (committed or "")[:10],
                "keys": keys,
                "on_default_branch": on_default,
                "merge": len(parent_ids) > 1,
            }
        )
    return commits


def _run(repo: Path, args: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def _load_tickets(path: str | None) -> list[dict] | None:
    if not path:
        return None
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("issues") or payload.get("tickets") or []
    if not isinstance(payload, list):
        raise ValueError("tickets file must be a list or an object with issues/tickets")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan repos/ git metadata for ticket keys")
    parser.add_argument("--root", required=True, help="live workspace root")
    parser.add_argument("--since", help="YYYY-MM-DD; default is the cursor, else 14 days")
    parser.add_argument("--today", help="YYYY-MM-DD override for the snapshot date")
    parser.add_argument("--tickets", help="board snapshot JSON for the four drift checks")
    parser.add_argument("--stale-days", type=int, default=STALE_DAYS)
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="skip fetch and read the local log only",
    )
    args = parser.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    today = None
    if args.today:
        if not DATE_RE.fullmatch(args.today):
            print("ERROR: --today must be YYYY-MM-DD", file=sys.stderr)
            return 2
        today = date.fromisoformat(args.today)
    try:
        tickets = _load_tickets(args.tickets)
        snapshot = run_activity(
            root,
            since=args.since,
            today=today,
            stale_days=args.stale_days,
            tickets=tickets,
            fetch=not args.no_fetch,
        )
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    print(snapshot["snapshot"])
    for repo in snapshot["repos"]:
        if repo.get("note"):
            print(f"{repo['path']}: {repo['note']}")
    if snapshot.get("prefix_note"):
        print(snapshot["prefix_note"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
