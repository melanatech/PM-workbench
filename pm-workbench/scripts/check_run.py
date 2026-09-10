#!/usr/bin/env python3
"""check_run.py — did the last workflow run do what it said?

Run it after any command. It reads what changed since the last check (or since
--since <minutes>) and reports, in order of severity:

  FAIL  something the kit's rules forbid actually happened
  WARN  something that is probably fine but you should look at
  OK    what was verified

Checks
  1. Register integrity   every registers/*.csv parses; every row has the header's
                          column count; IDs are unique; no multi-line cells.
  2. ID provenance        every DEC-/COM-/RISK-/EV-/INIT- ID cited in a changed
                          output or register exists in a register. Every LUM-/JIRA
                          style ticket key cited exists in an inbox export.
  3. Run log              logs/run-log.csv gained a line for this run.
  4. Write scope          changed files are inside inbox/ archive/ outputs/
                          registers/ state/ logs/ learning/ reference/ prototypes/
                          drafts/ — nothing else moved.
  5. Fact provenance      dates, percentages, money and quoted phrases in changed
                          outputs appear somewhere in the inputs (inbox/, registers/,
                          reference/, state/). Strict by default; --lenient reports
                          these as WARN instead of FAIL.
  6. Completion claims    a changed output that says "posted", "sent", "published",
                          "submitted", "applied" is flagged unless it also says
                          "draft", "not posted", "awaiting approval" or "verified".

Usage
  python3 scripts/check_run.py                # everything changed since the last check (or fixture load)
  python3 scripts/check_run.py --since 120    # last 2 hours
  python3 scripts/check_run.py --lenient      # fact provenance as warnings
  python3 scripts/check_run.py --all          # ignore timestamps, check the whole workspace

Exit code: 1 if any FAIL, else 0. No network, no model, stdlib only.
"""
import sys, os, re, csv, io, time, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ARGS = sys.argv[1:]
LENIENT = '--lenient' in ARGS
ALL = '--all' in ARGS
SINCE_MIN = 30
if '--since' in ARGS:
    SINCE_MIN = float(ARGS[ARGS.index('--since') + 1])
MARK = os.path.join(ROOT, 'state', '.last-check')
if ALL:
    CUTOFF = 0
elif '--since' in ARGS:
    CUTOFF = time.time() - SINCE_MIN * 60
elif os.path.exists(MARK):
    CUTOFF = os.path.getmtime(MARK)          # everything since the last check / fixture load
else:
    CUTOFF = time.time() - SINCE_MIN * 60
def mark():
    os.makedirs(os.path.dirname(MARK), exist_ok=True)
    open(MARK, 'w').write(time.strftime('%Y-%m-%dT%H:%M:%S'))

ALLOWED_DIRS = ('inbox/', 'archive/', 'outputs/', 'registers/', 'state/', 'logs/',
                'learning/', 'reference/', 'prototypes/', 'drafts/', 'repos/', 'roadmap/')
INPUT_DIRS = ('inbox/', 'archive/', 'registers/', 'reference/', 'state/', 'fixtures/')
SKIP = ('.git/', 'node_modules/', '.claude/', 'fixtures/', 'scripts/', 'tools/')

fails, warns, oks = [], [], []
def FAIL(m): fails.append(m)
def WARN(m): warns.append(m)
def OK(m): oks.append(m)

def walk(prefixes=None):
    for d, _, files in os.walk('.'):
        rel = os.path.relpath(d, '.').replace(os.sep, '/')
        rel = '' if rel == '.' else rel + '/'
        if any(rel.startswith(s) for s in SKIP): continue
        for f in files:
            p = rel + f
            if prefixes and not p.startswith(prefixes): continue
            yield p

def read(p):
    try:
        with open(p, encoding='utf-8', errors='replace') as fh: return fh.read()
    except Exception: return ''

# ---------- what changed ----------
changed = [p for p in walk() if os.path.getmtime(p) >= CUTOFF]
changed = [p for p in changed if not p.endswith(('.png', '.jpg', '.webp', '.pdf', '.docx', '.pptx', '.xlsx'))]
if not changed:
    print("Nothing changed since the last check (use --since N or --all).")
    mark(); sys.exit(0)

# ---------- 4. write scope ----------
outside = [p for p in changed if not p.startswith(ALLOWED_DIRS) and p not in ('BACKLOG.md',)]
if outside: FAIL("files changed outside the allowed working folders: " + ", ".join(outside))
else: OK(f"{len(changed)} changed file(s), all inside allowed folders")

# ---------- 1. register integrity ----------
ids = {}
tickets = set()
for p in sorted(glob.glob('registers/*.csv')):
    txt = read(p)
    if not txt.strip(): continue
    try:
        rows = list(csv.reader(io.StringIO(txt)))
    except Exception as e:
        FAIL(f"{p}: does not parse as CSV ({e})"); continue
    hdr = rows[0]
    for i, r in enumerate(rows[1:], start=2):
        if not any(c.strip() for c in r): continue
        if len(r) != len(hdr):
            FAIL(f"{p} line {i}: {len(r)} fields, header has {len(hdr)} — unquoted comma or broken row")
        if any('\n' in c for c in r):
            FAIL(f"{p} line {i}: multi-line cell (CLAUDE.md rule 14: collapse to one line)")
        rid = r[0].strip()
        if rid:
            if rid in ids: FAIL(f"{p} line {i}: duplicate id {rid} (first seen in {ids[rid]})")
            ids[rid] = p
    OK(f"{p}: {max(0, len(rows) - 1)} row(s), well-formed")

# ticket keys present in inputs
for p in walk(INPUT_DIRS):
    tickets |= set(re.findall(r'\b[A-Z]{2,6}-\d{2,6}\b', read(p)))
tickets = {t for t in tickets if not re.match(r'(DEC|COM|RISK|EV|INIT|OKR)-', t)}

# ---------- 2 + 5 + 6: outputs ----------
input_blob = "\n".join(read(p) for p in walk(INPUT_DIRS)).lower()
ID_RE = re.compile(r'\b(?:DEC|COM|RISK|EV|INIT)-\d{3,5}\b')
TICKET_RE = re.compile(r'\b[A-Z]{2,6}-\d{2,6}\b')
DATE_RE = re.compile(r'\b(20\d\d-\d\d-\d\d|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.? \d{1,2})\b')
NUM_RE = re.compile(r'\b\d+(?:\.\d+)?\s?(?:%|pp\b|pts\b|[kKM]\b)|\$\s?\d[\d,]*(?:\.\d+)?')
QUOTE_RE = re.compile(r'[“"]([^"”]{12,120})[”"]')
CLAIM_RE = re.compile(r'\b(posted|sent|published|submitted|applied|updated the ticket|moved the ticket)\b', re.I)
SAFE_RE = re.compile(r'\b(draft|not posted|not sent|awaiting approval|proposed|pending|verified|re-read)\b', re.I)

outputs = [p for p in changed if p.startswith(('outputs/', 'drafts/', 'registers/', 'learning/'))]
for p in outputs:
    txt = read(p)
    if not txt.strip(): continue
    # 2. IDs
    for m in sorted(set(ID_RE.findall(txt))):
        if m not in ids:
            FAIL(f"{p}: cites {m}, which exists in no register — an ID the run invented or never wrote")
    for t in sorted(set(TICKET_RE.findall(txt)) - set(ID_RE.findall(txt)) - set(re.findall(r'\bOKR-\d+\b', txt))):
        if t not in tickets:
            (WARN if LENIENT else FAIL)(f"{p}: cites ticket {t}, which appears in no inbox export or register — did the run see a board, or guess?")
    if not p.startswith('registers/'):
        low = txt.lower()
        # 5. facts
        for d in sorted(set(DATE_RE.findall(txt))):
            if d.lower() not in input_blob:
                (WARN if LENIENT else FAIL)(f"{p}: date '{d}' appears in no input")
        for n in sorted(set(NUM_RE.findall(txt))):
            if n.lower().replace(' ', '') not in input_blob.replace(' ', ''):
                (WARN if LENIENT else FAIL)(f"{p}: figure '{n}' appears in no input")
        for q in sorted(set(QUOTE_RE.findall(txt))):
            if q.lower() not in input_blob:
                (WARN if LENIENT else FAIL)(f"{p}: quoted phrase \"{q[:60]}…\" appears in no input — a customer quote must be verbatim from a source")
        # 6. completion claims
        for m in CLAIM_RE.finditer(txt):
            window = txt[max(0, m.start() - 160): m.end() + 160]
            if not SAFE_RE.search(window):
                WARN(f"{p}: says '{m.group(0)}' near \"…{txt[max(0,m.start()-40):m.end()+40].strip()}…\" with no draft/approval/verified qualifier nearby — is this a claim of a completed external write?")
    OK(f"{p}: provenance checked")

# ---------- 3. run log ----------
rl = 'logs/run-log.csv'
ran = any(p.startswith(('outputs/', 'registers/', 'drafts/', 'learning/')) for p in changed)
if not ran:
    OK("no outputs or registers changed — no workflow run to log (fixture load or inbox drop only)")
elif os.path.exists(rl) and os.path.getmtime(rl) >= CUTOFF:
    lines = [l for l in read(rl).splitlines() if l.strip()]
    OK(f"run log has {len(lines) - 1} line(s); last: {lines[-1][:100] if len(lines) > 1 else '(header only)'}")
else:
    FAIL("logs/run-log.csv did not gain a line — rule 19 not honored (or the run-log hook is not installed)")

# ---------- report ----------
for m in fails: print("FAIL ", m)
for m in warns: print("WARN ", m)
for m in oks:   print("OK   ", m)
print(f"\n{len(fails)} fail · {len(warns)} warn · {len(oks)} ok")
mark()
sys.exit(1 if fails else 0)
