#!/usr/bin/env python3
"""PostToolUse hook on Write|Edit for outputs/**, drafts/**, learning/**,
registers/**, and reference/context/**.

Every DEC-/COM-/RISK-/EV-/INIT-/TODO- id cited must exist in a register.
For register writes, only non-ID columns are checked (so a new row's own id
is not treated as a citation of a missing id).
Every ticket key (LUM-123 style) must appear in an inbox export or register.
If not, Claude is told (exit 2) so it fixes the file in the same turn.
Nothing is deleted; the write has already happened.
"""
import sys, os, re, glob, csv, io, hashlib, time, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, rel, block, warn

ID_RE = re.compile(r'\b(?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5}\b')
TICKET_RE = re.compile(r'\b[A-Z]{2,6}-\d{2,6}\b')
OWN_ID_RE = re.compile(r'^\s*((?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5})\b')

WATCHED = (
    'outputs/', 'drafts/', 'learning/',
    'registers/', 'reference/context/',
)


def citation_text_for_register(txt: str) -> str:
    """For CSV registers: concatenate non-id columns so a new row's own id
    is not flagged as a missing citation."""
    try:
        rows = list(csv.reader(io.StringIO(txt)))
    except Exception:
        return txt
    if not rows:
        return txt
    parts = []
    for row in rows[1:]:
        if not row:
            continue
        # Skip column 0 (id); check everything else
        parts.append('\t'.join(row[1:]))
    return '\n'.join(parts)


try:
    p = payload()
    path = (p.get('tool_input', {}) or {}).get('file_path') or ''
    r = rel(path)
    if not r.startswith(WATCHED):
        sys.exit(0)
    full = os.path.join(root(), r)
    if not os.path.exists(full):
        sys.exit(0)
    txt = open(full, encoding='utf-8', errors='replace').read()

    def record_hash():
        """Plan C edit detection: remember what Claude wrote so a later change on disk can be counted
        as an edit by you. Failure here never affects the provenance check."""
        try:
            if not r.startswith(('outputs/', 'drafts/')):
                return
            state = os.path.join(root(), 'state')
            path = os.path.join(state, 'output-hashes.csv')
            if os.path.islink(state) or os.path.islink(path):
                return
            os.makedirs(state, exist_ok=True)
            digest = hashlib.sha256(open(full, 'rb').read()).hexdigest()
            rows = []
            if os.path.isfile(path):
                with open(path, newline='', encoding='utf-8') as fh:
                    rows = [x for x in csv.reader(fh) if x and x[0] != 'path' and x[0] != r]
            rows.append([r, digest, time.strftime('%Y-%m-%dT%H:%M:%S')])
            tmp = tempfile.NamedTemporaryFile('w', newline='', encoding='utf-8', dir=state, delete=False, suffix='.tmp')
            with tmp:
                w = csv.writer(tmp, lineterminator='\n')
                w.writerow(['path', 'sha256', 'written_at'])
                w.writerows(rows)
            os.replace(tmp.name, path)
        except Exception:
            pass
    record_hash()

    known = set()
    for reg in glob.glob(os.path.join(root(), 'registers', '*.csv')):
        for line in open(reg, encoding='utf-8', errors='replace'):
            m = OWN_ID_RE.match(line)
            if m:
                known.add(m.group(1))

    tickets = set()
    for d in ('inbox', 'archive', 'registers', 'state', 'reference'):
        for dp, _, fs in os.walk(os.path.join(root(), d)):
            for f in fs:
                if f.endswith(('.csv', '.txt', '.md', '.json', '.yml')):
                    tickets |= set(TICKET_RE.findall(
                        open(os.path.join(dp, f), encoding='utf-8', errors='replace').read()
                    ))

    scan = citation_text_for_register(txt) if r.startswith('registers/') else txt
    cited = set(ID_RE.findall(scan))
    missing = sorted(cited - known)
    ticket_cited = set(TICKET_RE.findall(scan)) - cited - set(re.findall(r'\bOKR-\d+\b', scan))
    ticket_missing = sorted(ticket_cited - tickets)
    msgs = []
    if missing:
        msgs.append(
            f"{r} cites register ids that exist in no register: {', '.join(missing)}. "
            "Either append the row first (with its source) or remove the citation. "
            "Never cite an id you did not write."
        )
    if ticket_missing:
        msgs.append(
            f"{r} cites ticket keys that appear in no export or register: {', '.join(ticket_missing)}. "
            "Name the access path you read them from (rule 21), drop them into inbox/, or remove them."
        )
    if msgs:
        block("PROVENANCE CHECK FAILED\n" + "\n".join(msgs))
    sys.exit(0)
except SystemExit:
    raise
except Exception as e:
    warn(f"check_output_provenance skipped: {e}")
