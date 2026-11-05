#!/usr/bin/env python3
"""PreToolUse hook on Write|Edit for registers/*.csv.

Enforces CLAUDE.md rule 14 mechanically: a register row that would break the CSV
(wrong field count, unquoted comma, multi-line cell, duplicate id, header change)
is rejected BEFORE it lands, and Claude is told exactly what to fix.
"""
import sys, os, csv, io
sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, rel, block, warn

CURRENT_STATE_REGISTERS = {'commitments.csv', 'risks.csv', 'initiatives.csv', 'todos.csv'}

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
    if existing.strip():
        old_rows = list(csv.reader(io.StringIO(existing)))
        old_hdr = old_rows[0]
        if hdr != old_hdr:
            block(f"REGISTER HEADER CHANGED in {r}. Keep the header exactly: {','.join(old_hdr)}")
        old_records = [x for x in old_rows[1:] if any(c.strip() for c in x)]
        new_records = [x for x in rows[1:] if any(c.strip() for c in x)]
        old_count, new_count = len(old_records), len(new_records)
        if new_count < old_count:
            block(f"{r} would lose rows ({old_count} -> {new_count}). Keep existing records and append new rows.")
        old_ids = [x[0].strip() if x else '' for x in old_records]
        new_ids = [x[0].strip() if x else '' for x in new_records]
        if new_ids[:len(old_ids)] != old_ids:
            block(f"{r} would delete, reorder, or change an existing record ID. Keep existing IDs in order.")
        if os.path.basename(r) not in CURRENT_STATE_REGISTERS and new_records[:len(old_records)] != old_records:
            block(f"{r} contains immutable history. Do not edit prior rows; append a correction or new event instead.")
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
