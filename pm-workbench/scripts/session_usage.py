#!/usr/bin/env python3
"""Mine Claude Code session token usage into state/usage-history.csv.

Claude Code / pm-live only (Cursor Agent transcripts are out of scope).

Layers
  L0  Per assistant-message tokens from message.usage + session id + timestamp
  L1  Attach to preceding non-meta user turn (excerpt)
  L2a Rules-first category from user text (free; default)
  L2b Optional Haiku classify for unlabeled turns (--classify; opt-in).
      Uses the local `claude -p` CLI (existing Claude Code login) — not ANTHROPIC_API_KEY.

Usage
  python3 scripts/session_usage.py --root ~/pm-live --backfill
  python3 scripts/session_usage.py --root ~/pm-live --backfill --classify
  python3 scripts/session_usage.py --root ~/pm-live --reclassify   # L2b on existing other/none rows
  python3 scripts/session_usage.py --root ~/pm-live --summary

Idempotent by (session_id, message_uuid). Never invents "tokens saved."
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

HEADER = [
    "session_id",
    "message_uuid",
    "timestamp",
    "user_uuid",
    "user_excerpt",
    "category",
    "category_source",  # l2a | l2b | none
    "input_tokens",
    "output_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "model",
    "is_sidechain",
    "project",
    "indexed_date",
]

# Coarse enum + workflow:<name> (not open-ended topics)
COARSE = {
    "lookup",
    "explore_brief",
    "code_dive",
    "prototype",
    "capture",
    "rework_correction",
    "other",
}

CLUSTERS = ("capture", "brief", "sync", "discover", "build", "report")
WORKFLOWS = {
    "meeting-closeout",
    "process-inbox",
    "daily-brief",
    "return-brief",
    "meeting-prep",
    "get-started",
    "jira-reconcile",
    "ripple-check",
    "context-reconcile",
    "roadmap-update",
    "rotate-registers",
    "discovery",
    "research-plan",
    "research-package",
    "competitive-scan",
    "learn-product-flow",
    "code-dive",
    "explore-brief",
    "prd-package",
    "prototype-build",
    "prd-prototype-sync",
    "experiment-package",
    "experiment-analyze",
    "launch-package",
    "weekly-update",
    "okr-refresh",
    "strategy-refresh",
    "workbench-health",
    "monthly-review",
    "ship-signal",
    "quick-close",
    "todo",
}

SLASH_RE = re.compile(
    r"/(?:(?P<cluster>capture|brief|sync|discover|build|report)\s+)?"
    r"(?P<wf>[a-z][a-z0-9-]*)",
    re.I,
)
COMMAND_NAME_RE = re.compile(
    r"<command-name>\s*/(?P<cluster>capture|brief|sync|discover|build|report|todo|quick-close)"
    r"(?:\s+(?P<wf>[a-z][a-z0-9-]*))?\s*</command-name>",
    re.I,
)
COMMAND_ARGS_RE = re.compile(r"<command-args>\s*([a-z][a-z0-9-]*)", re.I)
INIT_COM_RE = re.compile(r"\b(?:INIT|COM)-\d+\b", re.I)
REWORK_RE = re.compile(
    r"\b(you ignored|wrong|fix that|redo|re-?do|try again|that's not what|"
    r"missed the|circular citation|you cited the brief)\b",
    re.I,
)
LOOKUP_RE = re.compile(
    r"\b(what did we (decide|commit)|what's due|what do we already know|"
    r"how did you check|where did .+ come from|is the inbox empty|"
    r"what'?s the state of)\b",
    re.I,
)
EXCERPT_MAX = 1600


def usage_path(root: Path) -> Path:
    return root / "state" / "usage-history.csv"


def ensure_usage(root: Path) -> Path:
    path = usage_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        with path.open("w", encoding="utf-8", newline="") as fh:
            csv.writer(fh, lineterminator="\n").writerow(HEADER)
    return path


def read_existing_keys(root: Path) -> set[tuple[str, str]]:
    path = ensure_usage(root)
    keys: set[tuple[str, str]] = set()
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            keys.add((row.get("session_id") or "", row.get("message_uuid") or ""))
    return keys


def default_projects_dirs(root: Path) -> list[Path]:
    """Claude Code project dirs that may hold this live workspace's sessions.

    Sessions are keyed by the folder Claude Code / Cursor opened — often the
    kit multi-root (`…/PM-workbench`) rather than `…/pm-live` alone. We scan
    both (and any other dir ending in the live folder name).
    """
    home = Path.home()
    claude = home / ".claude" / "projects"
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        try:
            path = path.resolve()
        except OSError:
            return
        if not path.is_dir():
            return
        # Case-insensitive dedupe (macOS APFS): PM-workbench vs pm-workbench
        key = str(path).lower()
        if key in seen:
            return
        seen.add(key)
        found.append(path)

    # Encoded absolute path: /Users/x/pm-live → -Users-x-pm-live
    encoded = str(root.resolve()).replace("/", "-")
    if not encoded.startswith("-"):
        encoded = f"-{encoded}"
    add(claude / encoded)

    name = root.resolve().name  # e.g. pm-live
    if claude.is_dir():
        for p in sorted(claude.glob(f"*-{name}")):
            add(p)
        # Kit / multi-root workspace that commonly hosts the same work
        parent = root.resolve().parent
        for kit_name in ("PM-workbench", "pm-workbench"):
            kit = parent / kit_name
            if kit.is_dir():
                kit_enc = str(kit.resolve()).replace("/", "-")
                if not kit_enc.startswith("-"):
                    kit_enc = f"-{kit_enc}"
                add(claude / kit_enc)
            for p in sorted(claude.glob(f"*-{kit_name}")):
                add(p)
    return found


def default_projects_dir(root: Path) -> Path:
    """Backward-compat: first discovered project dir."""
    dirs = default_projects_dirs(root)
    if dirs:
        return dirs[0]
    encoded = str(root.resolve()).replace("/", "-")
    if not encoded.startswith("-"):
        encoded = f"-{encoded}"
    return Path.home() / ".claude" / "projects" / encoded


def _text_from_message(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text") or "")
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return ""


def classify_l2a(user_text: str) -> tuple[str, str]:
    """Return (category, source) with source 'l2a' or 'none'→other."""
    text = user_text or ""
    if not text.strip():
        return "other", "none"

    m = COMMAND_NAME_RE.search(text)
    if m:
        cluster = (m.group("cluster") or "").lower()
        wf = (m.group("wf") or "").lower()
        if not wf:
            am = COMMAND_ARGS_RE.search(text)
            if am:
                wf = am.group(1).lower()
        if cluster in ("todo", "quick-close"):
            return f"workflow:{cluster}", "l2a"
        if wf in WORKFLOWS:
            return _coarse_or_workflow(wf), "l2a"
        if cluster in CLUSTERS and wf:
            return f"workflow:{wf}", "l2a"

    for m in SLASH_RE.finditer(text):
        cluster = (m.group("cluster") or "").lower()
        wf = (m.group("wf") or "").lower()
        if wf in ("todo", "quick-close"):
            return f"workflow:{wf}", "l2a"
        if wf in WORKFLOWS:
            return _coarse_or_workflow(wf), "l2a"
        if cluster and wf:
            return f"workflow:{wf}", "l2a"

    low = text.lower()
    if "explore-brief" in low or "explore brief" in low or "product brief" in low:
        return "explore_brief", "l2a"
    if "code-dive" in low or "code dive" in low or "how does" in low and "code" in low:
        return "code_dive", "l2a"
    if "prototype-build" in low or "prototype" in low and ("build" in low or "mock" in low):
        return "prototype", "l2a"
    if REWORK_RE.search(text):
        return "rework_correction", "l2a"
    if LOOKUP_RE.search(text) or INIT_COM_RE.search(text):
        return "lookup", "l2a"
    return "other", "none"


def _coarse_or_workflow(wf: str) -> str:
    if wf == "explore-brief":
        return "explore_brief"
    if wf == "code-dive":
        return "code_dive"
    if wf == "prototype-build":
        return "prototype"
    if wf in ("meeting-closeout", "process-inbox", "quick-close"):
        return "capture"
    return f"workflow:{wf}"


def _load_label_cache(root: Path) -> dict[str, str]:
    path = root / "state" / "usage-label-cache.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _save_label_cache(root: Path, cache: dict[str, str]) -> None:
    path = root / "state" / "usage-label-cache.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, indent=2) + "\n", encoding="utf-8")


def _log_classify_run(
    root: Path,
    *,
    user_uuid: str,
    status: str,
    category: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    note: str = "",
) -> None:
    log = root / "logs" / "usage-classify-runs.csv"
    log.parent.mkdir(parents=True, exist_ok=True)
    new = not log.is_file()
    with log.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(
                [
                    "timestamp",
                    "user_uuid",
                    "status",
                    "category",
                    "input_tokens",
                    "output_tokens",
                    "note",
                ]
            )
        w.writerow(
            [
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                user_uuid,
                status,
                category,
                input_tokens,
                output_tokens,
                note,
            ]
        )


def _resolve_claude_bin(claude_bin: str = "") -> str:
    candidate = (claude_bin or os.environ.get("CLAUDE_BIN") or "claude").strip()
    if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
        return candidate
    found = shutil.which(candidate)
    return found or ""


def classify_l2b(
    root: Path,
    user_uuid: str,
    user_text: str,
    assistant_first_line: str,
    cache: dict[str, str],
    *,
    claude_bin: str = "",
) -> tuple[str, str]:
    """Opt-in Haiku classify via `claude -p` (existing Claude Code login).

    Cached by user_uuid. Classifier spend is logged in usage-classify-runs.csv
    (token counts are often unavailable from the CLI — status/note still record
    each call). Never invents a category when classify fails.
    """
    if user_uuid and user_uuid in cache:
        return cache[user_uuid], "l2b"

    claude = _resolve_claude_bin(claude_bin)
    if not claude:
        _log_classify_run(
            root,
            user_uuid=user_uuid,
            status="skipped",
            note="claude CLI not on PATH; use Claude Code login (CLAUDE_BIN) — no API key",
        )
        return "other", "none"

    excerpt = (user_text or "")[:EXCERPT_MAX]
    assistant_bit = (assistant_first_line or "")[:400]
    prompt = (
        "Classify this PM workbench user turn into exactly one category label.\n"
        "Allowed labels only:\n"
        "  workflow:<name>  (name = kebab workflow e.g. daily-brief, prd-package)\n"
        "  lookup | explore_brief | code_dive | prototype | capture | "
        "rework_correction | other\n"
        "Reply with the label alone, no punctuation.\n\n"
        f"USER:\n{excerpt}\n\nASSISTANT_FIRST_LINE:\n{assistant_bit}\n"
    )
    cmd = [
        claude,
        "-p",
        prompt,
        "--model",
        "haiku",
        "--permission-mode",
        "dontAsk",
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
            check=False,
        )
        raw = (result.stdout or "").strip()
        # Prefer last non-empty line (claude -p sometimes prints chatter first)
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        label = (lines[-1] if lines else "").split()[0].lower() if lines else ""
        # Strip common wrapping
        label = label.strip("`\"'.,;:")
        if result.returncode != 0:
            err = ((result.stderr or "") + " " + raw).strip()[:200]
            _log_classify_run(
                root,
                user_uuid=user_uuid,
                status="error",
                category=label,
                note=f"claude -p exit {result.returncode}: {err}",
            )
            return "other", "none"
        if not _valid_category(label):
            _log_classify_run(
                root,
                user_uuid=user_uuid,
                status="invalid",
                category=label,
                note="label not in enum (via claude -p)",
            )
            return "other", "none"
        cache[user_uuid] = label
        _log_classify_run(
            root,
            user_uuid=user_uuid,
            status="ok",
            category=label,
            note="via claude -p haiku (login); token counts not reported by CLI",
        )
        return label, "l2b"
    except subprocess.TimeoutExpired:
        _log_classify_run(
            root,
            user_uuid=user_uuid,
            status="error",
            note="claude -p timed out",
        )
        return "other", "none"
    except Exception as e:
        _log_classify_run(
            root,
            user_uuid=user_uuid,
            status="error",
            note=str(e)[:200],
        )
        return "other", "none"


def _valid_category(label: str) -> bool:
    if not label:
        return False
    if label in COARSE:
        return True
    if label.startswith("workflow:"):
        name = label.split(":", 1)[1]
        return bool(name) and re.fullmatch(r"[a-z][a-z0-9-]*", name) is not None
    return False


def scan_session_file(
    path: Path,
    *,
    project: str,
    classify: bool,
    root: Path,
    label_cache: dict[str, str],
    claude_bin: str = "",
) -> list[dict]:
    session_id = path.stem
    rows: list[dict] = []
    last_user_uuid = ""
    last_user_text = ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return rows

    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        typ = obj.get("type")
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        role = msg.get("role") or typ

        if typ == "user" or role == "user":
            if obj.get("isMeta") or obj.get("isSidechain"):
                continue
            text = _text_from_message(msg)
            # skip empty command stdout noise without real ask
            if not text.strip():
                continue
            last_user_uuid = obj.get("uuid") or ""
            last_user_text = text
            continue

        if typ != "assistant" and role != "assistant":
            continue
        if obj.get("isSidechain"):
            continue
        usage = msg.get("usage") or obj.get("usage")
        if not isinstance(usage, dict):
            continue
        in_t = int(usage.get("input_tokens") or 0)
        out_t = int(usage.get("output_tokens") or 0)
        cc = int(usage.get("cache_creation_input_tokens") or 0)
        cr = int(usage.get("cache_read_input_tokens") or 0)
        if in_t + out_t + cc + cr == 0:
            continue

        uuid = obj.get("uuid") or ""
        if not uuid:
            continue

        category, source = classify_l2a(last_user_text)
        assistant_text = _text_from_message(msg)
        first_line = assistant_text.strip().splitlines()[0] if assistant_text.strip() else ""
        if classify and source == "none" and last_user_uuid:
            category, source = classify_l2b(
                root,
                last_user_uuid,
                last_user_text,
                first_line,
                label_cache,
                claude_bin=claude_bin,
            )

        excerpt = re.sub(r"\s+", " ", last_user_text).strip()[:EXCERPT_MAX]
        rows.append(
            {
                "session_id": session_id,
                "message_uuid": uuid,
                "timestamp": obj.get("timestamp") or "",
                "user_uuid": last_user_uuid,
                "user_excerpt": excerpt,
                "category": category,
                "category_source": source if source != "none" else ("none" if category == "other" else source),
                "input_tokens": str(in_t),
                "output_tokens": str(out_t),
                "cache_creation_input_tokens": str(cc),
                "cache_read_input_tokens": str(cr),
                "model": (msg.get("model") or obj.get("model") or ""),
                "is_sidechain": "yes" if obj.get("isSidechain") else "no",
                "project": project,
                "indexed_date": date.today().isoformat(),
            }
        )
    return rows


def backfill(
    root: Path,
    *,
    projects_dir: Path | None = None,
    projects_dirs: list[Path] | None = None,
    classify: bool = False,
    claude_bin: str = "",
) -> tuple[int, int]:
    """Scan jsonl; append new rows. Returns (appended, scanned_files)."""
    ensure_usage(root)
    keys = read_existing_keys(root)
    if projects_dirs:
        projs = [p for p in projects_dirs if p.is_dir()]
    elif projects_dir is not None:
        projs = [projects_dir] if projects_dir.is_dir() else []
    else:
        projs = default_projects_dirs(root)
    if not projs:
        print("ERROR: no Claude Code projects dirs found", file=sys.stderr)
        print(
            "Pass --projects-dir (comma-separated ok) under ~/.claude/projects/",
            file=sys.stderr,
        )
        return 0, 0

    label_cache = _load_label_cache(root) if classify else {}
    appended = 0
    files_total = 0
    out_path = usage_path(root)
    with out_path.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\n")
        for proj in projs:
            files = sorted(proj.glob("*.jsonl"))
            files_total += len(files)
            print(f"scanning {proj} ({len(files)} jsonl)")
            for path in files:
                for row in scan_session_file(
                    path,
                    project=proj.name,
                    classify=classify,
                    root=root,
                    label_cache=label_cache,
                    claude_bin=claude_bin,
                ):
                    key = (row["session_id"], row["message_uuid"])
                    if key in keys:
                        continue
                    writer.writerow(row)
                    keys.add(key)
                    appended += 1
    if classify:
        _save_label_cache(root, label_cache)
    print(f"projects_dirs={len(projs)}")
    print(f"files_scanned={files_total}")
    print(f"rows_appended={appended}")
    print(f"classify={'yes' if classify else 'no'}")
    return appended, files_total


def reclassify_existing(root: Path, *, claude_bin: str = "") -> int:
    """Run L2b on existing rows still labeled other/none. Updates CSV in place.

    One claude -p call per distinct user_uuid (cached). Returns rows updated.
    """
    path = ensure_usage(root)
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("reclassify_updated=0 (empty history)")
        return 0

    label_cache = _load_label_cache(root)
    # first excerpt per user_uuid among unlabeled rows
    pending: dict[str, str] = {}
    for r in rows:
        if (r.get("category") or "") != "other":
            continue
        if (r.get("category_source") or "none") not in ("none", "", "other"):
            continue
        uid = r.get("user_uuid") or ""
        if not uid or uid in pending:
            continue
        pending[uid] = r.get("user_excerpt") or ""

    print(f"reclassify_pending_user_turns={len(pending)}")
    for uid, excerpt in pending.items():
        cat, src = classify_l2b(
            root, uid, excerpt, "", label_cache, claude_bin=claude_bin
        )
        if src != "l2b":
            continue
        for r in rows:
            if r.get("user_uuid") == uid and (r.get("category") or "") == "other":
                r["category"] = cat
                r["category_source"] = "l2b"

    _save_label_cache(root, label_cache)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    updated = sum(1 for r in rows if r.get("category_source") == "l2b")
    print(f"reclassify_rows_with_l2b={updated}")
    return updated


def summarize(root: Path, days: int = 30) -> None:
    path = usage_path(root)
    if not path.is_file():
        print("no usage-history.csv yet; run --backfill")
        return
    today = date.today()
    by_cat: dict[str, int] = {}
    totals = {"input": 0, "output": 0, "cache_create": 0, "cache_read": 0, "msgs": 0}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            ts = (row.get("timestamp") or "")[:10]
            try:
                d = date.fromisoformat(ts)
            except ValueError:
                continue
            if (today - d).days > days:
                continue
            totals["msgs"] += 1
            totals["input"] += int(row.get("input_tokens") or 0)
            totals["output"] += int(row.get("output_tokens") or 0)
            totals["cache_create"] += int(row.get("cache_creation_input_tokens") or 0)
            totals["cache_read"] += int(row.get("cache_read_input_tokens") or 0)
            cat = row.get("category") or "other"
            tok = (
                int(row.get("input_tokens") or 0)
                + int(row.get("output_tokens") or 0)
                + int(row.get("cache_creation_input_tokens") or 0)
                + int(row.get("cache_read_input_tokens") or 0)
            )
            by_cat[cat] = by_cat.get(cat, 0) + tok
    print(f"last_{days}d_assistant_msgs={totals['msgs']}")
    print(f"input_tokens={totals['input']}")
    print(f"output_tokens={totals['output']}")
    print(f"cache_creation_input_tokens={totals['cache_create']}")
    print(f"cache_read_input_tokens={totals['cache_read']}")
    total_tok = sum(by_cat.values()) or 1
    print("by_category_tokens (not 'tokens saved'):")
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1])[:12]:
        print(f"  {cat}: {n} ({100.0 * n / total_tok:.1f}%)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--root", required=True, help="live workspace root (e.g. ~/pm-live)")
    p.add_argument(
        "--projects-dir",
        default="",
        help="override project dir(s); comma-separated. Default: pm-live + PM-workbench encodings",
    )
    p.add_argument("--backfill", action="store_true")
    p.add_argument(
        "--classify",
        action="store_true",
        help="with --backfill: L2b via claude -p for newly scanned unlabeled turns",
    )
    p.add_argument(
        "--reclassify",
        action="store_true",
        help="L2b via claude -p on existing other/none rows in usage-history.csv",
    )
    p.add_argument(
        "--claude",
        default=os.environ.get("CLAUDE_BIN") or "claude",
        help="claude CLI binary for classify/reclassify (default: CLAUDE_BIN or claude on PATH)",
    )
    p.add_argument("--summary", action="store_true")
    p.add_argument("--days", type=int, default=30)
    args = p.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    projects_dirs = None
    projects = None
    if args.projects_dir:
        parts = [p.strip() for p in args.projects_dir.split(",") if p.strip()]
        projects_dirs = [Path(os.path.expanduser(p)).resolve() for p in parts]
    if args.backfill:
        backfill(
            root,
            projects_dir=projects,
            projects_dirs=projects_dirs,
            classify=args.classify,
            claude_bin=args.claude,
        )
    if args.reclassify:
        reclassify_existing(root, claude_bin=args.claude)
    if args.summary or not (args.backfill or args.reclassify):
        summarize(root, days=args.days)
    if not args.backfill and not args.summary and not args.reclassify:
        print("pass --backfill and/or --reclassify and/or --summary", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
