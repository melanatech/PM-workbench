#!/usr/bin/env python3
"""Checks a Rhythms check-in file against the Rhythms export (My_OKRs.csv).

Usage: python3 scripts/check_rhythms_checkin.py <checkin.md> [export.csv]

Every export row that is not closed, or is closed at 0%, must have a row in the
Entries table with a Status, a Score in 0.1 steps (0 to 1) and a Note. Key results
(value goals) need a Current value; other OKRs need a Progress %.
"""
import csv, re, sys

path = sys.argv[1]
export = sys.argv[2] if len(sys.argv) > 2 else 'archive/metrics/My_OKRs.csv'
ex = {e['Short ID']: e for e in csv.DictReader(open(export, encoding='utf-8-sig'))}
text = open(path, encoding='utf-8').read()
entries = {}
for line in text.split('\n'):
    if re.match(r'^\| (OBJ|KR|INIT)-\d+ \|', line):
        c = [x.strip() for x in line.strip()[1:-1].split(' | ')]
        entries[c[0]] = c
need = [i for i, e in ex.items() if e['OKR Status'] != 'closed' or float(e['Progress'] or 0) == 0]
errors = []
for i in need:
    if i not in entries: errors.append(f"{i}: needs a check-in but is not in the Entries table"); continue
    _, name, cur, prog, status, score, note = (entries[i] + [''] * 7)[:7]
    if not status: errors.append(f"{i}: missing Status")
    if not note: errors.append(f"{i}: missing Note")
    if not re.fullmatch(r'(0(\.\d)?|1(\.0)?)', score): errors.append(f"{i}: Score '{score}' is not a 0.1 step from 0 to 1")
    if ex[i]['Type'] == 'key_result' and not re.match(r'^-?\d', cur): errors.append(f"{i}: key result needs a Current value")
    if ex[i]['Type'] != 'key_result' and not re.match(r'^\d+%', prog): errors.append(f"{i}: needs a Progress %")
for i in entries:
    if i not in need: errors.append(f"{i}: in the Entries table but closed above 0% in the export")
print(f"export rows: {len(ex)}; need a check-in: {len(need)}; entries: {len(entries)}")
for e in errors: print('FAIL', e)
print('OK' if not errors else f'{len(errors)} problem(s)')
sys.exit(1 if errors else 0)
