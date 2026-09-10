#!/usr/bin/env python3
"""Move clips saved by the Workbench Clipper (Downloads/pm-workbench-inbox/<category>/*.md)
into inbox/<category>/. Cross-platform (macOS, Windows, Linux). Idempotent."""
import os, shutil, sys
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
home = os.path.expanduser('~')
candidates = [os.path.join(home, 'Downloads', 'pm-workbench-inbox'),
              os.path.join(home, 'OneDrive', 'Downloads', 'pm-workbench-inbox')]
src = next((c for c in candidates if os.path.isdir(c)), None)
if not src:
    print("no clips folder found (expected ~/Downloads/pm-workbench-inbox/)"); sys.exit(0)
moved = 0
for cat in sorted(os.listdir(src)):
    d = os.path.join(src, cat)
    if not os.path.isdir(d): continue
    dest = os.path.join(root, 'inbox', cat if cat in ('discovery','competitive','meetings','metrics','documents','captures') else 'captures')
    os.makedirs(dest, exist_ok=True)
    for f in sorted(os.listdir(d)):
        if not f.endswith('.md'): continue
        shutil.move(os.path.join(d, f), os.path.join(dest, f)); moved += 1
        print("  +", os.path.relpath(os.path.join(dest, f), root))
print(f"moved {moved} clip(s)")
