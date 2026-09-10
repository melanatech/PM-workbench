#!/usr/bin/env python3
"""Copy a fixture (fixtures/<name>/) into the live workspace folders.

Usage: python3 scripts/load_fixture.py lumenly [--force]

Refuses to overwrite a register that already has rows unless --force, so you
can't wipe real work by accident. Everything else (inbox files, roadmap,
current-priorities) is copied over.
"""
import sys, os, shutil
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
name = next((a for a in sys.argv[1:] if not a.startswith('--')), 'lumenly')
force = '--force' in sys.argv
src = os.path.join(root, 'fixtures', name)
if not os.path.isdir(src):
    sys.exit(f"no fixture at {src}")
copied, skipped = [], []
for d, _, files in os.walk(src):
    for f in files:
        if f == 'README.md' and d == src:
            continue
        s = os.path.join(d, f)
        rel = os.path.relpath(s, src)
        t = os.path.join(root, rel)
        if rel.startswith('registers') and os.path.exists(t) and not force:
            with open(t, encoding='utf-8') as fh:
                if len([l for l in fh if l.strip()]) > 1:
                    skipped.append(rel); continue
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copyfile(s, t); copied.append(rel)
os.makedirs(os.path.join(root, "state"), exist_ok=True)
open(os.path.join(root, "state", ".last-check"), "w").write("fixture loaded")
print("loaded fixture:", name)
for c in copied: print("  +", c)
for s_ in skipped: print("  skipped (has rows; use --force):", s_)
