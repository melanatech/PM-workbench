#!/usr/bin/env python3
"""todo_register.py — add, update, finish, drop and list rows in registers/todos.csv.

The /todo command calls this script so dates, IDs and CSV quoting are handled by
code instead of by a model hand-editing a CSV (CLAUDE.md rule 14). Standard
library only; no network, no model.

Usage (run from the workbench root)
  python3 scripts/todo_register.py add --description "Ask support about export retries" \\
      [--owner me] [--due 2026-10-09] [--priority high|normal|low] [--initiative NAME] \\
      [--blocks "PRD for Bulk Export"] [--links "EV-211, RISK-008"] \\
      [--origin stated|proposed|commitment] [--source "inbox/meetings/..."] [--note TEXT]
  python3 scripts/todo_register.py update TODO-001 [--description ...] [--owner ...] [--due ...]
      [--priority ...] [--status open|in_progress|blocked] [--initiative ...] [--blocks ...]
      [--links ...] [--source ...] [--note ...]        (--due "" clears a date)
  python3 scripts/todo_register.py done TODO-001 [--note TEXT]
  python3 scripts/todo_register.py drop TODO-001 --reason TEXT       (the row stays; reason required)
  python3 scripts/todo_register.py ensure-from-commitment --com COM-001 --description "…" \\
      [--due YYYY-MM-DD] [--source …] [--priority …] [--initiative …] [--note …]
      Idempotent twin for a promise the PM owns: adds a to-do linked to that COM, or
      prints the existing open/in_progress/blocked to-do that already links it.
  python3 scripts/todo_register.py list [--filter open|overdue|due-today|due-week|blocked|done|dropped|all]
      [--initiative TEXT] [--blocks TEXT] [--id TODO-001] [--days N] [--json]
  python3 scripts/todo_register.py counts [--json]
  python3 scripts/todo_register.py log-proposal --offered N --accepted M [--source TEXT]
                                   (appends one line to logs/todo-proposals.csv for the monthly review)
  python3 scripts/todo_register.py plan (--ids TODO-001,TODO-002 | --filter due-week |
      --queue 1,3 | --sweep) [--queue-file PATH] [--out PATH]
      Queue numbers are promoted in this step (origin proposed). Writes
      outputs/todo-drafts/[date]-dispatch-plan.md. Does not dispatch.
  python3 scripts/todo_register.py reconcile [--count] [--projects-dir DIR]
      Propose likely-done open to-dos. Never changes status.

Register writes take an exclusive lock on state/todo-register.lock for the whole
read-modify-write, so parallel /todo dispatch workers cannot interleave CSV updates.
Dispatch itself is scripts/dispatch_todos.py.

Every command accepts --today YYYY-MM-DD (so tests and fixture runs are repeatable) and
--stdin, which reads the field values as one JSON object from standard input. Use --stdin
with a quoted heredoc when a value contains quotes, so the shell never has to escape it:
  python3 scripts/todo_register.py add --stdin <<'EOF'
  {"description": "Ask the support team about \\"silent\\" export failures"}
  EOF

Rules this script enforces itself, because the register hook only watches Write/Edit
tool calls and never sees a shell command writing the file:
  - the header must be exactly the one below, and rows are never removed or reordered
  - IDs are TODO-001, TODO-002, ... assigned by this script, never reused
  - an existing row only changes in the fields an update names; id, created and origin
    never change; last_updated is set to today
  - "remove" means status dropped with a reason; nothing is ever deleted
  - values are collapsed to a single line and quoted by the csv module
Exit codes: 0 ok, 1 usage or validation error, 2 integrity refusal (nothing was written).
"""
import argparse
import csv
import datetime
import fcntl
import io
import json
import os
import re
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "registers", "todos.csv")
HEADER = [
    "id", "description", "owner", "due_date", "priority", "status", "initiative",
    "blocks", "links", "origin", "source", "created", "last_updated", "note",
]
OPEN_STATUSES = ("open", "in_progress", "blocked")
UPDATABLE_STATUSES = ("open", "in_progress", "blocked")
PRIORITIES = ("high", "normal", "low")
ORIGINS = ("stated", "proposed", "commitment")
_COM_ID = re.compile(r"^COM-\d+$", re.IGNORECASE)
FILTERS = ("open", "overdue", "due-today", "due-week", "blocked", "done", "dropped", "all")
PRIORITY_RANK = {"high": 0, "normal": 1, "low": 2}
# field name on the command line -> column in the register
FIELD_COLUMNS = {
    "description": "description", "owner": "owner", "due": "due_date", "priority": "priority",
    "status": "status", "initiative": "initiative", "blocks": "blocks", "links": "links",
    "origin": "origin", "source": "source", "note": "note",
}


class Refused(Exception):
    """Integrity refusal: nothing was written."""


class Invalid(Exception):
    """Bad input: nothing was written."""


class register_lock:
    """Exclusive lock around a to-do register read-modify-write.

    fcntl.flock is per process, so two ``todo_register.py`` processes serialize.
    Do not acquire this twice in one process (it is not reentrant).
    ``TODO_REGISTER_LOCK_HOLD`` (seconds) and ``TODO_REGISTER_LOCK_TRACE`` (path)
    exist so tests can show the critical section does not overlap.
    """

    def __enter__(self):
        directory = os.path.join(ROOT, "state")
        os.makedirs(directory, exist_ok=True)
        self.path = os.path.join(directory, "todo-register.lock")
        self.handle = open(self.path, "a+", encoding="utf-8")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        self.trace = os.environ.get("TODO_REGISTER_LOCK_TRACE") or ""
        self.pid = str(os.getpid())
        self._log("acquire")
        hold = os.environ.get("TODO_REGISTER_LOCK_HOLD") or ""
        if hold:
            time.sleep(float(hold))
        return self

    def __exit__(self, exc_type, exc, tb):
        self._log("release")
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()
        return False

    def _log(self, event):
        if not self.trace:
            return
        with open(self.trace, "a", encoding="utf-8") as handle:
            handle.write(f"{self.pid} {event} {time.time():.6f}\n")


def one_line(value):
    """Rule 14: collapse any line breaks and runs of whitespace to single spaces."""
    return " ".join(str(value if value is not None else "").split())


def parse_date(text, label):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        raise Invalid(f"{label} must be a date like 2026-10-09, got {text!r}")


def today_from(args):
    if getattr(args, "today", None):
        return parse_date(args.today, "--today")
    return datetime.date.today()


def check_safe_target():
    registers_dir = os.path.dirname(REGISTER)
    if os.path.islink(registers_dir):
        raise Refused("registers/ is a symlink; refusing to write through it")
    if os.path.lexists(REGISTER):
        if os.path.islink(REGISTER) or not os.path.isfile(REGISTER) or os.stat(REGISTER).st_nlink > 1:
            raise Refused("registers/todos.csv is not a safe regular file (symlink, hard link or directory)")


def read_register():
    """Return the parsed rows (list of dicts). A missing or empty file is an empty register."""
    check_safe_target()
    if not os.path.exists(REGISTER):
        return []
    with open(REGISTER, newline="", encoding="utf-8") as handle:
        text = handle.read()
    if not text.strip():
        return []
    raw = list(csv.reader(io.StringIO(text)))
    if raw[0] != HEADER:
        raise Refused("registers/todos.csv header is not the expected one.\n"
                      f"  expected: {','.join(HEADER)}\n  found:    {','.join(raw[0])}")
    rows, seen = [], set()
    for number, fields in enumerate(raw[1:], start=2):
        if not any(cell.strip() for cell in fields):
            continue
        if len(fields) != len(HEADER):
            raise Refused(f"registers/todos.csv line {number}: {len(fields)} fields, header has {len(HEADER)}")
        row = dict(zip(HEADER, fields))
        if row["id"] in seen:
            raise Refused(f"registers/todos.csv line {number}: duplicate id {row['id']}")
        seen.add(row["id"])
        rows.append(row)
    return rows


def write_register(old_rows, new_rows):
    """Re-check the same invariants as the register hook, then replace the file atomically."""
    if len(new_rows) < len(old_rows):
        raise Refused("this write would lose rows; to-dos are never deleted (use drop)")
    if [r["id"] for r in new_rows[:len(old_rows)]] != [r["id"] for r in old_rows]:
        raise Refused("this write would delete, reorder or change an existing id")
    for row in new_rows:
        if len(row) != len(HEADER) or any(("\n" in v or "\r" in v) for v in row.values()):
            raise Refused(f"row {row.get('id')} has a bad field count or a line break")
    check_safe_target()
    os.makedirs(os.path.dirname(REGISTER), exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", newline="", encoding="utf-8", dir=os.path.dirname(REGISTER), delete=False,
        prefix=".todos-", suffix=".tmp")
    try:
        with handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(HEADER)
            for row in new_rows:
                writer.writerow([row[column] for column in HEADER])
        os.replace(handle.name, REGISTER)
    except BaseException:
        if os.path.exists(handle.name):
            os.unlink(handle.name)
        raise


def next_id(rows):
    highest = 0
    for row in rows:
        suffix = row["id"].rsplit("-", 1)[-1]
        if row["id"].startswith("TODO-") and suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"TODO-{highest + 1:03d}"


def normalize_id(text):
    value = one_line(text).upper()
    if value.isdigit():
        value = f"TODO-{int(value):03d}"
    return value


def find_row(rows, todo_id):
    wanted = normalize_id(todo_id)
    for row in rows:
        if row["id"] == wanted:
            return row
    raise Invalid(f"no to-do {wanted} in registers/todos.csv")


def collect_fields(args):
    """Field values given as flags and/or one JSON object on stdin. Flags win over stdin."""
    values = {}
    if getattr(args, "stdin", False):
        try:
            payload = json.load(sys.stdin)
        except ValueError as error:
            raise Invalid(f"--stdin expects one JSON object: {error}")
        if not isinstance(payload, dict):
            raise Invalid("--stdin expects one JSON object")
        unknown = sorted(set(payload) - set(FIELD_COLUMNS) - {"reason"})
        if unknown:
            raise Invalid(f"unknown field(s) in --stdin JSON: {', '.join(unknown)}")
        values.update(payload)
    for name in list(FIELD_COLUMNS) + ["reason"]:
        flag_value = getattr(args, name, None)
        if flag_value is not None:
            values[name] = flag_value
    return {name: one_line(value) for name, value in values.items()}


def validate(values):
    if "due" in values and values["due"]:
        parse_date(values["due"], "--due")
    if "priority" in values and values["priority"] not in PRIORITIES:
        raise Invalid(f"priority must be one of {', '.join(PRIORITIES)}, got {values['priority']!r}")
    if "origin" in values and values["origin"] not in ORIGINS:
        raise Invalid(f"origin must be one of {', '.join(ORIGINS)}, got {values['origin']!r}")
    if "status" in values and values["status"] not in UPDATABLE_STATUSES:
        raise Invalid("status via update must be open, in_progress or blocked; "
                      "use the done and drop commands to finish a to-do")


def join_note(existing, addition):
    existing, addition = one_line(existing), one_line(addition)
    if existing and addition:
        return f"{existing} | {addition}"
    return addition or existing


def format_table(rows, columns):
    def cell(value):
        text = one_line(value)
        return (text[:77] + "...") if len(text) > 80 else text
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(cell(row[c]).replace("|", "/") for c in columns) + " |")
    return "\n".join(lines)


def show_rows(rows, heading):
    print(heading)
    print(format_table(rows, ["id", "status", "priority", "due_date", "owner", "description",
                              "initiative", "blocks", "links", "note"]))


def cmd_add(args):
    with register_lock():
        _cmd_add(args)


def _cmd_add(args):
    values = collect_fields(args)
    validate(values)
    if not values.get("description"):
        raise Invalid("add needs a description")
    today = today_from(args).isoformat()
    rows = read_register()
    row = {column: "" for column in HEADER}
    row.update({
        "id": next_id(rows), "owner": "me", "priority": "normal", "status": "open",
        "origin": "stated", "created": today, "last_updated": today,
    })
    for name, column in FIELD_COLUMNS.items():
        if name in values and name != "status":
            row[column] = values[name]
    write_register(rows, rows + [row])
    show_rows([row], f"Added {row['id']}:")
    return row


def _link_tokens(value):
    return {token.upper() for token in _ID_IN_TEXT.findall(value or "")}


def _open_todo_for_com(rows, com_id):
    needle = com_id.upper()
    for row in rows:
        if (row.get("status") or "").strip() not in OPEN_STATUSES:
            continue
        if needle in _link_tokens(row.get("links") or ""):
            return row
    return None


def cmd_ensure_from_commitment(args):
    with register_lock():
        _cmd_ensure_from_commitment(args)


def _cmd_ensure_from_commitment(args):
    com = (args.com or "").strip().upper()
    if not _COM_ID.match(com):
        raise Invalid(f"com must look like COM-001, got {args.com!r}")
    # Reuse flag/stdin collection for description and optional fields; force twin metadata.
    collected = collect_fields(args)
    description = collected.get("description") or ""
    if not description:
        raise Invalid("ensure-from-commitment needs a description")
    values = {
        "description": description,
        "origin": "commitment",
        "links": com,
        "owner": "me",
    }
    for name in ("due", "source", "priority", "initiative", "note"):
        if name in collected and collected[name] != "":
            values[name] = collected[name]
        elif name == "due" and "due" in collected:
            values["due"] = ""
    validate(values)
    today = today_from(args).isoformat()
    rows = read_register()
    existing = _open_todo_for_com(rows, com)
    if existing:
        show_rows([existing], f"Already linked to {com}:")
        print(f"ensure-from-commitment: existing {existing['id']}")
        return existing
    row = {column: "" for column in HEADER}
    row.update({
        "id": next_id(rows), "owner": "me", "priority": "normal", "status": "open",
        "origin": "commitment", "created": today, "last_updated": today,
        "links": com,
    })
    for name, column in FIELD_COLUMNS.items():
        if name in values and name not in ("status", "origin", "links", "owner"):
            row[column] = values[name]
    write_register(rows, rows + [row])
    show_rows([row], f"Added {row['id']} (twin of {com}):")
    print(f"ensure-from-commitment: created {row['id']}")
    return row


def cmd_update(args):
    with register_lock():
        _cmd_update(args)


def _cmd_update(args):
    values = collect_fields(args)
    values.pop("reason", None)
    for locked in ("origin",):
        if locked in values:
            raise Invalid(f"{locked} cannot be changed after a to-do is created")
    validate(values)
    if not values:
        raise Invalid("update needs at least one field to change")
    if "description" in values and not values["description"]:
        raise Invalid("description cannot be empty")
    today = today_from(args).isoformat()
    rows = read_register()
    target = find_row(rows, args.id)
    updated = []
    for row in rows:
        if row is target:
            row = dict(row)
            for name, value in values.items():
                row[FIELD_COLUMNS[name]] = value
            row["last_updated"] = today
            target = row
        updated.append(row)
    write_register(rows, updated)
    show_rows([target], f"Updated {target['id']}:")


def finish(args, status, note_text, require_reason):
    with register_lock():
        _finish(args, status, note_text, require_reason)


def _finish(args, status, note_text, require_reason):
    values = collect_fields(args)
    if require_reason and not values.get("reason"):
        raise Invalid("drop needs --reason: say why this to-do is being dropped")
    addition = values.get("reason") if require_reason else values.get("note", "")
    today = today_from(args).isoformat()
    rows = read_register()
    target = find_row(rows, args.id)
    if target["status"] == status:
        raise Invalid(f"{target['id']} is already {status}")
    updated = []
    for row in rows:
        if row is target:
            row = dict(row)
            row["status"] = status
            row["note"] = join_note(row["note"], addition)
            row["last_updated"] = today
            target = row
        updated.append(row)
    write_register(rows, updated)
    show_rows([target], f"{note_text} {target['id']}:")


def cmd_done(args):
    finish(args, "done", "Marked done", require_reason=False)


def cmd_drop(args):
    finish(args, "dropped", "Dropped (row kept)", require_reason=True)


def due_of(row):
    try:
        return datetime.date.fromisoformat(row["due_date"])
    except ValueError:
        return None


def select(rows, args, today):
    chosen = []
    for row in rows:
        due = due_of(row)
        status = row["status"]
        is_open = status in OPEN_STATUSES
        keep = {
            "open": is_open,
            "overdue": is_open and due is not None and due < today,
            "due-today": is_open and due == today,
            "due-week": is_open and due is not None and today <= due <= today + datetime.timedelta(days=7),
            "blocked": status == "blocked",
            "done": status == "done" and recent(row, today, args.days),
            "dropped": status == "dropped" and recent(row, today, args.days),
            "all": True,
        }[args.filter]
        if keep and args.initiative and args.initiative.lower() not in row["initiative"].lower():
            keep = False
        if keep and args.blocks and args.blocks.lower() not in row["blocks"].lower():
            keep = False
        if keep and args.id and normalize_id(args.id) != row["id"]:
            keep = False
        if keep:
            chosen.append(row)

    def order(row):
        due = due_of(row)
        return (due is None, due or datetime.date.max, PRIORITY_RANK.get(row["priority"], 1), row["id"])
    return sorted(chosen, key=order)


def recent(row, today, days):
    try:
        changed = datetime.date.fromisoformat(row["last_updated"])
    except ValueError:
        return False
    return (today - changed).days <= days


def cmd_list(args):
    today = today_from(args)
    rows = read_register()
    chosen = select(rows, args, today)
    if args.json:
        print(json.dumps({"as_of": today.isoformat(), "filter": args.filter,
                          "total_rows": len(rows), "rows": chosen}, indent=2))
        return
    if not rows:
        print(f"No to-dos yet (as of {today.isoformat()}).")
        return
    if not chosen:
        print(f"No to-dos match filter '{args.filter}' (as of {today.isoformat()}; {len(rows)} row(s) in the register).")
        return
    print(f"To-dos, filter '{args.filter}', as of {today.isoformat()}: {len(chosen)} of {len(rows)} row(s)")
    print(format_table(chosen, ["id", "status", "priority", "due_date", "owner", "description",
                                "initiative", "blocks", "links"]))


def cmd_counts(args):
    today = today_from(args)
    rows = read_register()
    counts = {}
    for name in ("open", "overdue", "due-today", "blocked"):
        probe = argparse.Namespace(filter=name, initiative="", blocks="", id="", days=14)
        counts[name] = len(select(rows, probe, today))
    if args.json:
        print(json.dumps({"as_of": today.isoformat(), **counts}))
    else:
        print(f"To-dos as of {today.isoformat()}: {counts['due-today']} due today, "
              f"{counts['overdue']} overdue, {counts['blocked']} blocked, {counts['open']} open")


def cmd_log_proposal(args):
    if args.offered < 0 or args.accepted < 0 or args.accepted > args.offered:
        raise Invalid("--offered and --accepted must be whole numbers with accepted <= offered")
    path = os.path.join(ROOT, "logs", "todo-proposals.csv")
    directory = os.path.dirname(path)
    if os.path.islink(directory) or os.path.islink(path):
        raise Refused("logs/ or logs/todo-proposals.csv is a symlink; refusing to write through it")
    os.makedirs(directory, exist_ok=True)
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if new:
            writer.writerow(["date", "source", "offered", "accepted"])
        writer.writerow([today_from(args).isoformat(), one_line(args.source), args.offered, args.accepted])
    print(f"Logged: {args.accepted} of {args.offered} proposed to-dos accepted.")


REGISTER_FOR_PREFIX = {
    "EV": "registers/evidence.csv",
    "COM": "registers/commitments.csv",
    "DEC": "registers/decisions.csv",
    "RISK": "registers/risks.csv",
    "INIT": "registers/initiatives.csv",
    "TODO": "registers/todos.csv",
}
_ID_IN_TEXT = re.compile(r"\b(?:EV|COM|DEC|RISK|INIT|TODO)-\d+\b")
_COMPLETION = re.compile(r"\b(done|sent|finished|shipped|completed|closed out)\b", re.I)
_NEGATION = re.compile(r"\b(not|never|didn'?t|haven'?t|hasn'?t|won'?t)\b", re.I)
_USED_DRAFT = re.compile(r"\bused (the |this )?draft\b", re.I)


def _slug(description):
    slug = re.sub(r"[^a-z0-9]+", "-", (description or "").lower()).strip("-")
    return (slug[:40] or "todo").strip("-")


def _looks_like_path(text):
    text = (text or "").strip()
    if not text or len(text) > 180:
        return False
    if " " in text and "/" not in text:
        return False
    return "/" in text or text.endswith((".md", ".txt", ".csv", ".json", ".yml"))


def _guess_deliverable(description):
    text = (description or "").lower()
    if any(word in text for word in ("email", "slack", "message", "reply", "ask ", "send ", "ping ")):
        return "message"
    if any(word in text for word in ("research", "confirm", "find out", "look into", "investigate")):
        return "research plan"
    if any(word in text for word in ("jira", "ticket", "spike")):
        return "ticket draft"
    return "analysis"


def _files_for(row):
    files = []
    source = (row.get("source") or "").strip()
    if _looks_like_path(source) and source not in files:
        files.append(source)
    blob = " ".join(row.get(name) or "" for name in ("links", "source", "blocks", "note"))
    for token in _ID_IN_TEXT.findall(blob):
        path = REGISTER_FOR_PREFIX.get(token.split("-", 1)[0])
        if path and path not in files:
            files.append(path)
    return files[:12]


def _plan_item(row):
    files = _files_for(row)
    gaps = [] if files else ["[NEEDS INPUT: no source file or register links]"]
    deliverable = _guess_deliverable(row.get("description") or "")
    return {
        "id": row["id"],
        "description": row.get("description") or "",
        "deliverable": deliverable,
        "files": files,
        "gaps": gaps,
        "output": f"outputs/todo-drafts/{row['id']}-{_slug(row.get('description') or '')}.md",
        "size": "short" if deliverable == "message" else "medium",
        "note": row.get("note") or "",
        "links": row.get("links") or "",
    }


def _draft_newer_than(todo_id, last_updated):
    directory = os.path.join(ROOT, "outputs", "todo-drafts")
    if not os.path.isdir(directory):
        return ""
    try:
        updated = datetime.datetime.fromisoformat(last_updated)
    except ValueError:
        updated = None
    for name in sorted(os.listdir(directory)):
        if not (name.startswith(todo_id + "-") and name.endswith(".md")):
            continue
        path = os.path.join(directory, name)
        if updated is None or datetime.datetime.fromtimestamp(os.path.getmtime(path)) > updated:
            return os.path.relpath(path, ROOT)
    return ""


def _sweep_rows(rows, today):
    matched = []
    for row in rows:
        if row["status"] not in OPEN_STATUSES:
            continue
        if not ((row.get("source") or "").strip() or (row.get("links") or "").strip()):
            continue
        due = due_of(row)
        if due is None or due > today + datetime.timedelta(days=2):
            continue
        matched.append(row)
    matched.sort(key=lambda row: (
        due_of(row) or datetime.date.max,
        PRIORITY_RANK.get(row["priority"], 1),
        row["id"],
    ))
    return matched[:3]


def _split_table_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def _queue_is_reviewed(text):
    return any(line.strip().lower().startswith("reviewed ") for line in text.splitlines())


def _latest_queue_file():
    directory = os.path.join(ROOT, "outputs", "todo-proposals")
    if not os.path.isdir(directory):
        return ""
    names = sorted(name for name in os.listdir(directory) if name.endswith(".md"))
    for name in reversed(names):
        path = os.path.join(directory, name)
        with open(path, encoding="utf-8") as handle:
            if not _queue_is_reviewed(handle.read()):
                return path
    return ""


def parse_queue_items(text):
    """1-based candidates from a proposals file (table, numbers, or bullets)."""
    lines = text.splitlines()
    header_index = None
    for index, line in enumerate(lines):
        if not line.strip().startswith("|"):
            continue
        cells = [cell.lower() for cell in _split_table_row(line)]
        if any(cell == "description" or cell.startswith("description ") or cell.startswith("description(") for cell in cells):
            header_index = index
            header = []
            for cell in cells:
                if cell == "description" or cell.startswith("description ") or cell.startswith("description("):
                    header.append("description")
                elif cell.startswith("source"):
                    header.append("source")
                elif cell in ("#", "no", "no."):
                    header.append("number")
                else:
                    header.append(cell)
            break
    items = []
    if header_index is not None:
        for line in lines[header_index + 1:]:
            if not line.strip().startswith("|"):
                if items:
                    break
                continue
            if set(line.replace("|", "").strip()) <= {"-", ":", " "}:
                continue
            cells = _split_table_row(line)
            if len(cells) < len(header):
                cells = cells + [""] * (len(header) - len(cells))
            record = dict(zip(header, cells))
            description = record.get("description") or ""
            if not description or description.lower() == "description":
                continue
            number_text = cells[0]
            number = int(number_text) if number_text.isdigit() else len(items) + 1
            items.append({
                "number": number,
                "description": description,
                "owner": record.get("owner") or "",
                "due": record.get("due") or "",
                "priority": record.get("priority") or "",
                "initiative": record.get("initiative") or "",
                "blocks": record.get("blocks") or "",
                "links": record.get("links") or "",
                "source": record.get("source file") or record.get("source") or "",
            })
        return items
    for line in lines:
        stripped = line.strip()
        match = re.match(r"^(?:[-*]|\d+[.)])\s+(\S.*)$", stripped)
        if not match:
            continue
        description = match.group(1).strip()
        if description.lower().startswith("queued"):
            continue
        due_match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", description)
        links = ", ".join(_ID_IN_TEXT.findall(description))
        items.append({
            "number": len(items) + 1,
            "description": description,
            "owner": "",
            "due": due_match.group(1) if due_match else "",
            "priority": "",
            "initiative": "",
            "blocks": "",
            "links": links,
            "source": "",
        })
    return items


def _add_from_queue(item, today, source_path):
    """Promote one queue item. Caller must already hold register_lock."""
    item_source = (item.get("source") or "").strip()
    fields = {
        "description": item["description"],
        "origin": "proposed",
        "source": item_source or source_path,
    }
    for name in ("owner", "due", "priority", "initiative", "blocks", "links"):
        value = (item.get(name) or "").strip()
        if not value:
            continue
        if name == "priority" and value not in PRIORITIES:
            continue
        if name == "due":
            try:
                parse_date(value, "due")
            except Invalid:
                continue
        fields[name] = value
    namespace = argparse.Namespace(stdin=False, today=today, reason=None, status=None, **{
        column: fields.get(column) for column in (
            "description", "owner", "due", "priority", "initiative", "blocks",
            "links", "origin", "source", "note",
        )
    })
    _cmd_add(namespace)


def _write_dispatch_plan(path, today, mode, items, skipped):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload = {
        "date": today,
        "approved": False,
        "mode": mode,
        "items": items,
        "skipped": skipped,
    }
    lines = [
        f"# Dispatch plan {today}",
        "",
        "Status: PENDING APPROVAL",
        "Approved: no",
        "",
        "Nothing is dispatched until you approve. Add context with "
        "`todo_register.py update TODO-nnn --note ... --links ...`, edit this file, "
        "then set `Approved: yes`.",
        "",
        "| id | deliverable | files | gaps | output | size |",
        "|---|---|---|---|---|---|",
    ]
    for item in items:
        files = "; ".join(item["files"]) or "—"
        gaps = "; ".join(item["gaps"]) or "none"
        lines.append(
            "| {id} | {deliverable} | {files} | {gaps} | {output} | {size} |".format(
                id=item["id"],
                deliverable=item["deliverable"],
                files=files.replace("|", "/"),
                gaps=gaps.replace("|", "/"),
                output=item["output"],
                size=item["size"],
            )
        )
    if not items:
        lines.append("| — | — | — | — | — | — |")
    lines.append("")
    for item in items:
        gap_text = "; ".join(item["gaps"]) or "none"
        file_text = ", ".join(item["files"]) or "none"
        lines.extend([
            f"## {item['id']} — {item['description']}",
            "",
            f"- deliverable: {item['deliverable']}",
            f"- files: {file_text}",
            f"- gaps: {gap_text}",
            f"- output: {item['output']}",
            f"- size: {item['size']}",
            "",
        ])
    if skipped:
        lines.append("## Skipped")
        lines.append("")
        for item in skipped:
            lines.append(f"- {item['id']}: {item['reason']}")
        lines.append("")
    lines.append("```todo-plan")
    lines.append(json.dumps(payload, indent=2))
    lines.append("```")
    lines.append("")
    text = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    return text


def cmd_plan(args):
    today = today_from(args).isoformat()
    mode = "sweep" if args.sweep else "plan"
    promoted = []
    if args.queue:
        queue_path = args.queue_file or _latest_queue_file()
        if not queue_path or not os.path.isfile(queue_path):
            raise Invalid("no unreviewed queue file in outputs/todo-proposals/ (pass --queue-file)")
        with open(queue_path, encoding="utf-8") as handle:
            queue_text = handle.read()
        if _queue_is_reviewed(queue_text):
            raise Invalid(f"{queue_path} is already reviewed; pass a different --queue-file to promote again")
        wanted = {int(part) for part in re.split(r"[\s,]+", args.queue.strip()) if part}
        catalog = {item["number"]: item for item in parse_queue_items(queue_text)}
        missing = sorted(wanted - set(catalog))
        if missing:
            raise Invalid(f"queue has no item number(s): {', '.join(str(n) for n in missing)}")
        with register_lock():
            for number in sorted(wanted):
                item = catalog[number]
                rows = read_register()
                existing = {
                    one_line(row["description"]).casefold(): row["id"]
                    for row in rows if row["status"] in OPEN_STATUSES
                }
                prior = existing.get(one_line(item["description"]).casefold())
                if prior:
                    print(f"Queue {number} already open as {prior}; not added again.")
                    promoted.append(prior)
                    continue
                _add_from_queue(item, today, os.path.relpath(queue_path, ROOT))
                added = read_register()[-1]
                promoted.append(added["id"])
        if not queue_text.endswith("\n"):
            queue_text += "\n"
        with open(queue_path, "a", encoding="utf-8") as handle:
            numbers = ",".join(str(n) for n in sorted(wanted))
            handle.write(f"reviewed {today}: added {numbers} via /todo plan\n")
    rows = read_register()
    by_id = {row["id"]: row for row in rows}
    chosen = []
    skipped = []
    seen = set()

    def take(row, skip_reason=""):
        if row["id"] in seen:
            return
        seen.add(row["id"])
        if skip_reason:
            skipped.append({"id": row["id"], "reason": skip_reason})
            return
        chosen.append(row)

    for todo_id in promoted:
        row = by_id.get(todo_id)
        if row:
            take(row)
    if args.ids:
        for token in re.split(r"[\s,]+", args.ids.strip()):
            if not token:
                continue
            take(find_row(rows, token))
    if args.filter:
        if args.filter not in FILTERS:
            raise Invalid(f"--filter must be one of {', '.join(FILTERS)}")
        probe = argparse.Namespace(filter=args.filter, initiative="", blocks="", id="", days=14)
        for row in select(rows, probe, today_from(args)):
            take(row)
    if args.sweep:
        for row in _sweep_rows(rows, today_from(args)):
            newer = _draft_newer_than(row["id"], row.get("last_updated") or "")
            if newer:
                take(row, f"draft newer than last_updated ({newer})")
            else:
                take(row)
    if not args.queue and not args.ids and not args.filter and not args.sweep:
        raise Invalid("plan needs --ids, --filter, --queue, or --sweep")
    items = [_plan_item(row) for row in chosen]
    out = args.out or os.path.join(ROOT, "outputs", "todo-drafts", f"{today}-dispatch-plan.md")
    _write_dispatch_plan(out, today, mode, items, skipped)
    print(f"Wrote dispatch plan: {os.path.relpath(out, ROOT)}")
    print(f"items={len(items)} skipped={len(skipped)} promoted={len(promoted)}")
    print("Approve before dispatch. Context added with update goes on the to-do note and links.")


def _has_completion(text):
    for match in _COMPLETION.finditer(text or ""):
        prefix = text[max(0, match.start() - 40):match.start()]
        if _NEGATION.search(prefix):
            continue
        return True
    return False


def _mentions_completed(text, todo_id):
    haystack = text or ""
    lowered = haystack.lower()
    needle = todo_id.lower()
    start = 0
    while True:
        index = lowered.find(needle, start)
        if index < 0:
            return False
        window = haystack[max(0, index - 400):index + len(todo_id) + 400]
        if _has_completion(window) or (_USED_DRAFT.search(window) and "todo-drafts" in window.lower()):
            return True
        start = index + len(needle)


def _excerpt(text, limit=180):
    return " ".join((text or "").split())[:limit]


def _reconcile_evidence(rows, today, projects_dirs):
    open_rows = [row for row in rows if row["status"] in OPEN_STATUSES]
    proposals = []
    if not open_rows:
        return proposals
    dates = []
    for row in open_rows:
        try:
            dates.append(datetime.date.fromisoformat(row.get("last_updated") or ""))
        except ValueError:
            pass
    earliest = min(dates) if dates else today
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import transcripts
    files = transcripts.session_files(projects_dirs)
    cutoff = datetime.datetime.combine(earliest, datetime.time.min).timestamp()
    recent_files = []
    for path in files:
        try:
            if path.stat().st_mtime >= cutoff:
                recent_files.append(path)
        except OSError:
            continue
    turns = list(transcripts.iter_user_turns(recent_files))
    commitments_path = os.path.join(ROOT, "registers", "commitments.csv")
    commitments = []
    if os.path.isfile(commitments_path):
        with open(commitments_path, newline="", encoding="utf-8") as handle:
            commitments = list(csv.DictReader(handle))
    output_hits = []
    outputs_root = os.path.join(ROOT, "outputs")
    if os.path.isdir(outputs_root):
        for dirpath, _dirs, names in os.walk(outputs_root):
            for name in names:
                if not name.endswith(".md"):
                    continue
                if name.endswith("-reconcile.md") or name.endswith("-dispatch-plan.md"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    text = open(path, encoding="utf-8", errors="replace").read()
                except OSError:
                    continue
                output_hits.append((os.path.relpath(path, ROOT), text))
    for row in open_rows:
        todo_id = row["id"]
        try:
            since = datetime.date.fromisoformat(row.get("last_updated") or "")
        except ValueError:
            since = earliest
        found = []
        for turn in turns:
            stamp = (turn.timestamp or "")[:10]
            try:
                if datetime.date.fromisoformat(stamp) < since:
                    continue
            except ValueError:
                continue
            if not _mentions_completed(turn.text, todo_id):
                continue
            found.append({
                "kind": "transcript",
                "evidence": _excerpt(turn.text),
                "source": f"transcript {turn.session_id} @ {turn.timestamp} ({turn.path})",
            })
        for rel, text in output_hits:
            if _mentions_completed(text, todo_id):
                found.append({
                    "kind": "output",
                    "evidence": _excerpt(text[text.lower().find(todo_id.lower()):][:180] or text),
                    "source": rel,
                })
        for commitment in commitments:
            status = (commitment.get("status") or "").strip().lower()
            if status != "done":
                continue
            blob = " ".join(str(value) for value in commitment.values())
            if not re.search(rf"\b{re.escape(todo_id)}\b", blob):
                continue
            found.append({
                "kind": "commitment",
                "evidence": _excerpt(commitment.get("description") or blob),
                "source": f"registers/commitments.csv {commitment.get('id') or ''}".strip(),
            })
        if found:
            proposals.append({"id": todo_id, "description": row.get("description") or "", "evidence": found})
    return proposals


def _write_reconcile(path, today, proposals):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = [
        f"# Likely done {today}",
        "",
        "Nothing in registers/todos.csv was marked done. Confirm, then run "
        "`todo_register.py done` for each id you accept.",
        "",
        "| id | evidence | source |",
        "|---|---|---|",
    ]
    if not proposals:
        lines.append("| — | none | — |")
    for proposal in proposals:
        for item in proposal["evidence"]:
            lines.append(
                "| {id} | {evidence} | {source} |".format(
                    id=proposal["id"],
                    evidence=item["evidence"].replace("|", "/"),
                    source=item["source"].replace("|", "/"),
                )
            )
    lines.extend(["", "```reconcile", json.dumps({"date": today, "likely_done": proposals}, indent=2), "```", ""])
    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def cmd_reconcile(args):
    """Propose likely-done to-dos. Never changes status."""
    before = ""
    if os.path.isfile(REGISTER):
        with open(REGISTER, encoding="utf-8") as handle:
            before = handle.read()
    today = today_from(args)
    rows = read_register()
    projects = None
    if args.projects_dir:
        projects = [os.path.abspath(os.path.expanduser(part))
                    for part in args.projects_dir.split(",") if part.strip()]
    proposals = _reconcile_evidence(rows, today, projects)
    if os.path.isfile(REGISTER):
        with open(REGISTER, encoding="utf-8") as handle:
            after = handle.read()
        if after != before:
            raise Refused("reconcile must not change registers/todos.csv")
    if args.count:
        print(f"likely_done={len(proposals)}")
        for proposal in proposals:
            print(f"likely {proposal['id']}")
        return
    out = args.out or os.path.join(
        ROOT, "outputs", "todo-drafts", f"{today.isoformat()}-reconcile.md")
    _write_reconcile(out, today.isoformat(), proposals)
    print(f"likely_done={len(proposals)}")
    print(f"Wrote reconcile proposal: {os.path.relpath(out, ROOT)}")
    print("Status was not changed. Confirm before done.")
    if args.json:
        print(json.dumps({"as_of": today.isoformat(), "likely_done": proposals}, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p, fields):
        p.add_argument("--today", help="override today's date (YYYY-MM-DD), for repeatable runs")
        p.add_argument("--stdin", action="store_true", help="read field values as one JSON object on stdin")
        for name in fields:
            p.add_argument(f"--{name}")

    add = sub.add_parser("add")
    common(add, [n for n in FIELD_COLUMNS if n != "status"])
    add.set_defaults(func=cmd_add)

    update = sub.add_parser("update")
    update.add_argument("id")
    common(update, list(FIELD_COLUMNS))
    update.set_defaults(func=cmd_update)

    done = sub.add_parser("done")
    done.add_argument("id")
    common(done, ["note"])
    done.set_defaults(func=cmd_done)

    drop = sub.add_parser("drop")
    drop.add_argument("id")
    common(drop, ["reason"])
    drop.set_defaults(func=cmd_drop)

    ensure = sub.add_parser(
        "ensure-from-commitment",
        help="idempotent to-do twin for a COM the PM owns",
    )
    ensure.add_argument("--com", required=True, help="COM-nnn id to link")
    common(ensure, ["description", "due", "source", "priority", "initiative", "note"])
    ensure.set_defaults(func=cmd_ensure_from_commitment)

    listing = sub.add_parser("list")
    listing.add_argument("--filter", choices=FILTERS, default="open")
    listing.add_argument("--initiative", default="")
    listing.add_argument("--blocks", default="")
    listing.add_argument("--id", default="")
    listing.add_argument("--days", type=int, default=14, help="window for the done and dropped filters")
    listing.add_argument("--json", action="store_true")
    listing.add_argument("--today")
    listing.set_defaults(func=cmd_list)

    counts = sub.add_parser("counts")
    counts.add_argument("--json", action="store_true")
    counts.add_argument("--today")
    counts.set_defaults(func=cmd_counts)

    proposal = sub.add_parser("log-proposal")
    proposal.add_argument("--offered", type=int, required=True)
    proposal.add_argument("--accepted", type=int, required=True)
    proposal.add_argument("--source", default="")
    proposal.add_argument("--today")
    proposal.set_defaults(func=cmd_log_proposal)

    plan = sub.add_parser("plan")
    plan.add_argument("--ids", default="", help="comma-separated TODO ids or bare numbers")
    plan.add_argument("--filter", default="", help="open|overdue|due-today|due-week|blocked|done|dropped|all")
    plan.add_argument("--queue", default="", help="1-based queue item numbers to promote, e.g. 1,3,5")
    plan.add_argument("--queue-file", default="", help="proposals file; default is the latest unreviewed queue")
    plan.add_argument("--sweep", action="store_true", help="sweep selection: due within 2 days, with source or links, max 3")
    plan.add_argument("--out", default="", help="dispatch plan path")
    plan.add_argument("--today")
    plan.set_defaults(func=cmd_plan)

    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--count", action="store_true", help="print likely_done=N only; write nothing")
    reconcile.add_argument("--json", action="store_true")
    reconcile.add_argument("--out", default="")
    reconcile.add_argument("--projects-dir", default="", help="comma-separated Claude project dirs of *.jsonl")
    reconcile.add_argument("--today")
    reconcile.set_defaults(func=cmd_reconcile)
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        args.func(args)
    except Invalid as error:
        sys.stderr.write(f"todo_register: {error}\n")
        return 1
    except Refused as error:
        sys.stderr.write(f"todo_register: REFUSED, nothing was written. {error}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
