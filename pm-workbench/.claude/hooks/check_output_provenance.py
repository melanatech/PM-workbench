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
import sys, os, re, csv, io, hashlib, time, tempfile, json
sys.path.insert(0, os.path.dirname(__file__))
from _common import payload, root, rel, block, warn

ID_RE = re.compile(r'\b(?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5}\b')
TICKET_RE = re.compile(r'\b[A-Z]{2,6}-\d{2,6}\b')
OWN_ID_RE = re.compile(r'^\s*((?:DEC|COM|RISK|EV|INIT|TODO)-\d{3,5})\b')

WATCHED = (
    'outputs/', 'drafts/', 'learning/',
    'registers/', 'reference/context/',
)
SCAN_DIRS = ('inbox', 'archive', 'registers', 'state', 'reference')
SCAN_EXTS = ('.csv', '.txt', '.md', '.json', '.yml')
CACHE_REL = os.path.join('state', 'hooks', 'provenance-cache.json')


def index_corpus(base):
    """Known register ids and ticket keys. Reread a file only when its mtime changed."""
    cache_path = os.path.join(base, CACHE_REL)
    try:
        cache = json.load(open(cache_path, encoding='utf-8'))
    except (OSError, ValueError):
        cache = {}
    files = cache.get('files') if isinstance(cache.get('files'), dict) else {}
    seen = set()
    for d in SCAN_DIRS:
        scan_root = os.path.join(base, d)
        if not os.path.isdir(scan_root):
            continue
        for dp, _, names in os.walk(scan_root):
            for name in names:
                if not name.endswith(SCAN_EXTS):
                    continue
                full = os.path.join(dp, name)
                rel_path = os.path.relpath(full, base)
                if rel_path == CACHE_REL:
                    continue
                seen.add(rel_path)
                try:
                    mtime = os.stat(full).st_mtime_ns
                except OSError:
                    continue
                rec = files.get(rel_path)
                if isinstance(rec, dict) and rec.get('mtime') == mtime:
                    continue
                text = open(full, encoding='utf-8', errors='replace').read()
                ids = []
                if rel_path.startswith('registers' + os.sep) and name.endswith('.csv'):
                    ids = sorted({m.group(1) for line in text.splitlines() if (m := OWN_ID_RE.match(line))})
                files[rel_path] = {
                    'mtime': mtime,
                    'ids': ids,
                    'tickets': sorted(set(TICKET_RE.findall(text))),
                    'read_at': time.time(),
                }
    for rel_path in list(files):
        if rel_path not in seen:
            del files[rel_path]
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    tmp = cache_path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as handle:
        json.dump({'files': files}, handle)
    os.replace(tmp, cache_path)
    known, tickets = set(), set()
    for rec in files.values():
        known.update(rec.get('ids') or [])
        tickets.update(rec.get('tickets') or [])
    return known, tickets


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

    known, tickets = index_corpus(root())

    scan = citation_text_for_register(txt) if r.startswith('registers/') else txt
    cited = set(ID_RE.findall(scan))
    missing = sorted(cited - known)
    ticket_cited = set(TICKET_RE.findall(scan)) - cited - set(re.findall(r'\bOKR-\d+\b', scan))
    ticket_missing = sorted(ticket_cited - tickets)
    blocking = []
    advisory = []
    if missing:
        blocking.append(
            f"{r} cites register ids that exist in no register: {', '.join(missing)}. "
            "Either append the row first (with its source) or remove the citation. "
            "Never cite an id you did not write."
        )
    if ticket_missing:
        msg = (
            f"{r} cites ticket keys that appear in no export or register: {', '.join(ticket_missing)}. "
            "Name the access path you read them from (rule 21), drop them into inbox/, or remove them."
        )
        # Drafting surfaces get a warning; durable records still block.
        (advisory if r.startswith(('outputs/', 'drafts/')) else blocking).append(msg)
    if blocking:
        block("PROVENANCE CHECK FAILED\n" + "\n".join(blocking + advisory))
    if advisory:
        warn("PROVENANCE WARNING\n" + "\n".join(advisory))
    sys.exit(0)
except SystemExit:
    raise
except Exception as e:
    warn(f"check_output_provenance skipped: {e}")
