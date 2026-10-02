#!/usr/bin/env python3
"""todo_register.py — add, update, finish, drop and list rows in registers/todos.csv.

The /todo command calls this script so dates, IDs and CSV quoting are handled by
code instead of by a model hand-editing a CSV (CLAUDE.md rule 14). Standard
library only; no network, no model.

Usage (run from the workbench root)
  python3 scripts/todo_register.py add --description "Ask support about export retries" \\
      [--owner me] [--due 2026-10-09] [--priority high|normal|low] [--initiative NAME] \\
      [--blocks "PRD for Bulk Export"] [--links "EV-211, RISK-008"] \\
      [--origin stated|proposed] [--source "inbox/meetings/..."] [--note TEXT]
  python3 scripts/todo_register.py update TODO-001 [--description ...] [--owner ...] [--due ...]
      [--priority ...] [--status open|in_progress|blocked] [--initiative ...] [--blocks ...]
      [--links ...] [--source ...] [--note ...]        (--due "" clears a date)
  python3 scripts/todo_register.py done TODO-001 [--note TEXT]
  python3 scripts/todo_register.py drop TODO-001 --reason TEXT       (the row stays; reason required)
  python3 scripts/todo_register.py list [--filter open|overdue|due-today|due-week|blocked|done|dropped|all]
      [--initiative TEXT] [--blocks TEXT] [--id TODO-001] [--days N] [--json]
  python3 scripts/todo_register.py counts [--json]
  python3 scripts/todo_register.py log-proposal --offered N --accepted M [--source TEXT]
                                   (appends one line to logs/todo-proposals.csv for the monthly review)

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
import io
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "registers", "todos.csv")
HEADER = [
    "id", "description", "owner", "due_date", "priority", "status", "initiative",
    "blocks", "links", "origin", "source", "created", "last_updated", "note",
]
OPEN_STATUSES = ("open", "in_progress", "blocked")
UPDATABLE_STATUSES = ("open", "in_progress", "blocked")
PRIORITIES = ("high", "normal", "low")
ORIGINS = ("stated", "proposed")
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


def cmd_update(args):
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
