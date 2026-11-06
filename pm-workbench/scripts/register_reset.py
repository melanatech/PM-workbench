#!/usr/bin/env python3
"""register_reset.py — fresh start for the registers without deleting anything (Plan E Part 1, step 8a).

  python3 scripts/register_reset.py --root ~/pm-live                  # dry run: print the carry-forward batch
  python3 scripts/register_reset.py --root ~/pm-live --write-proposal # save it to outputs/registers/ to tick
  python3 scripts/register_reset.py --root ~/pm-live --apply --keep keep.txt
                                     # keep.txt: the first id on each line is kept (the saved batch works
                                     # as-is after deleting unwanted lines); `#` lines ignored

--apply first copies every file in registers/ plus reference/context/assumptions-and-open-questions.md,
unchanged, to archive/registers-<YYYY-MM-DD>/. The archive is the full history; anything citing an old id
still resolves there. Then each register is rewritten with its current header and only the kept rows. Ids
keep their values. The highest id in each register is always carried (marked in the batch) so the next new
row continues numbering past the archive. Evidence and research-participants are history only: they are
archived and start empty. The open-questions file is archived, not rewritten; resolve bullets in place.
The reset is logged to logs/run-log.csv and noted in reference/context/current-priorities.md (rule 16).
Run it after the supersedes migration, so reversed decisions are already excluded.
"""
import argparse
import csv
import datetime
import glob
import io
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import register_view  # noqa: E402
from workspace_layout import REGISTER_HEADERS  # noqa: E402

STALE_DAYS = 60
OPEN_QUESTIONS = os.path.join("reference", "context", "assumptions-and-open-questions.md")
HISTORY_ONLY = {"evidence.csv", "research-participants.csv"}
CLOSED = {"done", "closed", "resolved", "mitigated", "dropped", "cancelled", "canceled", "retired", "killed"}
RULES = {
    "decisions.csv": ("date", None),
    "commitments.csv": ("last_updated", "status"),
    "risks.csv": ("date_raised", "status"),
    "todos.csv": ("last_updated", "status"),
    "initiatives.csv": ("last_updated", "stage"),
}


def parse_day(text):
    try:
        return datetime.date.fromisoformat((text or "").strip()[:10])
    except ValueError:
        return None


def id_number(rid):
    m = re.search(r"(\d+)$", rid or "")
    return int(m.group(1)) if m else -1


def read(path):
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames or [], list(reader)


def recent_output_text(root, today):
    cutoff = datetime.datetime.combine(today - datetime.timedelta(days=STALE_DAYS), datetime.time())
    chunks = []
    for path in glob.glob(os.path.join(root, "outputs", "**", "*.md"), recursive=True):
        if datetime.datetime.fromtimestamp(os.path.getmtime(path)) >= cutoff:
            try:
                chunks.append(open(path, encoding="utf-8", errors="replace").read())
            except OSError:
                pass
    return "\n".join(chunks)


def batch(root, today):
    """{register: [(id, kind, reasons)]} where kind is 'carry', 'sequence' or 'archive-only'."""
    out, recent = {}, recent_output_text(root, today)
    for name, (date_col, status_col) in RULES.items():
        path = os.path.join(root, "registers", name)
        if not os.path.isfile(path):
            continue
        _, rows = read(path)
        if name == "decisions.csv":
            candidates = register_view.active_rows(rows)
            later_affects = {}
            for r in rows:
                later_affects.setdefault((r.get("affects") or "").strip().lower(), []).append(r.get("id", "").strip())
        else:
            candidates = [r for r in rows if (r.get(status_col) or "").strip().lower() not in CLOSED]
        top = max((r.get("id", "").strip() for r in rows), key=id_number, default="")
        items = []
        for r in candidates:
            rid = r.get("id", "").strip()
            reasons = []
            day = parse_day(r.get(date_col))
            if day and (today - day).days > STALE_DAYS:
                reasons.append(f"older than {STALE_DAYS} days ({day})")
            if rid and rid not in recent:
                reasons.append(f"not mentioned in outputs from the last {STALE_DAYS} days")
            if name == "decisions.csv":
                key = (r.get("affects") or "").strip().lower()
                newer = [x for x in later_affects.get(key, []) if id_number(x) > id_number(rid)] if key else []
                if newer:
                    reasons.append(f"a later decision has the same affects value ({', '.join(newer[:3])})")
            items.append((rid, "carry", reasons))
        if top and top not in {i[0] for i in items}:
            items.append((top, "sequence", ["highest id; carried so new ids continue past the archive"]))
        out[name] = items
    return out


def render(proposal, today):
    lines = [f"# Register reset: carry-forward batch ({today})", "",
             "Tier 2 batch. Delete the lines for rows you do not want to keep, save the ids as keep.txt, then run "
             "`python3 scripts/register_reset.py --apply --keep keep.txt`. Everything is archived first.", ""]
    for name, items in proposal.items():
        lines += [f"## {name} ({len(items)} proposed)", ""]
        for rid, kind, reasons in items:
            note = "; ".join(reasons) if reasons else "no stale signal"
            lines.append(f"- [x] {rid} — {'keep (sequence)' if kind == 'sequence' else 'might be stale: ' + note if reasons else note}")
        lines.append("")
    lines.append("Evidence and research-participants are history only: archived, not carried.")
    return "\n".join(lines) + "\n"


def archive(root, today):
    dest = os.path.join(root, "archive", f"registers-{today}")
    if os.path.isdir(dest) and os.listdir(dest):
        raise SystemExit(f"{os.path.relpath(dest, root)} already exists; move it aside before a second reset today")
    os.makedirs(dest, exist_ok=True)
    for path in glob.glob(os.path.join(root, "registers", "*")):
        if os.path.isfile(path):
            shutil.copy2(path, dest)
    if os.path.isfile(os.path.join(root, OPEN_QUESTIONS)):
        shutil.copy2(os.path.join(root, OPEN_QUESTIONS), dest)
    return dest


def apply(root, keep, today):
    dest = archive(root, today)
    kept_total = 0
    for name, header in REGISTER_HEADERS.items():
        path = os.path.join(root, "registers", name)
        if not os.path.isfile(path):
            continue
        fields = header.split(",")
        _, rows = read(path)
        keep_rows = [] if name in HISTORY_ONLY else [r for r in rows if r.get(fields[0], "").strip() in keep]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore", restval="")
        writer.writeheader()
        writer.writerows(keep_rows)
        with open(path, "w", newline="", encoding="utf-8") as handle:
            handle.write(buf.getvalue())
        kept_total += len(keep_rows)
    rel_dest = os.path.relpath(dest, root)
    log = os.path.join(root, "logs", "run-log.csv")
    os.makedirs(os.path.dirname(log), exist_ok=True)
    new = not os.path.exists(log) or os.path.getsize(log) == 0
    with open(log, "a", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        if new:
            writer.writerow(["timestamp", "workflow", "approx_duration_min", "success", "note"])
        writer.writerow([datetime.datetime.now().isoformat(timespec="seconds"), "register-reset", "", "ok",
                         f"registers reset; {kept_total} rows carried; full history in {rel_dest}"])
    prio = os.path.join(root, "reference", "context", "current-priorities.md")
    os.makedirs(os.path.dirname(prio), exist_ok=True)
    with open(prio, "a", encoding="utf-8") as handle:
        handle.write(f"\n- {today}: registers were reset; rows not carried forward are in `{rel_dest}/` "
                     "(missing ids there are archived, not never-existing).\n")
    return rel_dest, kept_total


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--keep", help="file of ids to keep, one per line")
    parser.add_argument("--write-proposal", action="store_true")
    parser.add_argument("--today", help="YYYY-MM-DD, for repeatable runs")
    args = parser.parse_args(argv)
    root = os.path.abspath(os.path.expanduser(args.root)) if args.root else register_view._resolve_root()
    today = datetime.date.fromisoformat(args.today) if args.today else datetime.date.today()
    if args.apply:
        if not args.keep:
            print("--apply needs --keep <file of ticked ids>", file=sys.stderr)
            return 2
        with open(args.keep, encoding="utf-8") as handle:
            first_ids = (re.search(r"\b[A-Z]+-\d+\b", line) for line in handle if not line.lstrip().startswith("#"))
            keep = {m.group(0) for m in first_ids if m}
        dest, kept = apply(root, keep, today.isoformat())
        print(f"archived to {dest}; {kept} rows carried forward")
        return 0
    text = render(batch(root, today), today.isoformat())
    if args.write_proposal:
        out = os.path.join(root, "outputs", "registers", f"{today.isoformat()}-register-reset-proposal.md")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"wrote {os.path.relpath(out, root)}")
        return 0
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
