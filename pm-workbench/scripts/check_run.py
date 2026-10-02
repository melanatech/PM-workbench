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
  2. ID provenance        every DEC-/COM-/RISK-/EV-/INIT-/TODO- ID cited in a changed
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

Coverage limits
  This is a heuristic local check, not a semantic review or a security boundary.
  Changed-file checks use modification times (so edits with preserved/old
  timestamps are not detected). A path/content inventory in state/.last-check
  detects files removed since the last successful check, even when timestamps
  cannot help. An unchanged inbox file moved into archive/ is treated as a move,
  not a deletion. Deletions before the first inventory is established (or since
  an older baseline with no inventory) cannot be detected; the first successful
  check or fixture load bootstraps that inventory. The checker checks only the
  patterns above and does not verify external systems or whether cited sources
  are truthful. Register
  integrity is checked across registers/*.csv when the check window contains a
  changed file; provenance is checked only for changed outputs, drafts,
  registers, and learning files. A no-change shortcut skips all checks except
  deletion detection; use
  --all for a full runtime-workspace pass. A run-log check confirms a new row
  relative to the last successful baseline, but cannot prove that the row
  accurately describes the run. Hooks remain a separate, fail-open check.

Usage
  python3 scripts/check_run.py                # everything changed since the last check (or fixture load)
  python3 scripts/check_run.py --since 120    # last 2 hours
  python3 scripts/check_run.py --lenient      # fact provenance as warnings
  python3 scripts/check_run.py --all          # ignore timestamps, check the runtime workspace

Exit code: 1 if any FAIL, else 0. No network, no model, stdlib only.
"""
import sys, os, re, csv, io, time, glob, hashlib
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ARGS = sys.argv[1:]
LENIENT = '--lenient' in ARGS
ALL = '--all' in ARGS
SINCE_MIN = 30
if '--since' in ARGS:
    SINCE_MIN = float(ARGS[ARGS.index('--since') + 1])
MARK = os.path.join(ROOT, 'state', '.last-check')
if os.path.islink(os.path.dirname(MARK)) or os.path.islink(MARK) or (
    os.path.lexists(MARK)
    and (not os.path.isfile(MARK) or os.stat(MARK).st_nlink > 1)
):
    print("Unsafe state/.last-check path; refusing to read or write the checker baseline.", file=sys.stderr)
    sys.exit(2)
BASELINE_RUN_LOG_ROWS = None
BASELINE_CUTOFF = None
BASELINE_INVENTORY = None
if os.path.exists(MARK):
    try:
        with open(MARK, encoding='utf-8') as baseline_file:
            baseline = json.load(baseline_file)
        if isinstance(baseline.get('cutoff'), (int, float)):
            BASELINE_CUTOFF = float(baseline['cutoff'])
        if isinstance(baseline.get('run_log_rows'), int):
            BASELINE_RUN_LOG_ROWS = baseline['run_log_rows']
        if isinstance(baseline.get('inventory'), dict):
            inventory = baseline['inventory']
            if all(isinstance(path, str) and isinstance(digest, str)
                   for path, digest in inventory.items()):
                BASELINE_INVENTORY = inventory
            else:
                print("Invalid file inventory in state/.last-check; refusing to check against it.", file=sys.stderr)
                sys.exit(2)
    except (OSError, ValueError, AttributeError):
        # Older installations used free text here; its modification time is
        # retained as the baseline until a successful check upgrades the marker.
        BASELINE_CUTOFF = os.path.getmtime(MARK)
    if BASELINE_CUTOFF is None:
        BASELINE_CUTOFF = os.path.getmtime(MARK)
if ALL:
    CUTOFF = 0
elif '--since' in ARGS:
    CUTOFF = time.time() - SINCE_MIN * 60
elif BASELINE_CUTOFF is not None:
    CUTOFF = BASELINE_CUTOFF
else:
    CUTOFF = time.time() - SINCE_MIN * 60

def mark(cutoff=None, run_log_rows=None, inventory=None, include_inventory=True):
    os.makedirs(os.path.dirname(MARK), exist_ok=True)
    baseline = {'checked_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
                'cutoff': time.time() if cutoff is None else cutoff,
                'run_log_rows': run_log_row_count() if run_log_rows is None else run_log_rows}
    if include_inventory:
        baseline['inventory'] = file_inventory() if inventory is None else inventory
    with open(MARK, 'w', encoding='utf-8') as marker:
        json.dump(baseline, marker)

def retain_failed_baseline():
    # A first failed check has no prior marker to retain. Save its cutoff and
    # run-log count without advancing them so later checks repeat the same scan.
    # An explicit broader scan may widen the retained window, never narrow it.
    if BASELINE_CUTOFF is None or CUTOFF < BASELINE_CUTOFF:
        mark(cutoff=CUTOFF,
             run_log_rows=BASELINE_RUN_LOG_ROWS if BASELINE_RUN_LOG_ROWS is not None
             else run_log_row_count(),
             inventory=BASELINE_INVENTORY,
             include_inventory=BASELINE_INVENTORY is not None)

ALLOWED_DIRS = ('inbox/', 'archive/', 'outputs/', 'registers/', 'state/', 'logs/',
                'learning/', 'reference/', 'prototypes/', 'drafts/', 'repos/', 'roadmap/')
INPUT_DIRS = ('inbox/', 'archive/', 'registers/', 'reference/', 'state/', 'fixtures/')
SKIP = ('.git/', 'node_modules/', '.claude/', 'fixtures/', 'scripts/', 'tools/', 'tests/')
PROJECT_FILES = {
    'AGENTS.md', 'CLAUDE.md', 'CONNECTIONS.md', 'EVOLVING.md', 'SCHEDULING.md',
    'SETUP.md', 'SKILLS.md', 'SOURCE-POLICY.md', 'START HERE.md', 'STATE-BACKUP.md',
    'Capture Clipboard.command', 'Run PM Workflow.command', '.gitignore',
}

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
            if p == 'state/.last-check':
                continue
            if rel == '' and p in PROJECT_FILES:
                continue
            if prefixes and not p.startswith(prefixes): continue
            yield p

def file_inventory():
    inventory = {}
    for path in walk():
        digest = hashlib.sha256()
        try:
            with open(path, 'rb') as handle:
                for chunk in iter(lambda: handle.read(65536), b''):
                    digest.update(chunk)
        except OSError:
            continue
        inventory[path] = digest.hexdigest()
    return inventory

def read(p):
    try:
        with open(p, encoding='utf-8', errors='replace') as fh: return fh.read()
    except Exception: return ''

def run_log_row_count():
    try:
        with open('logs/run-log.csv', newline='', encoding='utf-8') as handle:
            return max(0, sum(1 for row in csv.reader(handle) if row) - 1)
    except (OSError, csv.Error):
        return 0

# ---------- what changed ----------
CURRENT_INVENTORY = file_inventory()
DELETED = sorted(set(BASELINE_INVENTORY or {}) - set(CURRENT_INVENTORY))
added_archive_counts = {}
for path in set(CURRENT_INVENTORY) - set(BASELINE_INVENTORY or {}):
    if path.startswith('archive/'):
        digest = CURRENT_INVENTORY[path]
        added_archive_counts[digest] = added_archive_counts.get(digest, 0) + 1
remaining_deleted = []
for path in DELETED:
    digest = (BASELINE_INVENTORY or {}).get(path)
    if path.startswith('inbox/') and added_archive_counts.get(digest, 0):
        added_archive_counts[digest] -= 1
    else:
        remaining_deleted.append(path)
DELETED = remaining_deleted
changed = [p for p in walk() if os.path.getmtime(p) >= CUTOFF]
changed = [p for p in changed if not p.endswith(('.png', '.jpg', '.webp', '.pdf', '.docx', '.pptx', '.xlsx'))]
if not changed and not DELETED:
    print("Nothing changed since the last check (use --since N or --all).")
    # Bootstrap or refresh the inventory only after this no-change pass succeeds.
    # Keep the timestamp/run-log baseline so a no-op does not hide recent writes.
    mark(cutoff=BASELINE_CUTOFF if BASELINE_CUTOFF is not None else time.time(),
         run_log_rows=BASELINE_RUN_LOG_ROWS if BASELINE_RUN_LOG_ROWS is not None
         else run_log_row_count(),
         inventory=CURRENT_INVENTORY)
    sys.exit(0)
for path in DELETED:
    FAIL(f"{path}: file was deleted since the last successful check")

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
tickets = {t for t in tickets if not re.match(r'(DEC|COM|RISK|EV|INIT|TODO|OKR)-', t)}

# ---------- 2 + 5 + 6: outputs ----------
input_blob = "\n".join(read(p) for p in walk(INPUT_DIRS)).lower()
ID_RE = re.compile(r'\b(?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5}\b')
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
elif os.path.exists(rl) and (ALL or os.path.getmtime(rl) >= CUTOFF):
    lines = [l for l in read(rl).splitlines() if l.strip()]
    row_count = run_log_row_count()
    if len(lines) < 2 or row_count < 1:
        FAIL("logs/run-log.csv has no data row for this run")
    elif not ALL and '--since' not in ARGS and BASELINE_RUN_LOG_ROWS is not None and row_count <= BASELINE_RUN_LOG_ROWS:
        FAIL("logs/run-log.csv did not gain a data row since the last successful check")
    else:
        OK(f"run log has {row_count} data row(s); latest: {lines[-1][:100]}")
else:
    if os.path.exists(rl) and BASELINE_RUN_LOG_ROWS is not None and run_log_row_count() <= BASELINE_RUN_LOG_ROWS:
        FAIL("logs/run-log.csv did not gain a data row since the last successful check")
    else:
        FAIL("logs/run-log.csv was not updated after the check window — rule 19 not honored (or the run-log hook is not installed)")

# ---------- report ----------
for m in fails: print("FAIL ", m)
for m in warns: print("WARN ", m)
for m in oks:   print("OK   ", m)
print(f"\n{len(fails)} fail · {len(warns)} warn · {len(oks)} ok")
if fails:
    print("Check baseline retained because failures remain; fix them and rerun to check the same files.")
    retain_failed_baseline()
else:
    mark(inventory=CURRENT_INVENTORY)
sys.exit(1 if fails else 0)
