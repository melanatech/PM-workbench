#!/usr/bin/env python3
"""Import Cursor agent activity, and optional dashboard tokens, into a live workspace.

Activity lane reads Cursor's local state DB read-only
(``file:<path>?mode=ro&immutable=1``). One row per conversation. Message
text is used only in memory to classify the first user turn, then dropped.
Local ``tokenCount`` values are ignored (they are zero in current Cursor DBs).

Token lane (optional ``--usage-csv``): a Cursor dashboard usage export,
joined to conversations by model and a timestamp window.

Stdlib only. Generic for any Cursor user — pass ``--db`` and ``--root``.

  python3 scripts/import_cursor_usage.py --root ~/pm-live
  python3 scripts/import_cursor_usage.py --root ~/pm-live --usage-csv export.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Sibling import. Tests put scripts/ on sys.path; CLI does too via this file.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import session_usage  # noqa: E402

DEFAULT_DB = (
    Path.home()
    / "Library/Application Support/Cursor/User/globalStorage/state.vscdb"
)
DEFAULT_KIT_MARKERS = ("pm-workbench", "pm-live")
DEFAULT_JOIN_MINUTES = 120
TITLE_MAX = 500

ACTIVITY_FIELDS = [
    "id",
    "created",
    "last_message",
    "workspace",
    "title",
    "selected_model",
    "user_msgs",
    "assistant_msgs",
    "subagent_count",
    "kit_related",
    "category",
    "harness",
    "surface",
]

USAGE_FIELDS = [
    "date",
    "kind",
    "model",
    "input_tokens",
    "cache_write_tokens",
    "cache_read_tokens",
    "output_tokens",
    "cost",
    "conversation_id",
    "harness",
    "surface",
]

# Normalized header → field. First match wins; see _header_field.
_HEADER_EXACT = {
    "date": "date",
    "timestamp": "date",
    "time": "date",
    "datetime": "date",
    "created": "date",
    "kind": "kind",
    "type": "kind",
    "event": "kind",
    "model": "model",
    "model name": "model",
    "model_name": "model",
    "input": "input_tokens",
    "input tokens": "input_tokens",
    "input_tokens": "input_tokens",
    "prompt tokens": "input_tokens",
    "output": "output_tokens",
    "output tokens": "output_tokens",
    "output_tokens": "output_tokens",
    "completion tokens": "output_tokens",
    "cache write": "cache_write_tokens",
    "cache write tokens": "cache_write_tokens",
    "cache_write": "cache_write_tokens",
    "cache_write_tokens": "cache_write_tokens",
    "cache creation": "cache_write_tokens",
    "cache creation tokens": "cache_write_tokens",
    "cache read": "cache_read_tokens",
    "cache read tokens": "cache_read_tokens",
    "cache_read": "cache_read_tokens",
    "cache_read_tokens": "cache_read_tokens",
    "cached tokens": "cache_read_tokens",
    "cost": "cost",
    "cost (usd)": "cost",
    "cost usd": "cost",
    "price": "cost",
    "total cost": "cost",
}


def sqlite_uri(path: Path) -> str:
    """Read-only immutable URI. Spaces and special characters are percent-encoded."""
    return path.expanduser().resolve().as_uri() + "?mode=ro&immutable=1"


def open_readonly(path: Path, *, immutable: bool = True) -> sqlite3.Connection:
    """Open the DB without writing.

    ``immutable=True`` uses ``mode=ro&immutable=1`` (no lock, no WAL). A live
    Cursor process can make that snapshot look malformed; callers may retry
    or fall back to ``mode=ro`` (still read-only, follows the WAL).
    """
    if immutable:
        uri = sqlite_uri(path)
        if "mode=ro" not in uri or "immutable=1" not in uri:
            raise RuntimeError("refusing to open Cursor DB without mode=ro&immutable=1")
    else:
        uri = path.expanduser().resolve().as_uri() + "?mode=ro"
        if "mode=ro" not in uri or "immutable=1" in uri:
            raise RuntimeError("refusing a writable fallback")
    return sqlite3.connect(uri, uri=True)


def _parse_time(value) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        n = float(value)
        if n > 1e12:
            n = n / 1000.0
        try:
            return datetime.fromtimestamp(n, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = str(value).strip()
    if not text:
        return None
    if re.fullmatch(r"\d{13}", text):
        return _parse_time(int(text))
    if re.fullmatch(r"\d{10}", text):
        return _parse_time(int(text))
    text = text.replace("Z", "+00:00")
    for candidate in (text, text[:19], text[:10]):
        try:
            dt = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _iso(dt: datetime | None) -> str:
    if dt is None:
        return ""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def bubble_role(type_value) -> str | None:
    """Map Cursor's bubble type to user or assistant.

    Observed local DB uses integers (1 user, 2 assistant). Strings are accepted
    because the format is undocumented.
    """
    if type_value is None:
        return None
    if isinstance(type_value, bool):
        return None
    if isinstance(type_value, (int, float)):
        n = int(type_value)
        if n == 1:
            return "user"
        if n == 2:
            return "assistant"
        return None
    text = str(type_value).strip().lower()
    if text in ("1", "user", "human"):
        return "user"
    if text in ("2", "assistant", "ai"):
        return "assistant"
    return None


def workspace_label(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, dict):
        for key in ("uri", "configPath", "folder"):
            uri = value.get(key)
            if isinstance(uri, dict):
                path = uri.get("fsPath") or uri.get("path") or ""
                if path:
                    return str(path)
            elif isinstance(uri, str) and uri:
                return uri
        ident = value.get("id") or value.get("workspaceId") or ""
        return str(ident) if ident else ""
    return ""


def _subagent_count(data: dict) -> int:
    ids = data.get("subagentComposerIds")
    if not isinstance(ids, list):
        ids = data.get("subComposerIds")
    if not isinstance(ids, list):
        return 0
    return sum(1 for item in ids if item)


def _selected_model(data: dict) -> str:
    mc = data.get("modelConfig")
    if isinstance(mc, dict):
        name = mc.get("modelName")
        if name:
            return str(name).strip()
    for key in ("modelName", "model"):
        if data.get(key):
            return str(data[key]).strip()
    return ""


def _title(data: dict) -> str:
    raw = data.get("name")
    if not isinstance(raw, str):
        raw = ""
    text = " ".join(raw.split())
    if len(text) > TITLE_MAX:
        text = text[:TITLE_MAX]
    return text


def is_kit_related(workspace: str, markers: tuple[str, ...] = DEFAULT_KIT_MARKERS) -> bool:
    low = (workspace or "").lower()
    return any(m.lower() in low for m in markers if m)


def classify_title(title: str, first_user_text: str) -> str:
    """Reuse session_usage categories. first_user_text is not stored."""
    blob = "\n".join(part for part in (title or "", first_user_text or "") if part)
    category, _source = session_usage.classify_l2a(blob)
    return category or "other"


def _loads(raw) -> tuple[dict | None, str]:
    if raw is None:
        return None, "empty"
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None, "decode"
    if not isinstance(raw, str):
        raw = str(raw)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None, "json"
    if not isinstance(data, dict):
        return None, "not_object"
    return data, ""


def _composer_id_from_key(key: str) -> str:
    prefix = "composerData:"
    if key.startswith(prefix):
        return key[len(prefix):]
    return ""


def _bubble_ids_from_key(key: str) -> tuple[str, str]:
    # bubbleId:<composerId>:<bubbleId>
    parts = key.split(":")
    if len(parts) >= 3 and parts[0] == "bubbleId":
        return parts[1], parts[2]
    return "", ""


def _load_header_workspaces(conn: sqlite3.Connection) -> dict[str, str]:
    """composerId → workspace label from composerHeaders, when that table exists."""
    found: dict[str, str] = {}
    try:
        cur = conn.execute(
            "SELECT composerId, workspaceId, value FROM composerHeaders"
        )
    except sqlite3.Error:
        return found
    for composer_id, workspace_id, value in cur:
        label = ""
        data, err = _loads(value)
        if data and not err:
            label = workspace_label(data.get("workspaceIdentifier"))
        if not label and isinstance(workspace_id, str):
            label = workspace_id.strip()
        if composer_id and label and composer_id not in found:
            found[str(composer_id)] = label
    return found


def import_activity(
    db_path: Path,
    *,
    kit_markers: tuple[str, ...] = DEFAULT_KIT_MARKERS,
) -> tuple[list[dict], dict]:
    """Return activity rows and a skip/count report. Does not write files."""
    stats = {
        "composers_seen": 0,
        "composers_imported": 0,
        "composers_skipped": 0,
        "bubbles_seen": 0,
        "bubbles_skipped": 0,
        "skip_reasons": {},
    }

    def skip(bucket: str) -> None:
        stats["skip_reasons"][bucket] = stats["skip_reasons"].get(bucket, 0) + 1

    # A live Cursor process can tear an immutable snapshot. Retry, then
    # fall back to mode=ro (still no writes; follows the WAL).
    open_plan = [(True, "ro_immutable")] * 3 + [(False, "ro_fallback")]
    conn: sqlite3.Connection | None = None
    last_error: Exception | None = None
    composers: dict[str, dict] = {}
    for immutable, open_mode in open_plan:
        stats["composers_seen"] = 0
        stats["composers_skipped"] = 0
        stats["bubbles_seen"] = 0
        stats["bubbles_skipped"] = 0
        stats["skip_reasons"] = {}
        composers = {}
        try:
            conn = open_readonly(db_path, immutable=immutable)
            stats["open_mode"] = open_mode
            headers = _load_header_workspaces(conn)
            cur = conn.execute(
                "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'composerData:%'"
            )
            for key, raw in cur:
                stats["composers_seen"] += 1
                data, err = _loads(raw)
                if err or data is None:
                    stats["composers_skipped"] += 1
                    skip(f"composer_{err}")
                    continue
                cid = str(data.get("composerId") or _composer_id_from_key(str(key)) or "")
                if not cid:
                    stats["composers_skipped"] += 1
                    skip("composer_missing_id")
                    continue
                created = _parse_time(data.get("createdAt"))
                workspace = workspace_label(data.get("workspaceIdentifier"))
                if not workspace:
                    workspace = headers.get(cid, "")
                composers[cid] = {
                    "id": cid,
                    "created": created,
                    "last_message": _parse_time(data.get("lastUpdatedAt")) or created,
                    "workspace": workspace,
                    "title": _title(data),
                    "selected_model": _selected_model(data),
                    "user_msgs": 0,
                    "assistant_msgs": 0,
                    "subagent_count": _subagent_count(data),
                    "first_user_text": "",
                    "first_user_at": None,
                }

            bcur = conn.execute(
                "SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:%'"
            )
            for key, raw in bcur:
                stats["bubbles_seen"] += 1
                composer_id, _bubble_id = _bubble_ids_from_key(str(key))
                conv = composers.get(composer_id)
                if conv is None:
                    stats["bubbles_skipped"] += 1
                    skip("bubble_orphan")
                    continue
                data, err = _loads(raw)
                if err or data is None:
                    stats["bubbles_skipped"] += 1
                    skip(f"bubble_{err}")
                    continue
                role = bubble_role(data.get("type"))
                created = _parse_time(data.get("createdAt"))
                if role is None and created is None:
                    stats["bubbles_skipped"] += 1
                    skip("bubble_unusable")
                    continue
                if role is None:
                    stats["bubbles_skipped"] += 1
                    skip("bubble_unknown_role")
                elif role == "user":
                    conv["user_msgs"] += 1
                    text = data.get("text") if isinstance(data.get("text"), str) else ""
                    prev = conv["first_user_at"]
                    if text and (prev is None or (created is not None and created < prev)):
                        conv["first_user_text"] = text
                        conv["first_user_at"] = created or prev
                else:
                    conv["assistant_msgs"] += 1
                if created is not None:
                    last = conv["last_message"]
                    if last is None or created > last:
                        conv["last_message"] = created
        except sqlite3.DatabaseError as exc:
            last_error = exc
            composers = {}
            continue
        else:
            last_error = None
            break
        finally:
            if conn is not None:
                conn.close()
                conn = None
    if last_error is not None and not composers:
        raise last_error

    rows: list[dict] = []
    for conv in composers.values():
        first = conv.pop("first_user_text")
        conv.pop("first_user_at", None)
        category = classify_title(conv["title"], first)
        # first user text must not survive past classification
        del first
        row = {
            "id": conv["id"],
            "created": _iso(conv["created"]),
            "last_message": _iso(conv["last_message"]),
            "workspace": conv["workspace"],
            "title": conv["title"],
            "selected_model": conv["selected_model"],
            "user_msgs": conv["user_msgs"],
            "assistant_msgs": conv["assistant_msgs"],
            "subagent_count": conv["subagent_count"],
            "kit_related": "yes" if is_kit_related(conv["workspace"], kit_markers) else "no",
            "category": category,
            "harness": "cursor",
            "surface": "cursor-agent",
        }
        rows.append(row)
    rows.sort(key=lambda r: (r["created"], r["id"]))
    stats["composers_imported"] = len(rows)
    return rows, stats


def _norm_header(name: str) -> str:
    text = (name or "").strip().lower().lstrip("\ufeff")
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text


def _header_field(name: str) -> str | None:
    norm = _norm_header(name)
    if norm in _HEADER_EXACT:
        return _HEADER_EXACT[norm]
    if "cache" in norm and "write" in norm and "input" not in norm:
        return "cache_write_tokens"
    if "cache" in norm and ("read" in norm or "hit" in norm):
        return "cache_read_tokens"
    if norm.startswith("input") and "cache" not in norm and "total" not in norm:
        return "input_tokens"
    if "without cache" in norm or "w/o cache" in norm or "w/o cache write" in norm:
        return "input_tokens"
    if norm.startswith("output") or norm == "completion":
        return "output_tokens"
    if norm in ("cost",) or norm.startswith("cost"):
        return "cost"
    if norm in ("model",) or norm.startswith("model"):
        return "model"
    if norm in ("date", "timestamp") or norm.startswith("date"):
        return "date"
    return None


def _num(value: str) -> str:
    text = (value or "").strip().replace(",", "").replace("$", "")
    if not text:
        return ""
    try:
        return str(int(text)) if re.fullmatch(r"-?\d+", text) else str(float(text))
    except ValueError:
        return ""


def _norm_model(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")


def models_compatible(usage_model: str, conv_model: str) -> bool:
    a = _norm_model(usage_model)
    b = _norm_model(conv_model)
    if not a or not b:
        return False
    if a == b:
        return True
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    return len(short) >= 8 and long.startswith(short)


def join_conversation_id(
    when: datetime,
    model: str,
    conversations: list[dict],
    *,
    slack: timedelta,
) -> str:
    """Pick the conversation whose [created, last_message] is closest to ``when``.

    Model must match. Distance 0 means the timestamp falls inside the span.
    Ties go to the shorter span, then the earlier created time.
    """
    best: tuple[float, float, str, str] | None = None
    for conv in conversations:
        if not models_compatible(model, conv.get("selected_model") or ""):
            continue
        start = _parse_time(conv.get("created"))
        end = _parse_time(conv.get("last_message")) or start
        if start is None or end is None:
            continue
        if end < start:
            start, end = end, start
        if when < start:
            dist = (start - when).total_seconds()
        elif when > end:
            dist = (when - end).total_seconds()
        else:
            dist = 0.0
        if dist > slack.total_seconds():
            continue
        span = (end - start).total_seconds()
        created_key = conv.get("created") or ""
        cid = conv.get("id") or ""
        cand = (dist, span, created_key, cid)
        if best is None or cand < best:
            best = cand
    return best[3] if best else ""


def parse_usage_csv(
    path: Path,
    conversations: list[dict],
    *,
    slack: timedelta,
) -> tuple[list[dict], dict]:
    stats = {
        "usage_seen": 0,
        "usage_imported": 0,
        "usage_skipped": 0,
        "usage_matched": 0,
        "usage_unmatched": 0,
        "skip_reasons": {},
    }

    def skip(bucket: str) -> None:
        stats["skip_reasons"][bucket] = stats["skip_reasons"].get(bucket, 0) + 1

    rows: list[dict] = []
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            stats["usage_skipped"] += 1
            skip("usage_no_header")
            return rows, stats
        mapping: dict[str, str] = {}
        for name in reader.fieldnames:
            field = _header_field(name)
            if field and field not in mapping.values():
                mapping[name] = field
        if "date" not in mapping.values() or "model" not in mapping.values():
            stats["usage_skipped"] += 1
            skip("usage_missing_date_or_model_column")
            return rows, stats
        for raw in reader:
            stats["usage_seen"] += 1
            pulled = {field: "" for field in (
                "date", "kind", "model", "input_tokens", "cache_write_tokens",
                "cache_read_tokens", "output_tokens", "cost",
            )}
            for src, field in mapping.items():
                pulled[field] = (raw.get(src) or "").strip()
            when = _parse_time(pulled["date"])
            if when is None or not pulled["model"]:
                stats["usage_skipped"] += 1
                skip("usage_bad_date_or_model")
                continue
            conv_id = join_conversation_id(when, pulled["model"], conversations, slack=slack)
            if conv_id:
                stats["usage_matched"] += 1
            else:
                stats["usage_unmatched"] += 1
            rows.append({
                "date": _iso(when),
                "kind": pulled["kind"],
                "model": pulled["model"],
                "input_tokens": _num(pulled["input_tokens"]),
                "cache_write_tokens": _num(pulled["cache_write_tokens"]),
                "cache_read_tokens": _num(pulled["cache_read_tokens"]),
                "output_tokens": _num(pulled["output_tokens"]),
                "cost": _num(pulled["cost"]),
                "conversation_id": conv_id,
                "harness": "cursor",
                "surface": "cursor-agent",
            })
    stats["usage_imported"] = len(rows)
    return rows, stats


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def run_import(
    *,
    db_path: Path,
    root: Path,
    usage_csv: Path | None = None,
    join_minutes: int = DEFAULT_JOIN_MINUTES,
    kit_markers: tuple[str, ...] = DEFAULT_KIT_MARKERS,
) -> dict:
    activity, stats = import_activity(db_path, kit_markers=kit_markers)
    write_csv(root / "state" / "cursor-activity.csv", ACTIVITY_FIELDS, activity)
    stats["activity_path"] = str(root / "state" / "cursor-activity.csv")
    if usage_csv is not None:
        usage_rows, usage_stats = parse_usage_csv(
            usage_csv,
            activity,
            slack=timedelta(minutes=join_minutes),
        )
        write_csv(root / "state" / "cursor-usage.csv", USAGE_FIELDS, usage_rows)
        stats["usage_path"] = str(root / "state" / "cursor-usage.csv")
        for key, value in usage_stats.items():
            if key == "skip_reasons":
                for reason, n in value.items():
                    stats["skip_reasons"][reason] = stats["skip_reasons"].get(reason, 0) + n
            else:
                stats[key] = value
    else:
        stats["usage_seen"] = 0
        stats["usage_imported"] = 0
        stats["usage_skipped"] = 0
        stats["usage_matched"] = 0
        stats["usage_unmatched"] = 0
        stats["usage_path"] = ""
    return stats


def _print_stats(stats: dict) -> None:
    if stats.get("open_mode"):
        print(f"open_mode {stats['open_mode']}")
    print(f"composers_seen {stats.get('composers_seen', 0)}")
    print(f"composers_imported {stats.get('composers_imported', 0)}")
    print(f"composers_skipped {stats.get('composers_skipped', 0)}")
    print(f"bubbles_seen {stats.get('bubbles_seen', 0)}")
    print(f"bubbles_skipped {stats.get('bubbles_skipped', 0)}")
    print(f"usage_seen {stats.get('usage_seen', 0)}")
    print(f"usage_imported {stats.get('usage_imported', 0)}")
    print(f"usage_skipped {stats.get('usage_skipped', 0)}")
    print(f"usage_matched {stats.get('usage_matched', 0)}")
    print(f"usage_unmatched {stats.get('usage_unmatched', 0)}")
    reasons = stats.get("skip_reasons") or {}
    if reasons:
        print("skip_reasons " + ",".join(f"{k}={v}" for k, v in sorted(reasons.items())))
    if stats.get("activity_path"):
        print(f"activity_path {stats['activity_path']}")
    if stats.get("usage_path"):
        print(f"usage_path {stats['usage_path']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="Cursor state.vscdb path")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Live workspace root")
    parser.add_argument("--usage-csv", type=Path, default=None, help="Optional dashboard usage export")
    parser.add_argument("--join-window-minutes", type=int, default=DEFAULT_JOIN_MINUTES)
    parser.add_argument(
        "--kit-marker",
        action="append",
        default=None,
        help="Workspace path substring that flags kit_related (repeatable). Default: pm-workbench, pm-live",
    )
    args = parser.parse_args(argv)
    db_path = args.db.expanduser()
    if not db_path.is_file():
        print(f"Cursor DB not found: {db_path}", file=sys.stderr)
        return 1
    markers = tuple(args.kit_marker) if args.kit_marker else DEFAULT_KIT_MARKERS
    stats = run_import(
        db_path=db_path,
        root=args.root.expanduser(),
        usage_csv=args.usage_csv.expanduser() if args.usage_csv else None,
        join_minutes=args.join_window_minutes,
        kit_markers=markers,
    )
    _print_stats(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
