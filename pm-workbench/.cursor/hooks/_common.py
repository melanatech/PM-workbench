#!/usr/bin/env python3
"""Shared helpers for the workbench Cursor project hooks (live workspace)."""
from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOOKS_DIR = Path(__file__).resolve().parent
# .cursor/hooks -> project root
DEFAULT_ROOT = HOOKS_DIR.parents[1]
CONFIG_PATH = HOOKS_DIR / "shared-artifacts.json"
STATE_DIR = DEFAULT_ROOT / "state" / "hooks"
STATUS_PATH = STATE_DIR / "gate-status.json"
LOG_PATH = STATE_DIR / "hook-log.jsonl"
DESIGN_BASELINES_DIRNAME = "design-baselines"

DESIGN_SCRIPT = "scripts/check_design_preserved.py"
NUMBER_SCRIPT = "scripts/check_number_consistency.py"

# Stable phrases required in Task prompts that edit shared artifacts.
DESIGN_HEADER_PHRASE = "Keep its design, CSS, markup structure"
NUMBER_GATE_PHRASE = "number gate"
NUMBER_GATE_ALT = "check_number_consistency"

# Digits that look like reported counts (mirrors check_number_consistency bounds).
_NUM_RE = re.compile(
    r"(?<![\w./-])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d{4,}|\d{1,3})(?![\w./-])"
)
_MIN_ABS = 3

ATLASSIAN_WRITE_TOOLS = {
    "createJiraIssue",
    "editJiraIssue",
    "transitionJiraIssue",
    "addOrEditJiraIssueComment",
    "createConfluenceContent",
    "updateConfluenceContent",
    "executeWrite",
    "executeDestructive",
}

ATLASSIAN_READ_PREFIXES = (
    "get",
    "search",
    "discover",
    "executeRead",
    "atlassianUserInfo",
)

SLACK_READ_HINTS = (
    "search",
    "get",
    "list",
    "fetch",
    "read",
    "lookup",
    "find",
    "mcp_auth",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_stdin_json() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_raw": raw, "_parse_error": True}


def emit(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False))
    sys.stdout.flush()


def project_root(payload: dict[str, Any] | None = None) -> Path:
    roots = (payload or {}).get("workspace_roots") or []
    for r in roots:
        p = Path(r)
        if (p / "scripts" / "check_design_preserved.py").exists() or (
            p / ".cursor" / "hooks"
        ).exists():
            return p
    if roots:
        return Path(roots[0])
    return DEFAULT_ROOT


def load_config(root: Path | None = None) -> dict[str, Any]:
    path = (root or DEFAULT_ROOT) / ".cursor" / "hooks" / "shared-artifacts.json"
    if not path.is_file():
        path = CONFIG_PATH
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def ensure_state_dir(root: Path) -> Path:
    d = root / "state" / "hooks"
    d.mkdir(parents=True, exist_ok=True)
    return d


def log_decision(root: Path, entry: dict[str, Any]) -> None:
    ensure_state_dir(root)
    row = {"ts": utc_now(), **entry}
    path = root / "state" / "hooks" / "hook-log.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def load_status(root: Path) -> dict[str, Any]:
    ensure_state_dir(root)
    path = root / "state" / "hooks" / "gate-status.json"
    if not path.is_file():
        return {"sessions": {}, "files": {}}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"sessions": {}, "files": {}}


def save_status(root: Path, status: dict[str, Any]) -> None:
    ensure_state_dir(root)
    path = root / "state" / "hooks" / "gate-status.json"
    path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_to_root(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _match_any(rel: str, patterns: list[str]) -> bool:
    """Glob match with ``**`` support (pathlib; stdlib fnmatch does not treat ``**``)."""
    from pathlib import PurePosixPath

    rel = rel.replace("\\", "/").lstrip("./")
    name = PurePosixPath(rel).name
    path = PurePosixPath(rel)
    for pat in patterns:
        pat_n = pat.replace("\\", "/")
        try:
            if path.match(pat_n) or PurePosixPath(name).match(pat_n):
                return True
        except ValueError:
            pass
        # Basename-only patterns like *.html
        if "/" not in pat_n.rstrip("*") and fnmatch.fnmatch(name, pat_n):
            return True
        if pat_n.startswith("**/") and (
            path.match(pat_n[3:]) or fnmatch.fnmatch(name, pat_n[3:])
        ):
            return True
    return False


def is_shared_artifact(rel_path: str, config: dict[str, Any]) -> bool:
    root_prefix = (config.get("root") or "outputs").rstrip("/") + "/"
    # Normalize
    rel = rel_path.replace("\\", "/").lstrip("./")
    if not rel.startswith(root_prefix) and not rel.startswith("outputs/"):
        # Absolute-looking under outputs somewhere
        if "/outputs/" in f"/{rel}":
            idx = rel.find("outputs/")
            rel = rel[idx:]
        else:
            return False
    if not rel.startswith("outputs/"):
        return False
    under = rel[len("outputs/") :]
    includes = config.get("include_globs") or []
    excludes = config.get("exclude_globs") or []
    if excludes and _match_any(under, excludes):
        return False
    if not includes:
        return False
    return _match_any(under, includes)


def is_claim_checked(rel_path: str, config: dict[str, Any]) -> bool:
    """outputs/**/*.md deliverables that get the claim-table check (see shared-artifacts.json)."""
    cc = config.get("claim_check") or {}
    rel = rel_path.replace("\\", "/").lstrip("./")
    if "/outputs/" in f"/{rel}" and not rel.startswith("outputs/"):
        rel = rel[rel.find("outputs/") :]
    if not rel.startswith("outputs/") or not rel.endswith(".md"):
        return False
    under = rel[len("outputs/") :]
    excludes = cc.get("exclude_globs") or []
    if excludes and _match_any(under, excludes):
        return False
    return _match_any(under, cc.get("include_globs") or [])


def ledger_path_for(artifact: Path, root: Path, config: dict[str, Any]) -> Path | None:
    rel = rel_to_root(artifact, root)
    overrides = config.get("ledger_by_artifact") or {}
    if rel in overrides:
        return root / overrides[rel]
    # Also try basename key
    if artifact.name in overrides:
        return root / overrides[artifact.name]
    suffix = (config.get("ledger_convention") or {}).get(
        "sibling_suffix", "-number-ledger.md"
    )
    return artifact.with_name(artifact.stem + suffix)


def artifact_has_numbers(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    # Strip style/script roughly for html
    if path.suffix.lower() in {".html", ".htm"}:
        text = re.sub(r"<script\b[^>]*>.*?</script>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
        text = re.sub(r"<[^>]+>", " ", text)
    for m in _NUM_RE.finditer(text):
        norm = m.group(1).replace(",", "")
        try:
            val = float(norm)
        except ValueError:
            continue
        if abs(val) >= _MIN_ABS or "." in norm:
            return True
    return False


def git_has_blob(root: Path, rel: str, ref: str = "HEAD") -> bool:
    proc = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{ref}:{rel}"],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def design_baselines_root(root: Path) -> Path:
    return root / "state" / "hooks" / DESIGN_BASELINES_DIRNAME


def design_baseline_path(root: Path, artifact: Path) -> Path:
    """Baseline copy path: state/hooks/design-baselines/<rel-to-root>."""
    rel = rel_to_root(artifact, root)
    return design_baselines_root(root) / rel


def write_design_baseline(root: Path, artifact: Path) -> Path:
    """Copy the current artifact over its design baseline. Returns baseline path."""
    dest = design_baseline_path(root, artifact)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(artifact, dest)
    return dest


def run_design_check(root: Path, artifact: Path) -> tuple[str, str]:
    """Return (status, message). status in pass|fail|new|skipped|n/a.

    Prefer ``--git HEAD`` when the file exists in git; otherwise compare against
    the last-passing baseline under ``state/hooks/design-baselines/``.

    On pass (or new), update the baseline to the current file. On fail, leave it.
    ``skipped`` is legacy / unavailable — treat as fail for shared HTML gates.
    """
    if artifact.suffix.lower() not in {".html", ".htm"}:
        return "n/a", "design check only applies to HTML"
    script = root / DESIGN_SCRIPT
    if not script.is_file():
        return "fail", "design check not installed (scripts/check_design_preserved.py missing)"
    if not artifact.is_file():
        return "fail", f"artifact missing: {artifact}"

    rel = rel_to_root(artifact, root)
    baseline = design_baseline_path(root, artifact)

    if git_has_blob(root, rel):
        cmd = [sys.executable, str(script), str(artifact), "--git", "HEAD"]
        source = "git HEAD"
    elif baseline.is_file():
        cmd = [
            sys.executable,
            str(script),
            str(artifact),
            "--before",
            str(baseline),
        ]
        source = f"baseline {rel_to_root(baseline, root)}"
    else:
        # Brand-new shared HTML: no prior version to compare. First state becomes baseline.
        write_design_baseline(root, artifact)
        return "new", "no prior version (git or baseline); seeded baseline from current file"

    proc = subprocess.run(
        cmd,
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    out = out.strip() or f"exit {proc.returncode}"
    if proc.returncode == 0:
        write_design_baseline(root, artifact)
        msg = out.splitlines()[0] if out else "PASS"
        return "pass", f"{msg} (via {source})"
    if proc.returncode == 2:
        # Usage / missing prior — do not soft-skip; gate must fail closed.
        return "fail", f"design check unavailable ({source}): {out}"
    return "fail", out


def run_number_check(root: Path, artifact: Path, config: dict[str, Any]) -> tuple[str, str]:
    """Return (status, message). Fail closed if script missing."""
    script = root / NUMBER_SCRIPT
    if not script.is_file():
        return "fail", "number check not installed"
    if not artifact_has_numbers(artifact):
        return "skipped", "no report-like numbers detected in artifact"
    ledger = ledger_path_for(artifact, root, config)
    if ledger is None or not ledger.is_file():
        expected = (
            artifact.with_name(artifact.stem + "-number-ledger.md").name
            if ledger is None
            else ledger.name
        )
        return "fail", f"number ledger missing (expected {expected})"
    proc = subprocess.run(
        [sys.executable, str(script), "--ledger", str(ledger), str(artifact)],
        cwd=str(root),
        capture_output=True,
        text=True,
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    out = out.strip() or f"exit {proc.returncode}"
    if proc.returncode == 0:
        return "pass", out.splitlines()[0] if out else "PASS"
    return "fail", out[:2000]


def record_gate(
    root: Path,
    payload: dict[str, Any],
    artifact: Path,
    design: str,
    number: str,
    messages: list[str],
    claims: str = "n/a",
) -> dict[str, Any]:
    status = load_status(root)
    rel = rel_to_root(artifact, root)
    try:
        st = artifact.stat()
        mtime = int(st.st_mtime)
        digest = file_hash(artifact)
    except OSError:
        mtime = 0
        digest = ""
    session_id = (
        payload.get("conversation_id")
        or payload.get("session_id")
        or payload.get("parent_conversation_id")
        or "unknown"
    )
    # Design: pass / n/a / new are ok. skipped is a FAIL for shared HTML
    # (no prior version must be recorded as new, not skipped).
    # Number: skipped/n/a remain non-blocking for that dimension.
    design_ok = design in {"pass", "n/a", "new"}
    number_ok = number in {"pass", "skipped", "n/a"}
    claims_ok = claims in {"pass", "n/a"}
    both_pass = design_ok and number_ok and claims_ok
    record = {
        "path": rel,
        "mtime": mtime,
        "hash": digest,
        "design": design,
        "number": number,
        "claims": claims,
        "timestamp": utc_now(),
        "messages": messages,
        "session_id": session_id,
        "pass_hash": digest if both_pass else None,
        "ok": both_pass,
    }
    if not both_pass:
        record["pass_hash"] = None
    status.setdefault("sessions", {}).setdefault(session_id, {}).setdefault(
        "artifacts", {}
    )[rel] = record
    status.setdefault("files", {})[rel] = record
    save_status(root, status)
    return record


def gate_failures_for_session(root: Path, session_id: str | None) -> list[dict[str, Any]]:
    status = load_status(root)
    failures: list[dict[str, Any]] = []
    seen: set[str] = set()
    latest = status.get("files") or {}

    def consider(rec: dict[str, Any]) -> None:
        path = rec.get("path") or ""
        if not path or path in seen:
            return
        seen.add(path)
        # Session entries are membership pointers; the newest check of the file wins.
        rec = latest.get(path, rec)
        abs_path = root / path
        reason = None
        if not abs_path.is_file():
            # Artifact gone; drop from consideration
            return
        try:
            current = file_hash(abs_path)
        except OSError:
            current = ""
        if not rec.get("ok"):
            reason = "gate missing or failing"
        elif rec.get("pass_hash") and current != rec.get("pass_hash"):
            reason = "hash changed since last passing check"
        elif current and current != rec.get("hash"):
            # Edited after last check without a new gate run
            reason = "hash changed since last check"
        if reason:
            failures.append({**rec, "fail_reason": reason, "current_hash": current})

    if session_id and session_id in status.get("sessions", {}):
        arts = status["sessions"][session_id].get("artifacts") or {}
        for rec in arts.values():
            consider(rec)
    elif not session_id:
        # Fallback: all tracked files (when session id absent)
        for rec in (status.get("files") or {}).values():
            consider(rec)
    # Worker failures that could not be tied to a parent conversation.
    for rec in pending_failures(status):
        consider(rec)
    return failures


# ---------------------------------------------------------------------------
# Claim checks (absence / assignment / person claims need a sourced claim table)
# ---------------------------------------------------------------------------

PENDING_MAX_AGE_HOURS = 24

_ABSENCE_PATTERNS = [
    r"\bno (?:existing |linked |matching |open |jira )?(?:prds?|tickets?|epics?|stor(?:y|ies)|jira (?:tickets?|issues?|epics?))\b"
    r"(?!\s+(?:keys?|numbers?|ids?|prefix(?:es)?|titles?|links? (?:in|format))\b)",
    r"\b(?:needs?|needed|requires?) (?:a |an )?(?:new )?prd\b",
    r"\bprd (?:is )?(?:needed|missing|required)\b",
    r"\bmissing (?:a |the )?prd\b",
    r"\b(?:empty|blank) description\b",
    r"\bdescription (?:is )?(?:empty|blank)\b",
    r"\b(?:is|are|looks|marked|now|went|gone) stale\b",
    r"\bstale (?:tickets?|epics?|stor(?:y|ies)|prds?|pages?|docs?|status|issues?)\b",
]
_ABSENCE_RE = [re.compile(p, re.I) for p in _ABSENCE_PATTERNS]
# Files (outputs .md) get only the PRD/ticket/epic absence family: "stale" and
# "empty description" are routine in registers and term docs.
_FILE_ABSENCE_RE = _ABSENCE_RE[:4]

_NAME = r"@?([A-Z][a-z]+(?:[ ][A-Z][a-z]+)?)"
_ASSIGN_RE = re.compile(
    r"\b(?:[Aa]ssigned to|ASSIGNED TO|[Aa]ssignee\s*[:=]|[Oo]wner\s*[:=]|[Oo]wned by|DRI\s*[:=]|[Rr]eporter\s*[:=])\s*\**\s*"
    + _NAME
)
_PM_NAME_RE = re.compile(
    r"\b(?:the )?PM\s*(?:\(|:|=|is\s+)\s*\**\s*" + _NAME + r"(?=\**\s*(?:[),.;]|$))", re.M
)
_FILE_ASSIGN_RE = re.compile(r"\b(?:[Aa]ssigned to|ASSIGNED TO)\s*\**\s*" + _NAME)
_NOT_NAMES = {
    "The", "This", "That", "None", "Nobody", "Unassigned", "Tbd", "TBD", "Me", "You",
    "Pm", "PM", "Whom", "Whoever", "Someone", "Anyone", "Team", "Eng", "Engineering",
    "Design", "Product", "Jira", "Confluence", "Unknown", "Null", "Empty", "Same",
}

_CLAIM_HEADER_RE = re.compile(r"^\s*\|.*\bclaims?\b.*\|", re.I)
_EMPTY_SOURCE = {"", "-", "—", "–", "none", "n/a", "na", "tbd", "?", "[needs input]"}


def load_identity(root: Path | None = None) -> dict[str, Any]:
    path = (root or DEFAULT_ROOT) / ".cursor" / "hooks" / "pm-identity.json"
    if not path.is_file():
        path = HOOKS_DIR / "pm-identity.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text or "", flags=re.S)
    return re.sub(r"`[^`\n]*`", " ", text)


def find_claims(
    text: str, pm_first_name: str | None = None, mode: str = "message"
) -> dict[str, list[str]]:
    """Return {'absence': [...], 'people': [...], 'wrong_pm': [...]} snippets found.

    mode="message" (worker results, replies) uses every pattern. mode="file"
    (outputs .md) is narrower: PRD/ticket/epic absence, "assigned to <not the PM>",
    and a wrong PM name.
    """
    body = _strip_code(text)
    out: dict[str, list[str]] = {"absence": [], "people": [], "wrong_pm": []}
    file_mode = mode == "file"
    for rx in _FILE_ABSENCE_RE if file_mode else _ABSENCE_RE:
        for m in rx.finditer(body):
            out["absence"].append(m.group(0))
    for m in (_FILE_ASSIGN_RE if file_mode else _ASSIGN_RE).finditer(body):
        first = m.group(1).split()[0]
        if first in _NOT_NAMES or (file_mode and first == pm_first_name):
            continue
        out["people"].append(m.group(0).strip())
    for m in _PM_NAME_RE.finditer(body):
        name = m.group(1)
        first = name.split()[0]
        if first in _NOT_NAMES:
            continue
        if pm_first_name and first != pm_first_name:
            out["wrong_pm"].append(m.group(0).strip())
    for k in out:
        out[k] = list(dict.fromkeys(out[k]))[:8]
    return out


def has_sourced_claim_table(text: str) -> tuple[bool, str]:
    """A markdown table whose header has a Claim column and a Source/Evidence column,
    with at least one data row whose source cell is filled in."""
    lines = (text or "").splitlines()
    for i, line in enumerate(lines):
        if not _CLAIM_HEADER_RE.match(line):
            continue
        cells = [c.strip().lower() for c in line.strip().strip("|").split("|")]
        src_idx = next(
            (j for j, c in enumerate(cells) if re.search(r"\b(source|evidence)\b", c)),
            None,
        )
        if src_idx is None:
            continue
        rows = 0
        for row in lines[i + 1 :]:
            if not row.strip().startswith("|"):
                break
            if re.match(r"^\s*\|[\s:|-]+\|\s*$", row):
                continue
            rc = [c.strip() for c in row.strip().strip("|").split("|")]
            if src_idx < len(rc) and rc[src_idx].strip("* ").lower() not in _EMPTY_SOURCE:
                rows += 1
        if rows:
            return True, f"claim table with {rows} sourced row(s)"
        return False, "claim table present but no row has a source"
    return False, "no claim table (| Claim | Source | … |)"


def claims_verdict(text: str, root: Path | None = None, mode: str = "message") -> dict[str, Any]:
    ident = load_identity(root)
    first = (ident.get("name") or "").split()[0] if ident.get("name") else None
    found = find_claims(text, first, mode)
    flagged = bool(found["absence"] or found["people"] or found["wrong_pm"])
    table_ok, table_msg = has_sourced_claim_table(text)
    if found["wrong_pm"]:
        ok = False
    elif not flagged:
        ok = True
    else:
        ok = table_ok
    return {"ok": ok, "flagged": flagged, "found": found, "table": table_msg}


def claims_followup_text(verdict: dict[str, Any], root: Path | None = None, who: str = "worker") -> str:
    ident = load_identity(root)
    pm = ident.get("name") or "[NEEDS INPUT: PM name/email]"
    f = verdict["found"]
    bits = []
    if f["absence"]:
        bits.append("absence/staleness claims: " + "; ".join(f'"{s}"' for s in f["absence"]))
    if f["people"]:
        bits.append("person/assignment claims: " + "; ".join(f'"{s}"' for s in f["people"]))
    if f["wrong_pm"]:
        bits.append(
            f"you named someone other than {pm} as the PM: "
            + "; ".join(f'"{s}"' for s in f["wrong_pm"])
            + f". The PM is {pm}. Never infer a person from a username, path, or account name"
        )
    return (
        f"Claim check failed ({verdict['table']}). Found {'; '.join(bits)}.\n"
        "Before this result goes to the PM: re-check each of these claims against the source "
        "(for an absence claim, check the artifact's own links and Sources section, not one search). "
        "Then either remove the claim or add a `## Claim table` to your final message with columns "
        "| Claim | Source | Checked how |, where Source is a Jira key plus the JQL or issue fetch you ran, "
        "a Confluence page id plus version, or file:line. If you cannot source a claim, write `unverified` "
        "as its source. Never invent a person, owner, date, metric, status, or decision."
    )


def pending_failures(status: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    now = datetime.now(timezone.utc)
    for rec in (status.get("pending") or {}).values():
        try:
            ts = datetime.fromisoformat(rec.get("pending_since", ""))
        except ValueError:
            continue
        if (now - ts).total_seconds() <= PENDING_MAX_AGE_HOURS * 3600:
            out.append(rec)
    return out


def refile_for_parent(root: Path, parent_id: str | None, rel_paths: list[str]) -> list[str]:
    """Attach the latest gate record for each worker-modified file to the parent
    conversation (or the shared pending list when no parent id). Returns failing paths."""
    status = load_status(root)
    files = status.get("files") or {}
    failing = []
    for rel in rel_paths:
        rec = files.get(rel)
        if not rec:
            continue
        if parent_id:
            status.setdefault("sessions", {}).setdefault(parent_id, {}).setdefault(
                "artifacts", {}
            )[rel] = rec
        elif not rec.get("ok"):
            status.setdefault("pending", {})[rel] = {**rec, "pending_since": utc_now()}
        if not rec.get("ok"):
            failing.append(rel)
    save_status(root, status)
    return failing


def add_relay_failure(root: Path, session_id: str, entry: dict[str, Any]) -> None:
    status = load_status(root)
    sess = status.setdefault("sessions", {}).setdefault(session_id or "unknown", {})
    sess.setdefault("relay_failures", []).append({"ts": utc_now(), **entry})
    save_status(root, status)


def pop_relay_failures(root: Path, session_id: str | None) -> list[dict[str, Any]]:
    status = load_status(root)
    sess = (status.get("sessions") or {}).get(session_id or "") or {}
    items = sess.pop("relay_failures", []) if sess else []
    if items:
        save_status(root, status)
    return items


def normalize_rel(path_like: Any, root: Path) -> str | None:
    if isinstance(path_like, dict):
        path_like = path_like.get("path") or path_like.get("file_path")
    if not path_like:
        return None
    p = Path(str(path_like))
    if not p.is_absolute():
        p = root / p
    return rel_to_root(p, root)


def looks_like_shared_edit_task(task: str, config: dict[str, Any]) -> bool:
    """True when a Task prompt looks like it will edit a shared artifact / outputs file.

    Detector (documented in README): false denies preferred over silent skips.
    Read-only research must not match.

    Implementation notes:
    - Strip negated phrases (\"do not edit\") before scanning write verbs so
      \"Do not edit any files\" is not treated as a write.
    - Require a write verb (word-boundary) plus an outputs/ path or shared name.
    """
    t = task or ""
    lower = t.lower()

    read_only_markers = (
        "read-only",
        "readonly",
        "research only",
        "explore only",
        "summarize only",
        "no file writes",
        "without editing",
    )
    # Remove negated write instructions before verb scan
    cleaned = re.sub(
        r"\b(do\s+not|don't|dont)\s+"
        r"(edit|modify|change|write|update|rewrite|revise|overwrite|patch|fix|extend)"
        r"(\s+any)?(\s+files?)?",
        " ",
        lower,
    )
    cleaned = re.sub(r"\bwithout\s+editing\b", " ", cleaned)

    write_re = re.compile(
        r"\b(edit|update|rewrite|revise|modify|overwrite|patch|extend)\b|"
        r"\b(add to|in place|write to|write over)\b"
    )
    has_write = bool(write_re.search(cleaned))
    has_read_only = any(m in lower for m in read_only_markers) or bool(
        re.search(
            r"\b(do\s+not|don't|dont)\s+(edit|modify|change|write)\b",
            lower,
        )
    )

    has_outputs_path = bool(re.search(r"outputs/[^\s`\"']+", t, re.I))
    has_shared_name = bool(
        re.search(
            r"(\.html\b|slack-draft|jira-drafts|jira draft|confluence|\breadout\b|\bdeck\b)",
            lower,
        )
    )

    # Pure research / explicit no-writes → never block
    if has_read_only and not has_write:
        return False
    if has_write and (has_outputs_path or has_shared_name):
        return True
    return False


def prompt_has_design_header(task: str) -> bool:
    return DESIGN_HEADER_PHRASE in (task or "")


def prompt_has_number_gate(task: str) -> bool:
    t = task or ""
    return NUMBER_GATE_PHRASE in t or NUMBER_GATE_ALT in t


def summarize_mcp_write(tool_name: str, tool_input: Any) -> str:
    try:
        if isinstance(tool_input, str):
            data = json.loads(tool_input) if tool_input.strip() else {}
        elif isinstance(tool_input, dict):
            data = tool_input
        else:
            data = {"value": tool_input}
    except json.JSONDecodeError:
        data = {"raw": str(tool_input)[:500]}
    # Compact interesting keys
    keys = [
        "summary",
        "title",
        "issueKey",
        "issue_key",
        "cloudId",
        "projectKey",
        "project_key",
        "body",
        "comment",
        "content",
        "spaceId",
        "pageId",
        "channel",
        "channel_id",
        "text",
        "message",
        "name",
        "inputs",
    ]
    bits = [f"tool={tool_name}"]
    for k in keys:
        if k in data and data[k] not in (None, ""):
            val = data[k]
            s = json.dumps(val, ensure_ascii=False) if isinstance(val, (dict, list)) else str(val)
            if len(s) > 180:
                s = s[:177] + "..."
            bits.append(f"{k}={s}")
    if len(bits) == 1:
        bits.append(f"args={json.dumps(data, ensure_ascii=False)[:300]}")
    return "; ".join(bits)


def is_atlassian_write(tool_name: str) -> bool:
    return tool_name in ATLASSIAN_WRITE_TOOLS


def is_atlassian_read(tool_name: str) -> bool:
    if tool_name in ATLASSIAN_WRITE_TOOLS:
        return False
    if tool_name.startswith(ATLASSIAN_READ_PREFIXES):
        return True
    # executeRead exact
    return tool_name == "executeRead"


def is_slack_server(payload: dict[str, Any]) -> bool:
    name = (payload.get("mcp_server_name") or "").lower()
    url = (payload.get("url") or payload.get("mcp_server_url") or "").lower()
    cmd = (payload.get("command") or "").lower()
    return "slack" in name or "slack" in url or "slack" in cmd


def is_slack_write(tool_name: str) -> bool:
    lower = (tool_name or "").lower()
    if any(h in lower for h in SLACK_READ_HINTS):
        return False
    write_hints = (
        "send",
        "post",
        "create",
        "update",
        "delete",
        "upload",
        "write",
        "set",
        "add",
        "remove",
        "chat",
        "message",
        "publish",
        "reply",
    )
    return any(h in lower for h in write_hints)
