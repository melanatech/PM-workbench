#!/usr/bin/env python3
"""Local entity-link map. jira-reconcile is the only writer.

Columns: from, to, type, source, confidence, status, first_seen.
status is proposed or confirmed.

Explicit links (a key or id named in a source) are Tier 1 local rows
(status=confirmed). Inferred links are Tier 2 (status=proposed) until
confirm_proposed(..., approved=True). Tracker payloads stay empty unless
approved=True, and this module never calls a tracker.

Confirmed links update registers/initiatives.csv in place (same id, same
order). That register has no links column: a doc goes in prd, a decision
id in related_decisions, and other refs as a links: clause in notes.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import repo_activity  # noqa: E402

HEADER = ["from", "to", "type", "source", "confidence", "status", "first_seen"]

LINK_TYPES = {
    "ticket-epic",
    "paired-tickets",
    "ticket-initiative",
    "initiative-doc",
    "ticket-decision",
    "ticket-thread",
    "initiative-thread",
    "commit-ticket",
}

_DEC = re.compile(r"\bDEC-\d+\b")
_INIT = re.compile(r"\bINIT-\d+\b")
_DECISION = re.compile(r"(?i)\b(decided|decision\s*:|we agreed|approved)\b")
_RISK = re.compile(r"(?i)\b(risk\s*:|at risk|might slip)\b")
_BLOCKER = re.compile(r"(?i)\b(blocker|blocked|blocking|waiting on)\b")
_STOPWORDS = {"with", "from", "that", "this", "have", "been", "will", "into", "your"}


def links_path(root: Path) -> Path:
    return Path(root) / "state" / "entity-links.csv"


def ensure_links(root: Path) -> Path:
    path = links_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with path.open("w", encoding="utf-8", newline="") as handle:
            csv.writer(handle, lineterminator="\n").writerow(HEADER)
    return path


def read_links(root: Path) -> list[dict]:
    path = ensure_links(root)
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def upsert_links(root: Path, rows: list[dict]) -> list[dict]:
    """Append new rows. Upgrade proposed → confirmed in place. Keep first_seen."""
    existing = read_links(root)
    index = {(row["from"], row["to"], row["type"]): row for row in existing}
    for row in rows:
        item = {column: (row.get(column) or "") for column in HEADER}
        if item["type"] not in LINK_TYPES:
            raise ValueError(f"unknown link type: {item['type']}")
        if item["status"] not in {"proposed", "confirmed"}:
            raise ValueError(f"status must be proposed or confirmed, got {item['status']!r}")
        key = (item["from"], item["to"], item["type"])
        current = index.get(key)
        if current is None:
            existing.append(item)
            index[key] = item
            continue
        if current["status"] != "confirmed" and item["status"] == "confirmed":
            current["status"] = "confirmed"
            current["confidence"] = item["confidence"] or current["confidence"]
            current["source"] = item["source"] or current["source"]
    _write_links(links_path(root), existing)
    return existing


def external_tracker_writes(rows: list[dict], *, approved: bool) -> list[dict]:
    """Local payload drafts. Empty until an approved run. Never calls a tracker."""
    if not approved:
        return []
    payloads = []
    for row in rows:
        if row.get("status") != "confirmed":
            continue
        if row.get("type") not in {"ticket-epic", "paired-tickets", "commit-ticket"}:
            continue
        if not row.get("from") or not row.get("to") or row["to"].endswith(":?"):
            continue
        payloads.append(
            {
                "action": "link",
                "from": row["from"],
                "to": row["to"],
                "type": row["type"],
                "approved": True,
            }
        )
    return payloads


def confirm_proposed(root: Path, pairs: list[tuple[str, str, str]], *, approved: bool) -> list[dict]:
    """Flip named proposed rows to confirmed. No-op unless approved."""
    if not approved or not pairs:
        return []
    wanted = set(pairs)
    changed = []
    rows = read_links(root)
    for row in rows:
        key = (row["from"], row["to"], row["type"])
        if key in wanted and row["status"] == "proposed":
            row["status"] = "confirmed"
            changed.append(dict(row))
    _write_links(links_path(root), rows)
    return changed


def comment_candidates(comments: list[dict], prefixes: list[str] | None = None) -> list[dict]:
    """Decision, risk, and blocker candidates. Nothing is auto-written."""
    prefixes = prefixes or []
    candidates = []
    for comment in comments or []:
        body = (comment.get("body") or "").replace("\n", " ").strip()
        ticket = (comment.get("ticket") or "").strip()
        kinds = []
        if _DECISION.search(body) or _DEC.search(body):
            kinds.append("decision")
        if _RISK.search(body):
            kinds.append("risk")
        if _BLOCKER.search(body):
            kinds.append("blocker")
        for kind in kinds:
            candidates.append(
                {
                    "kind": kind,
                    "ticket": ticket,
                    "excerpt": body[:240],
                    "cited": _DEC.findall(body),
                    "keys": repo_activity.extract_keys(body, prefixes),
                    "source": f"comment:{ticket}" if ticket else "comment",
                    "created": comment.get("created") or "",
                    "auto_written": False,
                }
            )
    return candidates


def build_proposals(
    *,
    prefixes: list[str],
    pairs: list[tuple[str, str]],
    commits: list[dict] | None = None,
    tickets: list[dict] | None = None,
    comments: list[dict] | None = None,
    initiatives: list[dict] | None = None,
    threads: list[dict] | None = None,
    first_seen: str | None = None,
) -> dict:
    """Return explicit (Tier 1), inferred (Tier 2), and comment candidates.

    register_writes and tracker_writes are always empty here.
    """
    seen = first_seen or date.today().isoformat()
    explicit: list[dict] = []
    inferred: list[dict] = []
    commits = commits or []
    tickets = tickets or []
    comments = comments or []
    initiatives = initiatives or []
    threads = threads or []

    for commit in commits:
        cite = f"{commit.get('repo')}@{str(commit.get('sha') or '')[:12]}"
        for key in commit.get("keys") or []:
            explicit.append(
                _row(cite, key, "commit-ticket", cite, "high", "confirmed", seen)
            )

    comments_by_ticket: dict[str, list[str]] = {}
    for comment in comments:
        ticket = (comment.get("ticket") or "").strip()
        comments_by_ticket.setdefault(ticket, []).append(comment.get("body") or "")

    for ticket in tickets:
        key = (ticket.get("key") or "").strip()
        if not key:
            continue
        parent = (ticket.get("parent") or "").strip()
        blob = "\n".join(comments_by_ticket.get(key, []))
        epic_from_comment = _keys_after_label(blob, prefixes, "epic", "parent")
        if parent:
            explicit.append(
                _row(key, parent, "ticket-epic", "ticket.parent", "high", "confirmed", seen)
            )
        elif epic_from_comment:
            for epic in epic_from_comment:
                explicit.append(
                    _row(key, epic, "ticket-epic", f"comment:{key}", "high", "confirmed", seen)
                )
        else:
            inferred.append(
                _row(key, "epic:?", "ticket-epic", f"ticket:{key} missing parent", "low", "proposed", seen)
            )

        linked = set(ticket.get("links") or [])
        linked.update(repo_activity.extract_keys(blob, prefixes))
        own_prefix = key.split("-", 1)[0]
        for left, right in pairs:
            other = right if own_prefix == left else left if own_prefix == right else ""
            if not other:
                continue
            named = [item for item in linked if item.startswith(other + "-")]
            if named:
                for partner in named:
                    explicit.append(
                        _row(
                            key,
                            partner,
                            "paired-tickets",
                            f"comment:{key}" if partner in repo_activity.extract_keys(blob, prefixes) else "ticket.links",
                            "high",
                            "confirmed",
                            seen,
                        )
                    )
            else:
                inferred.append(
                    _row(
                        key,
                        f"{other}:?",
                        "paired-tickets",
                        "systems-map link convention",
                        "low",
                        "proposed",
                        seen,
                    )
                )

        for dec in _DEC.findall(blob):
            explicit.append(
                _row(key, dec, "ticket-decision", f"comment:{key}", "high", "confirmed", seen)
            )
        for init in _INIT.findall(blob + "\n" + (ticket.get("summary") or "")):
            explicit.append(
                _row(key, init, "ticket-initiative", f"comment:{key}", "high", "confirmed", seen)
            )

    for initiative in initiatives:
        init_id = (initiative.get("id") or "").strip()
        if not init_id:
            continue
        notes = initiative.get("notes") or ""
        summary_blob = f"{initiative.get('name') or ''}\n{notes}"
        for key in repo_activity.extract_keys(summary_blob, prefixes):
            explicit.append(
                _row(init_id, key, "ticket-initiative", "initiatives.csv", "high", "confirmed", seen)
            )
        for doc in _split_multi(initiative.get("prd") or ""):
            explicit.append(
                _row(init_id, doc, "initiative-doc", "initiatives.csv prd", "high", "confirmed", seen)
            )

    _add_name_inferences(tickets, initiatives, prefixes, inferred, seen)

    for thread in threads:
        url = (thread.get("url") or "").strip()
        body = thread.get("body") or ""
        keys = list(thread.get("keys") or []) or repo_activity.extract_keys(body, prefixes)
        init = (thread.get("initiative") or "").strip() or (_INIT.search(body).group(0) if _INIT.search(body) else "")
        if url and keys:
            for key in keys:
                explicit.append(_row(key, url, "ticket-thread", url, "high", "confirmed", seen))
        elif keys:
            for key in keys:
                inferred.append(
                    _row(key, "thread:?", "ticket-thread", "thread text without url", "low", "proposed", seen)
                )
        if url and init:
            explicit.append(_row(init, url, "initiative-thread", url, "high", "confirmed", seen))

    return {
        "explicit": _dedupe(explicit),
        "inferred": _dedupe(inferred),
        "candidates": comment_candidates(comments, prefixes),
        "register_writes": [],
        "tracker_writes": [],
    }


def apply_confirmed_to_initiatives(root: Path, *, today: str | None = None) -> list[str]:
    """Update initiative link fields in place. Same ids, same order. No new rows."""
    root = Path(root)
    path = root / "registers" / "initiatives.csv"
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if not rows or "id" not in fieldnames:
        return []
    confirmed = [row for row in read_links(root) if row.get("status") == "confirmed"]
    by_id = {row["id"]: row for row in rows}
    changed: list[str] = []
    stamp = today or date.today().isoformat()
    for link in confirmed:
        init_id, other, field = _initiative_target(link)
        if not init_id or init_id not in by_id or not field:
            continue
        row = by_id[init_id]
        if field == "notes":
            clause = f"links: {other} ({link['type']})"
            notes = row.get("notes") or ""
            if clause in notes:
                continue
            row["notes"] = f"{notes} | {clause}".strip(" |") if notes else clause
        else:
            if not _append_token(row, field, other):
                continue
        if "last_updated" in fieldnames:
            row["last_updated"] = stamp
        if init_id not in changed:
            changed.append(init_id)
    if not changed:
        return []
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column) or "" for column in fieldnames})
    return changed


def _initiative_target(link: dict) -> tuple[str, str, str]:
    left, right, kind = link.get("from") or "", link.get("to") or "", link.get("type") or ""
    if left.startswith("INIT-"):
        init_id, other = left, right
    elif right.startswith("INIT-"):
        init_id, other = right, left
    else:
        return "", "", ""
    if not other or other.endswith(":?"):
        return "", "", ""
    if kind == "initiative-doc":
        return init_id, other, "prd"
    if kind == "ticket-decision" or other.startswith("DEC-"):
        return init_id, other, "related_decisions"
    return init_id, other, "notes"


def _append_token(row: dict, field: str, token: str) -> bool:
    current = row.get(field) or ""
    parts = [part.strip() for part in current.split(";") if part.strip()]
    if token in parts:
        return False
    parts.append(token)
    row[field] = ";".join(parts)
    return True


def _add_name_inferences(tickets, initiatives, prefixes, inferred, seen: str) -> None:
    explicit_pairs = set()
    for ticket in tickets:
        key = (ticket.get("key") or "").strip()
        if not key:
            continue
        summary = ticket.get("summary") or ""
        if repo_activity.extract_keys(summary, prefixes) or _INIT.search(summary):
            continue
        tokens = _tokens(summary)
        if len(tokens) < 2:
            continue
        for initiative in initiatives:
            init_id = (initiative.get("id") or "").strip()
            name_tokens = _tokens(initiative.get("name") or "")
            if not init_id or len(tokens & name_tokens) < 2:
                continue
            pair = (key, init_id)
            if pair in explicit_pairs:
                continue
            explicit_pairs.add(pair)
            inferred.append(
                _row(
                    key,
                    init_id,
                    "ticket-initiative",
                    "name overlap without a named key",
                    "medium",
                    "proposed",
                    seen,
                )
            )


def _tokens(text: str) -> set[str]:
    return {
        word.lower()
        for word in re.findall(r"[A-Za-z]{4,}", text or "")
        if word.lower() not in _STOPWORDS
    }


def _keys_after_label(text: str, prefixes: list[str], *labels: str) -> list[str]:
    found = []
    for key in repo_activity.extract_keys(text, prefixes):
        for label in labels:
            if re.search(rf"(?i)\b{label}\s+{re.escape(key)}\b", text or ""):
                found.append(key)
                break
    return found


def _split_multi(value: str) -> list[str]:
    return [part.strip() for part in (value or "").split(";") if part.strip()]


def _row(left, right, kind, source, confidence, status, seen) -> dict:
    return {
        "from": left,
        "to": right,
        "type": kind,
        "source": source.replace("\n", " "),
        "confidence": confidence,
        "status": status,
        "first_seen": seen,
    }


def _dedupe(rows: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for row in rows:
        key = (row["from"], row["to"], row["type"])
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def _write_links(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in HEADER})


def _load_json_list(path: str | None) -> list:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        for key in ("commits", "issues", "tickets", "comments", "threads"):
            if key in payload and isinstance(payload[key], list):
                return payload[key]
        return []
    return payload if isinstance(payload, list) else []


def _load_initiatives(root: Path) -> list[dict]:
    path = root / "registers" / "initiatives.csv"
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Propose local entity links")
    parser.add_argument("--root", required=True)
    sub = parser.add_subparsers(dest="cmd", required=True)

    propose = sub.add_parser("propose")
    propose.add_argument("--activity", help="repo-activity snapshot JSON")
    propose.add_argument("--tickets", help="board ticket JSON")
    propose.add_argument("--comments", help="comment JSON")
    propose.add_argument("--threads", help="thread JSON")
    propose.add_argument("--first-seen", default="")
    propose.add_argument(
        "--apply-confirmed",
        action="store_true",
        help="update initiative link fields for confirmed rows",
    )

    candidates = sub.add_parser("candidates")
    candidates.add_argument("--comments", required=True)

    confirm = sub.add_parser("confirm")
    confirm.add_argument("--from", dest="left", required=True)
    confirm.add_argument("--to", dest="right", required=True)
    confirm.add_argument("--type", required=True)
    confirm.add_argument("--approved", action="store_true")
    confirm.add_argument("--apply", action="store_true")

    args = parser.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2

    _rel, map_text = repo_activity.locate_systems_map(root)
    parsed = repo_activity.parse_systems_map(map_text)

    if args.cmd == "confirm":
        changed = confirm_proposed(
            root,
            [(args.left, args.right, args.type)],
            approved=args.approved,
        )
        applied: list[str] = []
        if args.apply and args.approved:
            applied = apply_confirmed_to_initiatives(root)
        print(json.dumps({"confirmed": len(changed), "initiatives_updated": applied}, indent=2))
        return 0

    if args.cmd == "candidates":
        comments = _load_json_list(args.comments)
        payload = {
            "candidates": comment_candidates(comments, parsed["prefixes"]),
            "register_writes": [],
            "tracker_writes": [],
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    activity = {}
    if args.activity:
        activity = json.loads(Path(args.activity).read_text(encoding="utf-8"))
    proposals = build_proposals(
        prefixes=parsed["prefixes"],
        pairs=[tuple(pair) for pair in parsed["pairs"]],
        commits=activity.get("commits") if isinstance(activity, dict) else [],
        tickets=_load_json_list(args.tickets),
        comments=_load_json_list(args.comments),
        initiatives=_load_initiatives(root),
        threads=_load_json_list(args.threads),
        first_seen=args.first_seen or None,
    )
    written = upsert_links(root, proposals["explicit"] + proposals["inferred"])
    applied: list[str] = []
    if args.apply_confirmed:
        applied = apply_confirmed_to_initiatives(root, today=args.first_seen or None)
    print(
        json.dumps(
            {
                "explicit": len(proposals["explicit"]),
                "inferred": len(proposals["inferred"]),
                "candidates": len(proposals["candidates"]),
                "rows": len(written),
                "initiatives_updated": applied,
                "tracker_writes": [],
                "register_writes": [],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
