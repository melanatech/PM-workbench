#!/usr/bin/env python3
"""One-time cleanup after two session-memory fixes. Dry run unless --apply.

  python3 migrate_keys.py --root <project folder> [--root <another>] [--apply]

1. Registers filed under a subfolder key are merged into the project key. Before the fix, session
   memory keyed by the folder the agent had moved into, so one chat could have registers in several
   folders and /pickup (which looks under the project) found none of them.
2. Saved transcripts of hook model calls (voice checks, register updates, related-work checks) are
   moved out of ~/.claude/projects into <data home>/headless-archive. They were saved as sessions and
   fill the resume list. Moved, never deleted. Real chats are not touched: a transcript moves only if
   its first user message starts with one of the plumbing prompts below and it is short.

Standard library only.
"""
import argparse
import json
import os
import re
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "hooks"))
import common as c  # noqa: E402

PLUMBING_PROMPTS = (
    "Judge this team-facing draft",
    "# Session register instructions (headless model)",
    "Does this new prompt continue one of these earlier sessions",
)
MAX_PLUMBING_ROWS = 120      # a hook call is a few dozen rows; a real chat is far longer
RECENT_SECONDS = 120         # leave anything written in the last two minutes alone
UUID_FILE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def encode_memory(path):
    return path.replace("/", "-")


def encode_claude(path):
    return re.sub(r"[/.]", "-", path)


def resolves_under(root, name, encode):
    """True when folder `name` is the encoded form of a folder inside `root` (or root itself)."""
    root = os.path.abspath(root)
    if name == encode(root):
        return True

    def walk(here):
        try:
            children = sorted(os.listdir(here))
        except OSError:
            return False
        for child in children:
            path = os.path.join(here, child)
            enc = encode(path)
            if enc == name:
                return True
            if name.startswith(enc + "-") and os.path.isdir(path) and walk(path):
                return True
        return False

    return name.startswith(encode(root) + "-") and walk(root)


# ---- registers ----

def merge_entries(sources):
    """Merge register entries from several files of one session. Ids are renumbered; `supersedes`
    follows the renumbering within each source. The newest Where it stands wins. Goal lines stay, so a later to-do does not erase the subject."""
    tagged = []
    for n, entries in enumerate(sources):
        for pos, entry in enumerate(entries):
            tagged.append((str(entry.get("date") or ""), n, pos, entry))
    tagged.sort(key=lambda row: (row[0], row[1], row[2]))
    mapping, merged = {}, []
    for _date, n, _pos, entry in tagged:
        new_id = f"e{len(merged) + 1}"
        mapping[(n, entry.get("id"))] = new_id
        supersedes = [mapping[(n, old)] for old in entry.get("supersedes") or [] if (n, old) in mapping]
        merged.append({**entry, "id": new_id, "supersedes": supersedes})
    for section in ("Where it stands",):
        ids = [e["id"] for e in merged if e.get("section") == section]
        if len(ids) > 1:
            last = next(e for e in merged if e["id"] == ids[-1])
            last["supersedes"] = sorted(set(last["supersedes"]) | set(ids[:-1]), key=lambda i: int(i[1:]))
    return merged


def write_entries(path, entries):
    with open(path, "w", encoding="utf-8") as handle:
        for entry in entries:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def merge_index(into, other):
    for sid, rec in other.items():
        have = into.get(sid)
        if not have:
            into[sid] = rec
            continue
        have["first"] = min(have.get("first") or rec.get("first") or "", rec.get("first") or have.get("first") or "")
        have["captures"] = have.get("captures", 0) + rec.get("captures", 0)
        have["last"] = max(have.get("last") or "", rec.get("last") or "")
        goals = []
        for goal in [have.get("goal"), rec.get("goal"), *(have.get("goals") or []), *(rec.get("goals") or [])]:
            if goal and goal not in goals:
                goals.append(goal)
        if goals:
            have["goals"] = goals
            have.setdefault("goal", goals[0])
        picked = list(dict.fromkeys((have.get("picked_from") or []) + (rec.get("picked_from") or [])))
        if picked:
            have["picked_from"] = picked
    return into


def read_json(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return [line for line in handle.read().splitlines() if line.strip()]
    except OSError:
        return []


def plan_registers(home, roots):
    """Folders under the data home that belong to a root but are not the root's own key."""
    plans = []
    try:
        names = sorted(os.listdir(home))
    except OSError:
        return plans
    for root in roots:
        dest = encode_memory(os.path.abspath(root))
        for name in names:
            path = os.path.join(home, name)
            if name == dest or not os.path.isdir(path):
                continue
            if resolves_under(root, name, encode_memory):
                plans.append((root, dest, name))
    return plans


def merge_folder(home, dest, name, apply):
    """Merge one subfolder key into the project key. Returns counts."""
    src, dst = os.path.join(home, name), os.path.join(home, dest)
    counts = {"registers": 0, "merged": 0, "other": 0}
    files = sorted(os.listdir(src))
    if apply:
        os.makedirs(dst, exist_ok=True)
    for f in files:
        path = os.path.join(src, f)
        if f.endswith(".lock") or not os.path.isfile(path):
            continue
        target = os.path.join(dst, f)
        if f == "index.json":
            if apply:
                write_json = merge_index(read_json(target), read_json(path))
                with open(target, "w", encoding="utf-8") as handle:
                    json.dump(write_json, handle, indent=1, ensure_ascii=False)
            counts["other"] += 1
        elif f == "log.jsonl":
            if apply:
                rows = read_lines(target) + read_lines(path)
                rows.sort(key=lambda line: (json.loads(line).get("ts", "") if line.startswith("{") else ""))
                with open(target, "w", encoding="utf-8") as handle:
                    handle.write("\n".join(rows) + "\n")
            counts["other"] += 1
        elif f.endswith(".jsonl") and UUID_FILE.match(f):
            counts["registers"] += 1
            if os.path.exists(target):
                counts["merged"] += 1
                if apply:
                    write_entries(target, merge_entries([c.load_entries(target), c.load_entries(path)]))
            elif apply:
                shutil.move(path, target)
        elif f.endswith(".reading.json"):
            if apply and (not os.path.exists(target) or os.path.getmtime(path) > os.path.getmtime(target)):
                shutil.copy2(path, target)
            counts["other"] += 1
        # anything else (job temp files) is left where it is
    if apply:
        for f in os.listdir(src):
            if f.endswith(".lock") or f in ("index.json", "log.jsonl") or f.endswith(".reading.json") \
                    or (f.endswith(".jsonl") and UUID_FILE.match(f)):
                try:
                    os.remove(os.path.join(src, f))
                except OSError:
                    pass
        try:
            os.rmdir(src)
        except OSError:
            pass
    return counts


# ---- hook-run transcripts ----

def first_user_text(path, limit=120):
    rows = 0
    first = None
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                rows += 1
                if rows > limit:
                    return None, rows
                if first is not None:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("type") == "user":
                    text = c.user_text(row)
                    if text is not None:
                        first = text
    except OSError:
        return None, rows
    return first, rows


def is_plumbing(path):
    text, rows = first_user_text(path, MAX_PLUMBING_ROWS)
    if text is None or rows > MAX_PLUMBING_ROWS:
        return False
    return text.lstrip().startswith(PLUMBING_PROMPTS)


def plan_transcripts(projects, roots):
    """(folder name, file path) for every hook-run transcript inside a root's project folders."""
    found = []
    try:
        names = sorted(os.listdir(projects))
    except OSError:
        return found
    now = time.time()
    for name in names:
        folder = os.path.join(projects, name)
        if not os.path.isdir(folder):
            continue
        if not any(resolves_under(root, name, encode_claude) for root in roots):
            continue
        for f in sorted(os.listdir(folder)):
            path = os.path.join(folder, f)
            if not (f.endswith(".jsonl") and os.path.isfile(path)):
                continue
            if now - os.path.getmtime(path) < RECENT_SECONDS:
                continue
            if is_plumbing(path):
                found.append((name, path))
    return found


def archive_transcripts(found, archive, apply):
    moved = {}
    for name, path in found:
        moved[name] = moved.get(name, 0) + 1
        if not apply:
            continue
        folder = os.path.join(archive, name)
        os.makedirs(folder, exist_ok=True)
        shutil.move(path, os.path.join(folder, os.path.basename(path)))
        companion = path[:-6]
        if os.path.isdir(companion):
            shutil.move(companion, os.path.join(folder, os.path.basename(companion)))
    return moved


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", action="append", help="project folder (repeatable); default: this folder's project")
    parser.add_argument("--home", default=c.data_home(), help="session-memory data home")
    parser.add_argument("--projects", default=os.path.expanduser("~/.claude/projects"))
    parser.add_argument("--apply", action="store_true", help="do it; without this, only report")
    args = parser.parse_args(argv)
    roots = [os.path.abspath(os.path.expanduser(r)) for r in (args.root or [c.project_root()])]
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"{mode}: roots {', '.join(roots)}")

    print("\nRegisters filed under a subfolder key")
    plans = plan_registers(args.home, roots)
    total = {"registers": 0, "merged": 0}
    for root, dest, name in plans:
        counts = merge_folder(args.home, dest, name, args.apply)
        total["registers"] += counts["registers"]
        total["merged"] += counts["merged"]
        print(f"  {name}: {counts['registers']} registers ({counts['merged']} also exist in the project key)")
    print(f"  total: {len(plans)} folders, {total['registers']} registers, {total['merged']} merged with an existing one")

    print("\nHook-run transcripts saved as sessions")
    found = plan_transcripts(args.projects, roots)
    moved = archive_transcripts(found, os.path.join(args.home, "headless-archive"), args.apply)
    for name, n in sorted(moved.items()):
        print(f"  {name}: {n}")
    print(f"  total: {len(found)} to {os.path.join(args.home, 'headless-archive')}")
    if not args.apply:
        print("\nNothing was changed. Run again with --apply.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
