#!/usr/bin/env python3
"""Stop hook: append one line to logs/run-log.csv for the turn that just ended,
IF that turn invoked a workbench command. Enforces CLAUDE.md rule 19 without
relying on the model remembering to do it.

Reads the session transcript (JSONL) that Claude Code passes in, finds the last
user message, and records the /command it started with. Plain-language turns
that routed to a command are logged as 'chat' unless the transcript shows a
Skill invocation.
"""
import sys, os, json, csv, datetime
sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, warn

try:
    p = payload()
    if p.get('stop_hook_active'):
        sys.exit(0)
    tp = p.get('transcript_path')
    if not tp or not os.path.exists(tp):
        sys.exit(0)
    cmd, last_user_ts, blocked = None, None, False
    with open(tp, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            try: ev = json.loads(line)
            except Exception: continue
            msg = ev.get('message') or {}
            role = msg.get('role') or ev.get('type')
            content = msg.get('content')
            if isinstance(content, list):
                texts = [c.get('text', '') for c in content if isinstance(c, dict) and c.get('type') == 'text']
                skills = [c.get('input', {}).get('skill') or c.get('input', {}).get('command') for c in content if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') in ('Skill',)]
                text = "\n".join(texts)
            else:
                text, skills = (content or ''), []
            if role == 'user' and text.strip() and not text.startswith('<'):
                cmd = None; blocked = False
                last_user_ts = ev.get('timestamp')
                first = text.strip().split()[0] if text.strip() else ''
                if first.startswith('/'):
                    cmd = first.lstrip('/').split(':')[-1]
            elif role == 'assistant':
                for s_ in skills:
                    if s_: cmd = str(s_).lstrip('/')
                if 'BLOCKED:' in text: blocked = True
    if not cmd:
        sys.exit(0)  # ordinary chat turn — not a workflow run
    logp = os.path.join(root(), 'logs', 'run-log.csv')
    os.makedirs(os.path.dirname(logp), exist_ok=True)
    new = not os.path.exists(logp) or os.path.getsize(logp) == 0
    dur = ''
    if last_user_ts:
        try:
            t0 = datetime.datetime.fromisoformat(last_user_ts.replace('Z', '+00:00'))
            dur = str(round((datetime.datetime.now(datetime.timezone.utc) - t0).total_seconds() / 60, 1))
        except Exception:
            pass
    with open(logp, 'a', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh, lineterminator='\n')
        if new: w.writerow(['timestamp', 'workflow', 'approx_duration_min', 'success', 'note'])
        w.writerow([datetime.datetime.now().isoformat(timespec='seconds'), cmd, dur, 'blocked' if blocked else 'ok', 'logged by hook'])
    sys.exit(0)
except SystemExit:
    raise
except Exception as e:
    warn(f"log_run skipped: {e}")
