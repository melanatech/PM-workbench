#!/usr/bin/env python3
"""PreToolUse hook on Write|Edit for registers/*.csv.

Enforces CLAUDE.md rule 14 mechanically: a register row that would break the CSV
(wrong field count, unquoted comma, multi-line cell, duplicate id, header change)
is rejected BEFORE it lands, and Claude is told exactly what to fix.

decisions.csv: the one-time header migration that appends a `supersedes` column (every
old row kept, padded with an empty cell) is allowed, and a `supersedes` value must name
earlier DEC- ids (this file or archive/registers-*/), never itself. A file that
scripts/register_reset.py archived byte-for-byte today may be replaced by a smaller one.
"""
import sys, os, csv, io, re, glob, datetime
sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, rel, block, warn

CURRENT_STATE_REGISTERS = {'commitments.csv', 'risks.csv', 'initiatives.csv', 'todos.csv'}
SUPERSEDES_REGISTERS = {'decisions.csv'}

try:
    p = payload()
    ti = p.get('tool_input', {}) or {}
    path = ti.get('file_path') or ''
    r = rel(path)
    if not r.startswith('registers/') or not r.endswith('.csv'):
        sys.exit(0)
    full = os.path.join(root(), r)
    existing = open(full, encoding='utf-8').read() if os.path.exists(full) else ''
    if p.get('tool_name') == 'Write':
        new = ti.get('content', '')
    else:  # Edit
        old_s, new_s = ti.get('old_string', ''), ti.get('new_string', '')
        if old_s and old_s not in existing:
            sys.exit(0)  # Claude Code will fail this edit itself
        new = existing.replace(old_s, new_s, 1) if old_s else existing + new_s
    rows = list(csv.reader(io.StringIO(new)))
    if not rows:
        sys.exit(0)
    hdr = rows[0]
    base = os.path.basename(r)
    today_archive = os.path.join(root(), 'archive', f'registers-{datetime.date.today().isoformat()}', base)
    if existing.strip():
        old_rows = list(csv.reader(io.StringIO(existing)))
        old_hdr = old_rows[0]
        old_records = [x for x in old_rows[1:] if any(c.strip() for c in x)]
        new_records = [x for x in rows[1:] if any(c.strip() for c in x)]
        migrating = base in SUPERSEDES_REGISTERS and hdr == old_hdr + ['supersedes']
        if migrating:
            if new_records[:len(old_records)] != [x + [''] for x in old_records]:
                block(f"{r}: adding the supersedes column must leave every existing row unchanged with an empty "
                      "supersedes cell. Links for old rows come from `python3 scripts/propose_supersedes.py` after approval.")
            old_records = [x + [''] for x in old_records]
        elif hdr != old_hdr:
            block(f"REGISTER HEADER CHANGED in {r}. Keep the header exactly: {','.join(old_hdr)}")
        reset = os.path.isfile(today_archive) and open(today_archive, encoding='utf-8').read() == existing
        old_count, new_count = len(old_records), len(new_records)
        if reset:
            pass  # scripts/register_reset.py archived this exact file today; a smaller fresh file is expected
        elif new_count < old_count:
            block(f"{r} would lose rows ({old_count} -> {new_count}). Keep existing records and append new rows.")
        old_ids = [x[0].strip() if x else '' for x in old_records]
        new_ids = [x[0].strip() if x else '' for x in new_records]
        if not reset and new_ids[:len(old_ids)] != old_ids:
            block(f"{r} would delete, reorder, or change an existing record ID. Keep existing IDs in order.")
        if not reset and base not in CURRENT_STATE_REGISTERS and new_records[:len(old_records)] != old_records:
            block(f"{r} contains immutable history. Do not edit prior rows; append a correction or new event instead.")
    if base in SUPERSEDES_REGISTERS and 'supersedes' in hdr:
        col = hdr.index('supersedes')
        archived = set()
        for old_file in glob.glob(os.path.join(root(), 'archive', 'registers-*', base)):
            with open(old_file, encoding='utf-8', errors='replace') as fh:
                archived.update((x[0] or '').strip() for x in list(csv.reader(fh))[1:] if x)
        seen = set()
        for i, row in enumerate(rows[1:], start=2):
            if not any(c.strip() for c in row):
                continue
            rid = row[0].strip()
            cell = row[col] if col < len(row) else ''
            for old in [x.strip() for x in cell.split(';') if x.strip()]:
                if old == rid:
                    block(f"{r} line {i}: {rid} supersedes itself. List only earlier DEC- ids it overrides.")
                if not re.fullmatch(r'DEC-\d+', old):
                    block(f"{r} line {i}: supersedes '{old}' is not a DEC- id. Use DEC-nnn ids separated by ';'.")
                if old not in seen and old not in archived:
                    block(f"{r} line {i}: {rid} supersedes {old}, which is not an earlier row in this file "
                          "or in archive/registers-*/. Point it at the decision it overrides.")
            seen.add(rid)
    ids = set()
    for i, row in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in row):
            continue
        if len(row) != len(hdr):
            block(f"{r} line {i}: {len(row)} fields but the header has {len(hdr)}. Quote any field containing a comma (rule 14). Row: {row}")
        if any('\n' in c or '\r' in c for c in row):
            block(f"{r} line {i}: a cell contains a line break. Collapse it to one line (rule 14).")
        rid = row[0].strip()
        if rid in ids:
            block(f"{r} line {i}: duplicate id {rid}. Use the next unused id.")
        ids.add(rid)
    sys.exit(0)
except SystemExit:
    raise
except Exception as e:
    warn(f"validate_register_write skipped: {e}")
