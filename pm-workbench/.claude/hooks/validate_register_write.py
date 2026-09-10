#!/usr/bin/env python3
"""PreToolUse hook on Write|Edit for registers/*.csv.

Enforces CLAUDE.md rule 14 mechanically: a register row that would break the CSV
(wrong field count, unquoted comma, multi-line cell, duplicate id, header change)
is rejected BEFORE it lands, and Claude is told exactly what to fix.
"""
import sys, os, csv, io
sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, rel, block, warn

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
        old_hdr = next(csv.reader(io.StringIO(existing)))
        if hdr != old_hdr:
            block(f"REGISTER HEADER CHANGED in {r}. Registers are append-only (rule 7); keep the header exactly: {','.join(old_hdr)}")
        old_count = len([x for x in csv.reader(io.StringIO(existing)) if any(c.strip() for c in x)])
        new_count = len([x for x in rows if any(c.strip() for c in x)])
        if new_count < old_count:
            block(f"{r} would lose rows ({old_count} -> {new_count}). Registers are append-only (rule 7). Append, never rewrite.")
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
