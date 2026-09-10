#!/usr/bin/env python3
"""Deterministic numbers for /workbench-health. The command narrates; this script counts,
so the model never estimates its own usage. Stdlib only."""
import os, csv, glob, datetime, collections, re
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root)
now = datetime.datetime.now()
cmds = sorted(os.path.basename(p)[:-3] for p in glob.glob('.claude/commands/*.md')) + \
       sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob('.claude/skills/*/SKILL.md'))
runs, blocked, failed = collections.Counter(), [], []
last = {}
if os.path.exists('logs/run-log.csv'):
    for r in csv.DictReader(open('logs/run-log.csv', encoding='utf-8', errors='replace')):
        w = (r.get('workflow') or '').strip().lstrip('/')
        if not w: continue
        runs[w] += 1; last[w] = r.get('timestamp', '')
        s = (r.get('success') or '').lower()
        if s == 'blocked' or 'BLOCKED' in (r.get('note') or ''): blocked.append(r)
        elif s and s not in ('ok', 'true', 'yes', '1', 'success'): failed.append(r)
print("# Workbench health —", now.strftime('%Y-%m-%d'))
print(f"\n## Runs logged: {sum(runs.values())}  (since {min(last.values()) if last else 'n/a'})")
print("\n| workflow | runs | last run |")
print("|---|---|---|")
for c in cmds:
    print(f"| /{c} | {runs.get(c, 0)} | {last.get(c, '—')[:16] if c in last else 'never'} |")
extra = [w for w in runs if w not in cmds]
if extra: print("\nLogged names that match no command (renamed? typo?):", ", ".join(extra))
never = [c for c in cmds if c not in runs]
print(f"\n## Never run ({len(never)}): " + ", ".join('/' + c for c in never))
print(f"\n## Blocked scheduled runs: {len(blocked)}")
for r in blocked[-10:]: print(" -", r.get('timestamp', '')[:16], r.get('workflow'), '—', r.get('note', ''))
print(f"\n## Failed runs: {len(failed)}")
for r in failed[-10:]: print(" -", r.get('timestamp', '')[:16], r.get('workflow'), '—', r.get('note', ''))
print("\n## Registers")
for p in sorted(glob.glob('registers/*.csv')):
    n = max(0, sum(1 for l in open(p, encoding='utf-8', errors='replace') if l.strip()) - 1)
    print(f" - {p}: {n} rows, {os.path.getsize(p)//1024} KB")
inbox = [p for p in glob.glob('inbox/**/*', recursive=True) if os.path.isfile(p)]
old = [p for p in inbox if (now - datetime.datetime.fromtimestamp(os.path.getmtime(p))).days > 3]
print(f"\n## Inbox: {len(inbox)} unprocessed file(s), {len(old)} older than 3 days")
for p in old[:10]: print(" -", p)
stubs = [s for s in ('scripts/log_metrics.py', 'scripts/extract_document.sh', 'scripts/render_template.py') if os.path.exists(s) and 'is a stub' in open(s, errors='replace').read()]
print(f"\n## Stub scripts still unimplemented: {', '.join(stubs) or 'none'}")
br = [l for l in open('CLAUDE.md', encoding='utf-8', errors='replace').read().splitlines()[:30] if re.search(r'\[[A-Z][A-Z /~-]{3,}\]', l)]
print(f"\n## CLAUDE.md brackets still unfilled: {len(br)}")
for l in br[:6]: print("  ", l.strip()[:110])
if os.path.exists('BACKLOG.md'):
    items = [l.strip() for l in open('BACKLOG.md', encoding='utf-8') if l.strip().startswith('- [ ]')]
    print(f"\n## BACKLOG open items: {len(items)}")
    for l in items[:8]: print("  ", l[:110])
