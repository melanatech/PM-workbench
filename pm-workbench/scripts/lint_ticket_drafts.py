#!/usr/bin/env python3
"""Deterministic lint for Jira ticket drafts (paste blocks) and, optionally, stored Jira text.

Paste blocks follow `reference/templates/jira-ticket-draft.md`: a fenced block whose first
non-blank line starts with `Summary:`. Each block is checked on its own. The heading above the
block names it in the output.

Usage:
  python3 scripts/lint_ticket_drafts.py FILE.md [FILE.md ...] [--jira-json SNAPSHOT.json] [--page]
                                        [--jira-keys KEY,KEY]

  FILE.md          draft files with paste blocks (or, with --page, a roadmap page in Markdown)
  --jira-json      a snapshot {"tickets": {KEY: {"project", "summary", "description", ...}}};
                   runs banned-conditional, banned-tech-question and code-terms on each description
  --jira-keys      limit the --jira-json check to these keys
  --page           check the Q4 table on a roadmap page: column 1 <= 25 words, column 3 <= 30 words,
                   links excluded

Exit 0 on pass, 1 on any FAIL. One line per FAIL: file | heading | check | matched text.
Final line is `LINT: PASS` or `LINT: FAIL n`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

I = re.I

BANNED_CONDITIONAL = [
    r"create only (?:if|when)", r"\bonly if\b", r"\bif (?:needed|required|necessary)\b",
    r"\bif (?:it|this) fits\b", r"\bconditional\b", r"\boptional\b", r"\bstretch\b",
    r"\bif picked up\b",
]
BANNED_TECH_Q = [
    r"what does (?:each|the|a) (?:query|request|call)", r"query cost",
    r"cost of (?:each|the) quer", r"how (?:much|long) does (?:each|a|the) (?:query|call|request)",
    r"load time", r"performance budget", r"would it take",
]
CODE_TERMS = [
    ("backtick", r"`"),
    ("file-extension", r"\.(?:tsx?|jsx?|ya?ml|sql|json|py)\b"),
    ("camelCase", r"\b[a-z]+[A-Z]\w+\b"),
    ("snake_case", r"\b[a-z]+_[a-z_]+\b"),
    ("api-path", r"/api/"),
    ("endpoint", r"\bendpoint"),
    ("cube", r"\bcube\b"),
    ("graphql", r"graphql"),
    ("opensearch", r"opensearch"),
    ("schema", r"\bschema"),
]
REPORT_ONLY_TERMS = [("datasheet", r"\bdatasheet"), ("backfill", r"\bbackfill")]
TECH_HEADERS_ALWAYS = r"^\s*(?:#+\s*)?(Implementation|Technical|Key files)\b[^\n]*:?\s*$"
TECH_HEADERS_IF_CODE = r"^\s*(?:#+\s*)?(Constraints|Questions to answer)\b[^\n]*:?\s*$"
DESIGN_LAYOUT = [
    r"\d+\s?px", r"full-width", r"card order", r"\b(?:above|below|beside|between|left of|right of)\b",
    r"candidates?:", r"placement",
]
VENDOR_NAMES = [r"\bclaude\b", r"\banthropic\b", r"\bchatgpt\b", r"\bopenai\b", r"\bcopilot\b", r"\bgemini\b"]
VAGUE_REFS = [r"\bthe accepted\b", r"\bas on screen\b", r"\bthe restored\b", r"\bsame as (?:before|today|the old)\b"]
DESIGN_MAX_WORDS = 300
REQUIRED_FIELDS = [
    "Summary", "Project", "Type", "Initiative / Epic", "Priority", "Target date", "Assignee",
    "Description", "Acceptance criteria", "Related tickets",
]
WORKBENCH_IDS = [r"\b(?:DEC|COM|RISK|TODO|EV|INIT)-\d+", r"outputs/", r"archive/"]
# Team-ownership terms and overloaded epics are PM-specific: they live in a local config file
# (gitignored), JSON like {"team_re": "a|b|c", "bad_epics": ["KEY-1", "KEY-2"]}.
CONFIG_CANDIDATES = [
    Path.cwd() / "reference" / "context" / "ticket-lint.json",
    Path(__file__).resolve().parents[1] / "reference" / "context" / "ticket-lint.json",
    Path(__file__).parents[1] / "reference" / "context" / "ticket-lint.json",
]


def _load_config():
    cfg = {}
    for c in CONFIG_CANDIDATES:
        try:
            cfg = json.loads(c.read_text(encoding="utf-8"))
            break
        except (OSError, ValueError):
            continue
    team = str(cfg.get("team_re") or "")
    epics = [re.escape(str(e)) for e in cfg.get("bad_epics") or []]
    return team, (r"\b(?:" + "|".join(epics) + r")\b") if epics else ""


TEAM_RE, BAD_EPICS = _load_config()
PAGE_COL1_MAX = 25
PAGE_COL3_MAX = 30


def _first(patterns, text):
    for p in patterns:
        m = re.search(p, text, I)
        if m:
            return m.group(0)
    return None


def _strip_urls(text):
    text = re.sub(r"\]\((?:https?://)?[^)\s]*\)", "]", text)
    return re.sub(r"https?://\S+", " ", text)


def code_term_hits(text, project):
    text = _strip_urls(text)
    hits = []
    for name, pat in CODE_TERMS:
        flags = 0 if name in ("camelCase", "snake_case") else I
        m = re.search(pat, text, flags)
        if m:
            hits.append((name, m.group(0)))
    if (project or "").strip().upper() != "REPORT":
        for name, pat in REPORT_ONLY_TERMS:
            m = re.search(pat, text, I)
            if m:
                hits.append((name, m.group(0)))
    return hits


# ---------------------------------------------------------------- parsing

def parse_blocks(text):
    """Yield (heading, block_text, section_text) for each paste block."""
    lines = text.splitlines()
    heading_at = []
    heading = "(top)"
    for ln in lines:
        m = re.match(r"^(#{1,6})\s+(.*\S)", ln)
        if m:
            heading = m.group(2)
        heading_at.append(heading)
    # section text = from a heading line to the next heading line
    idx_heads = [i for i, ln in enumerate(lines) if re.match(r"^#{1,6}\s+", ln)]
    out = []
    i = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].lstrip().startswith("```"):
                j += 1
            body = lines[i + 1:j]
            first = next((b for b in body if b.strip()), "")
            if first.strip().startswith("Summary:"):
                start = max([h for h in idx_heads if h <= i], default=0)
                nxt = min([h for h in idx_heads if h > i], default=len(lines))
                out.append((heading_at[i], "\n".join(body), "\n".join(lines[start:nxt])))
            i = j + 1
        else:
            i += 1
    return out


def field(block, name):
    m = re.search(r"^" + re.escape(name) + r":[ \t]*(.*)$", block, re.M)
    return m.group(1).strip() if m else None


def section_of(block, header):
    """Text under a `Header:` line until the next known header line."""
    names = REQUIRED_FIELDS + ["User stories", "Steps to reproduce", "Edge cases", "Out of scope",
                               "Feature guidelines", "Problem"]
    m = re.search(r"^" + re.escape(header) + r"[^\n]*:[ \t]*\n", block, re.M)
    if not m:
        return None
    rest = block[m.end():]
    stop = re.search(r"^(?:" + "|".join(re.escape(n) for n in names) + r")\b[^\n]*:", rest, re.M)
    return rest[:stop.start()] if stop else rest


# ---------------------------------------------------------------- checks on a paste block

def lint_block(block, section, jira_summaries):
    fails = []

    def add(check, matched):
        fails.append((check, matched))

    for f in REQUIRED_FIELDS:
        if not re.search(r"^" + re.escape(f) + r":", block, re.M):
            add("template", "missing line: " + f)

    project = field(block, "Project") or ""
    ptype = field(block, "Type") or ""
    summary = field(block, "Summary") or ""
    epic = field(block, "Initiative / Epic") or ""
    proj = "CP" if re.match(r"\s*CP\b", project, I) else ("REPORT" if re.match(r"\s*REPORT\b", project, I) else project.strip().split(" ")[0].upper())

    m = _first(BANNED_CONDITIONAL, block)
    if m:
        add("banned-conditional", m)
    m = _first(BANNED_TECH_Q, block)
    if m:
        add("banned-tech-question", m)
    for name, hit in code_term_hits(block, proj):
        add("code-terms", f"{name}: {hit}")

    td = (field(block, "Target date") or "").strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", td):
        add("target-date", "needs a plain YYYY-MM-DD, got: " + (td or "(empty)"))
    m = _first(VENDOR_NAMES, block)
    if m:
        add("vendor-name", m)
    m = _first(VAGUE_REFS, block)
    if m:
        add("vague-reference", m)

    for hm in re.finditer(TECH_HEADERS_ALWAYS, block, I | re.M):
        add("tech-sections", "header: " + hm.group(1))
    for hm in re.finditer(TECH_HEADERS_IF_CODE, block, I | re.M):
        body = section_of(block, hm.group(1)) or ""
        hits = code_term_hits(body, proj)
        if hits:
            add("tech-sections", f"{hm.group(1)} item with {hits[0][0]}: {hits[0][1]}")

    # design blocks
    is_design = bool(re.match(r"\s*design\b", summary, I))
    if not is_design:
        for k in re.findall(r"[A-Z][A-Z0-9]+-\d+", epic):
            if re.match(r"\s*design\b", jira_summaries.get(k, ""), I):
                is_design = True
    if is_design:
        m = _first(DESIGN_LAYOUT, block)
        if m:
            add("design-layout", m)
        for h in ("User stories:", "Feature guidelines:"):
            if not re.search(r"^" + re.escape(h), block, re.M):
                add("design-layout", "missing header " + h)
        words = len(re.findall(r"\S+", block))
        if words > DESIGN_MAX_WORDS:
            add("design-layout", f"{words} words (max {DESIGN_MAX_WORDS})")

    # columns-listed
    m = re.search(r"legacy (?:columns|fields)|every (?:column|field)", block, I)
    if m and not re.search(r"^\s*\|[\s:|-]*-[\s:|-]*\|", block, re.M):
        add("columns-listed", m.group(0))

    # workbench ids
    for p in WORKBENCH_IDS:
        m = re.search(p, block)
        if m:
            add("workbench-ids", m.group(0))
            break

    # pairing
    if proj == "CP" and re.match(r"\s*(?:story|bug)\b", ptype, I):
        related = field(block, "Related tickets") or ""
        rel_sec = section_of(block, "Related tickets") or ""
        rel_all = related + "\n" + rel_sec
        if not (re.search(r"REPORT-\d+", rel_all) or re.search(r"Draft #", rel_all)
                or re.search(r"no backend:", section, I)):
            add("pairing", "CP " + ptype.strip() + " without REPORT key, Draft #, or 'no backend:' note")

    # team
    if proj == "CP":
        m = re.search(TEAM_RE, summary, I) if TEAM_RE else None
        if m:
            add("team", m.group(0))

    # epic
    m = re.search(BAD_EPICS, epic) if BAD_EPICS else None
    if m:
        add("epic", m.group(0))
    return fails


# ---------------------------------------------------------------- Jira text

def strip_jira(text):
    text = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    text = _strip_urls(text)
    text = text.replace("`", "")
    text = re.sub(r"[*_]{2,}", "", text)
    return text


def lint_jira(path, keys):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    tickets = data.get("tickets", data)
    fails = []
    for k, t in tickets.items():
        if not isinstance(t, dict) or (keys and k not in keys):
            continue
        txt = strip_jira(t.get("description", ""))
        m = _first(BANNED_CONDITIONAL, txt)
        if m:
            fails.append((k, "banned-conditional", m))
        m = _first(BANNED_TECH_Q, txt)
        if m:
            fails.append((k, "banned-tech-question", m))
        for name, hit in code_term_hits(txt, t.get("project", "")):
            fails.append((k, "code-terms", f"{name}: {hit}"))
    return fails


# ---------------------------------------------------------------- page mode

def _cells(row):
    row = row.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [c.strip() for c in re.split(r"(?<!\\)\|", row)]


def _words(cell):
    cell = re.sub(r"\[[^\]]*\]\([^)]*\)", " ", cell)
    cell = re.sub(r"https?://\S+", " ", cell)
    cell = re.sub(r"<[^>]+>", " ", cell)
    return len(re.findall(r"[A-Za-z0-9$%][\w$%.,'/&-]*", cell))


def lint_page(text):
    fails = []
    lines = text.splitlines()
    heading = "(top)"
    tables = []
    i = 0
    while i < len(lines):
        m = re.match(r"^#{1,6}\s+(.*\S)", lines[i])
        if m:
            heading = m.group(1)
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and re.match(r"^\s*\|[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1]):
            j = i + 2
            rows = []
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append(_cells(lines[j]))
                j += 1
            tables.append((heading, _cells(lines[i]), rows))
            i = j
            continue
        i += 1
    cand = [t for t in tables if t[1] and re.match(r"item", t[1][0], I) and len(t[1]) >= 3]
    q4 = [t for t in cand if re.search(r"Q4", t[0], I)] or cand[:1]
    if not q4:
        return [("(page)", "page-cells", "no Q4 Item table found")]
    for h, head, rows in q4:
        for r in rows:
            name = _words(r[0]) and re.sub(r"\s+", " ", r[0])[:40]
            if len(r) > 0 and _words(r[0]) > PAGE_COL1_MAX:
                fails.append((h, "page-cells", f"col 1 {_words(r[0])} words > {PAGE_COL1_MAX}: {name}"))
            if len(r) > 2 and _words(r[2]) > PAGE_COL3_MAX:
                fails.append((h, "page-cells", f"col 3 {_words(r[2])} words > {PAGE_COL3_MAX}: {name}"))
    return fails


# ---------------------------------------------------------------- main

def main(argv):
    files, jira_json, page, keys = [], None, False, None
    it = iter(argv)
    for a in it:
        if a == "--jira-json":
            jira_json = next(it, None)
        elif a == "--jira-keys":
            keys = set((next(it, "") or "").split(","))
        elif a == "--page":
            page = True
        elif a in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            files.append(a)
    if not files and not jira_json:
        print(__doc__)
        return 2

    jira_summaries = {}
    if jira_json and Path(jira_json).is_file():
        d = json.loads(Path(jira_json).read_text(encoding="utf-8"))
        for k, t in (d.get("tickets", d) or {}).items():
            if isinstance(t, dict):
                jira_summaries[k] = t.get("summary", "")

    n = 0
    for f in files:
        p = Path(f)
        if not p.is_file():
            print(f"FAIL {f} | - | file | not found")
            n += 1
            continue
        text = p.read_text(encoding="utf-8")
        if page:
            for h, chk, matched in lint_page(text):
                print(f"FAIL {f} | {h} | {chk} | {matched}")
                n += 1
            continue
        blocks = parse_blocks(text)
        if not blocks:
            print(f"FAIL {f} | - | template | no paste block (fenced block starting 'Summary:') found")
            n += 1
        for heading, block, section in blocks:
            for chk, matched in lint_block(block, section, jira_summaries):
                print(f"FAIL {f} | {heading} | {chk} | {matched}")
                n += 1
    if jira_json:
        for k, chk, matched in lint_jira(jira_json, keys):
            print(f"FAIL {jira_json} | {k} | {chk} | {matched}")
            n += 1
    print("LINT: PASS" if n == 0 else f"LINT: FAIL {n}")
    return 0 if n == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
