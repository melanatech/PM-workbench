"""Shared helpers for the session-memory hooks (Plan E Part 2). Standard library only.

Every hook fails open: any error, an unrecognized payload, a Cursor payload, or
SESSION_MEMORY_INTERNAL=1 means exit 0 with no output. Session memory never writes
a project's own files (pm-brain, registers); it only writes under its data home.
"""
import datetime
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
INSTRUCTIONS = os.path.join(MODULE, "haiku-instructions.md")
SNAPSHOT_SECTIONS = ("Goal", "Where it stands")
SECTIONS = SNAPSHOT_SECTIONS + ("Decisions", "Constraints", "Corrections", "Don't retry", "Open questions")
CURSOR_KEYS = ("cursor_version", "conversation_id", "workspace_roots", "generation_id")
CORRECTION_WORDS = re.compile(r"\b(no|don't|dont|wrong|instead|stop|undo|actually|scratch that)\b", re.I)


def env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def data_home():
    return os.path.expanduser(os.environ.get("SESSION_MEMORY_HOME") or "~/.claude/session-memory")


def read_payload():
    """The hook payload, or None when this hook must stay silent."""
    if os.environ.get("SESSION_MEMORY_INTERNAL") == "1":
        return None
    try:
        data = json.load(sys.stdin)
    except Exception:
        return None
    if not isinstance(data, dict) or is_cursor(data) or not data.get("session_id"):
        return None
    return data


def is_cursor(payload):
    """Cursor Agent runs user-level Claude hooks with its own payload shape. Until the PM's probe test
    settles whether session memory should run there, every script exits 0 on a Cursor payload."""
    return any(key in payload for key in CURSOR_KEYS)


def slug(cwd):
    return (cwd or "unknown").replace("/", "-")


def project_dir(payload):
    path = os.path.join(data_home(), slug(payload.get("cwd") or os.getcwd()))
    os.makedirs(path, exist_ok=True)
    return path


def register_path(payload, session_id=None):
    return os.path.join(project_dir(payload), f"{session_id or payload['session_id']}.jsonl")


def now_iso():
    return datetime.datetime.now().isoformat(timespec="seconds")


def log_event(payload, event, **fields):
    try:
        with open(os.path.join(project_dir(payload), "log.jsonl"), "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"ts": now_iso(), "session": payload.get("session_id"), "event": event,
                                     **fields}, ensure_ascii=False) + "\n")
    except OSError:
        pass


@contextmanager
def locked(path, wait=10.0):
    """Exclusive lock on <path>.lock. Yields True if taken within `wait` seconds."""
    handle = open(path + ".lock", "a+")
    deadline, got = time.time() + wait, False
    try:
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                got = True
                break
            except OSError:
                if time.time() >= deadline:
                    break
                time.sleep(0.1)
        yield got
    finally:
        if got:
            fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


# ---- register (same supersession rule as pm-workbench/scripts/register_view.py) ----

def superseded_ids(entries):
    """Ids a later entry lists in `supersedes`, plus entries an audit dropped."""
    seen, gone = set(), set()
    for entry in entries:
        for old in entry.get("supersedes") or []:
            if old in seen and old != entry.get("id"):
                gone.add(old)
        if entry.get("dropped"):
            gone.add(entry.get("id"))
        seen.add(entry.get("id"))
    return gone


def active_entries(entries):
    gone = superseded_ids(entries)
    return [e for e in entries if e.get("id") not in gone and e.get("section") != "audit"]


def load_entries(path):
    out = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        continue
    except OSError:
        pass
    return out


def append_entries(path, new):
    with open(path, "a", encoding="utf-8") as handle:
        for entry in new:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def next_id(entries):
    nums = [int(e["id"][1:]) for e in entries if re.fullmatch(r"e\d+", str(e.get("id", "")))]
    return f"e{max(nums, default=0) + 1}"


def apply_ops(entries, ops, turn=None):
    """Turn model operations into new register lines. Unknown ops and sections are ignored."""
    new, known = [], {e.get("id") for e in entries}
    active = active_entries(entries)
    for op in ops if isinstance(ops, list) else []:
        if not isinstance(op, dict):
            continue
        kind, section, text = op.get("op"), op.get("section"), (op.get("text") or "").strip()
        ids = [i for i in op.get("ids") or [] if i in known]
        if kind == "drop" and ids:
            for i in ids:
                new.append({"id": next_id(entries + new), "section": "audit", "text": f"dropped {i}",
                            "date": now_iso(), "turn": turn, "supersedes": [i], "dropped": False})
            continue
        if kind not in ("add", "supersede") or section not in SECTIONS or not text:
            continue
        if section in SNAPSHOT_SECTIONS:
            ids = sorted(set(ids) | {e["id"] for e in active if e.get("section") == section})
        if kind == "add" and section not in SNAPSHOT_SECTIONS:
            ids = []
        new.append({"id": next_id(entries + new), "section": section, "text": text[:1200], "date": now_iso(),
                    "turn": turn, "supersedes": ids, "dropped": False})
    return new


def render(entries, heading=True):
    lines = []
    for section in SECTIONS:
        items = [e for e in entries if e.get("section") == section]
        if items:
            if heading:
                lines.append(f"## {section}")
            lines += [f"- [{e['id']}, {str(e.get('date', ''))[:10]}] {e['text']}" for e in items]
    return "\n".join(lines)


def word_count(entries):
    return sum(len((e.get("text") or "").split()) for e in entries)


# ---- index ----

def update_index(payload, **fields):
    path = os.path.join(project_dir(payload), "index.json")
    with locked(path, wait=5) as got:
        if not got:
            return
        try:
            index = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError):
            index = {}
        rec = index.setdefault(payload["session_id"], {"first": now_iso(), "captures": 0})
        rec["last"] = now_iso()
        for key, value in fields.items():
            if key == "captures_add":
                rec["captures"] = rec.get("captures", 0) + value
            elif key == "picked_from":
                rec.setdefault("picked_from", []).append(value)
            else:
                rec[key] = value
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(index, handle, indent=1, ensure_ascii=False)
    return rec


def read_index(payload):
    try:
        return json.load(open(os.path.join(project_dir(payload), "index.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return {}


# ---- transcript ----

def transcript_entries(path):
    out = []
    try:
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                if row.get("type") in ("user", "assistant") and not row.get("isSidechain"):
                    out.append(row)
    except (OSError, TypeError):
        pass
    return out


def user_text(row):
    """Text the user typed, or None for tool results and hook-injected rows."""
    content = (row.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list) and not any(b.get("type") == "tool_result" for b in content if isinstance(b, dict)):
        text = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        return text or None
    return None


def assistant_text(row):
    content = (row.get("message") or {}).get("content")
    if isinstance(content, list):
        return " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
    return content if isinstance(content, str) else ""


def tool_errors(row):
    content = (row.get("message") or {}).get("content")
    if not isinstance(content, list):
        return ""
    errs = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "tool_result" and block.get("is_error"):
            body = block.get("content")
            errs.append(body if isinstance(body, str) else json.dumps(body)[:300])
    return " ".join(errs)


def exchanges(rows):
    """[(user_prompt, assistant_text, tool_errors)] in order."""
    out = []
    for row in rows:
        if row.get("type") == "user":
            text = user_text(row)
            if text is not None:
                out.append([text, "", ""])
            elif out:
                out[-1][2] += tool_errors(row)
        elif out:
            out[-1][1] += (" " if out[-1][1] else "") + assistant_text(row)
    return [tuple(x) for x in out]


def last_usage(rows):
    """(timestamp, context_tokens) of the last assistant row with usage, or (None, 0)."""
    for row in reversed(rows):
        usage = (row.get("message") or {}).get("usage") if row.get("type") == "assistant" else None
        if usage:
            tokens = sum(int(usage.get(k) or 0) for k in
                         ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
            return row.get("timestamp"), tokens
    return None, 0


def parse_ts(text):
    try:
        return datetime.datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None


# ---- model calls ----

def call_budget_ok(record=True):
    """Daily cap on headless model calls across all projects (SESSION_MEMORY_DAILY_CALLS, default 200)."""
    cap = env_int("SESSION_MEMORY_DAILY_CALLS", 200)
    path = os.path.join(data_home(), f"calls-{datetime.date.today().isoformat()}.count")
    os.makedirs(data_home(), exist_ok=True)
    with locked(path, wait=2) as got:
        if not got:
            return False
        try:
            used = int(open(path).read().strip() or 0)
        except (OSError, ValueError):
            used = 0
        if used >= cap:
            return False
        if record:
            with open(path, "w") as handle:
                handle.write(str(used + 1))
    return True


def ask_model(prompt, timeout=60, model=None):
    """Run the headless model once. Returns the text reply, or None (over cap, timeout, error)."""
    if not call_budget_ok():
        return None
    claude = os.environ.get("SESSION_MEMORY_CLAUDE") or "claude"
    env = {**os.environ, "SESSION_MEMORY_INTERNAL": "1"}
    try:
        result = subprocess.run([claude, "-p", prompt, "--model", model or os.environ.get("SESSION_MEMORY_MODEL", "haiku")],
                                capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 else None


def parse_json(text):
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None


def instructions():
    try:
        return open(INSTRUCTIONS, encoding="utf-8").read()
    except OSError:
        return ""


def emit_context(event, text, user_message=None):
    out = {"hookSpecificOutput": {"hookEventName": event, "additionalContext": text}}
    if user_message:
        out["systemMessage"] = user_message
    print(json.dumps(out))
