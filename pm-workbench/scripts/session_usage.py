#!/usr/bin/env python3
"""Mine Claude Code session token usage into state/usage-history.csv.

Claude Code / pm-live only (Cursor Agent transcripts are out of scope).

Layers
  L0  Per assistant-message tokens from message.usage + session id + timestamp
  L1  Attach to preceding non-meta user turn (excerpt)
  L2a Rules-first category from user text (free; default)
  L2b Optional Haiku classify for unlabeled turns (--classify / --reclassify).
      Uses the local `claude -p` CLI (existing Claude Code login) — not ANTHROPIC_API_KEY.
      Classification is **bulk**: many user turns per Haiku call (not one call per turn).

Usage
  python3 scripts/session_usage.py --root ~/pm-live --backfill
  python3 scripts/session_usage.py --root ~/pm-live --backfill --classify
  python3 scripts/session_usage.py --root ~/pm-live --reclassify   # L2b bulk on other/none rows
  python3 scripts/session_usage.py --root ~/pm-live --backfill-surface
  python3 scripts/session_usage.py --root ~/pm-live --summary

Idempotent by (session_id, message_uuid). Never invents "tokens saved."

``surface`` comes from the transcript ``entrypoint`` via ``scripts/transcripts.py``:
``cli`` → terminal, ``sdk-cli`` → headless (``claude -p``), ``claude-vscode`` →
panel (VS Code/Cursor). Unknown entrypoints stay as the raw value.
``--backfill-surface`` rewrites existing rows in place on that key and copies
the CSV to ``state/usage-history.csv.bak`` first.
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

import transcripts

# Bulk L2b: ~20 turns/call, short excerpts, keep prompt bounded
BULK_BATCH_SIZE = 20
BULK_EXCERPT_MAX = 400
BULK_PROMPT_CHAR_CAP = 14000

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
    "surface",
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


def _parse_bulk_labels(raw: str, n: int) -> dict[int, str]:
    """Parse lines like '1\\tlookup' or '1: lookup' into {1-based index: label}."""
    out: dict[int, str] = {}
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(\d+)\s*[\:\|\t\-]\s*(\S+)", line)
        if not m:
            m = re.match(r"^(\d+)\s+(\S+)", line)
        if not m:
            continue
        idx = int(m.group(1))
        label = m.group(2).lower().strip("`\"'.,;:")
        if 1 <= idx <= n and _valid_category(label):
            out[idx] = label
    return out


def classify_l2b_bulk(
    root: Path,
    items: list[tuple[str, str]],
    cache: dict[str, str],
    *,
    claude_bin: str = "",
    batch_size: int = BULK_BATCH_SIZE,
) -> int:
    """Classify many (user_uuid, excerpt) pairs via batched `claude -p` calls.

    Returns number of uuids newly labeled into cache. Skips uuids already cached.
    """
    pending = [(uid, ex) for uid, ex in items if uid and uid not in cache]
    if not pending:
        return 0

    claude = _resolve_claude_bin(claude_bin)
    if not claude:
        _log_classify_run(
            root,
            user_uuid="(batch)",
            status="skipped",
            note="claude CLI not on PATH; use Claude Code login (CLAUDE_BIN) — no API key",
        )
        return 0

    labeled = 0
    i = 0
    batch_num = 0
    while i < len(pending):
        batch: list[tuple[str, str]] = []
        prompt_len = 0
        header = (
            "Classify each PM workbench user turn. Reply with one line per turn, "
            "exactly: <n>\\t<label>  (n starts at 1). No other text.\n"
            "Allowed labels only:\n"
            "  workflow:<name>  (kebab workflow e.g. daily-brief, prd-package)\n"
            "  lookup | explore_brief | code_dive | prototype | capture | "
            "rework_correction | other\n"
            "Use setup-ish plugin/MCP/auth asks as other; short yes/1/ok as other; "
            "session-continue summaries as other.\n\n"
        )
        prompt_len = len(header)
        while i < len(pending) and len(batch) < batch_size:
            uid, excerpt = pending[i]
            piece = (excerpt or "")[:BULK_EXCERPT_MAX].replace("\n", " ").strip()
            line = f"{len(batch) + 1}. {piece}\n"
            if batch and prompt_len + len(line) > BULK_PROMPT_CHAR_CAP:
                break
            batch.append((uid, piece))
            prompt_len += len(line)
            i += 1
        if not batch:
            break
        batch_num += 1
        body = "".join(f"{n}. {ex}\n" for n, (_, ex) in enumerate(batch, start=1))
        prompt = header + body
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
                timeout=180,
                check=False,
            )
            raw = (result.stdout or "").strip()
            parsed = _parse_bulk_labels(raw, len(batch))
            if result.returncode != 0 and not parsed:
                err = ((result.stderr or "") + " " + raw).strip()[:200]
                _log_classify_run(
                    root,
                    user_uuid=f"(batch-{batch_num})",
                    status="error",
                    note=f"claude -p exit {result.returncode}: {err}",
                )
                continue
            for n, (uid, _) in enumerate(batch, start=1):
                label = parsed.get(n)
                if not label:
                    _log_classify_run(
                        root,
                        user_uuid=uid,
                        status="invalid",
                        note=f"missing/invalid in bulk batch-{batch_num}",
                    )
                    continue
                cache[uid] = label
                labeled += 1
                _log_classify_run(
                    root,
                    user_uuid=uid,
                    status="ok",
                    category=label,
                    note=f"via claude -p haiku bulk batch-{batch_num} size={len(batch)}",
                )
            print(f"bulk_batch={batch_num} size={len(batch)} labeled={len(parsed)}/{len(batch)}")
        except subprocess.TimeoutExpired:
            _log_classify_run(
                root,
                user_uuid=f"(batch-{batch_num})",
                status="error",
                note="claude -p bulk timed out",
            )
        except Exception as e:
            _log_classify_run(
                root,
                user_uuid=f"(batch-{batch_num})",
                status="error",
                note=str(e)[:200],
            )
    return labeled


def classify_l2b(
    root: Path,
    user_uuid: str,
    user_text: str,
    assistant_first_line: str,
    cache: dict[str, str],
    *,
    claude_bin: str = "",
) -> tuple[str, str]:
    """Classify one turn (uses bulk helper with a single-item batch). Prefer reclassify bulk path."""
    if user_uuid and user_uuid in cache:
        return cache[user_uuid], "l2b"
    classify_l2b_bulk(
        root,
        [(user_uuid, user_text or "")],
        cache,
        claude_bin=claude_bin,
        batch_size=1,
    )
    if user_uuid in cache:
        return cache[user_uuid], "l2b"
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
    session_entrypoint = ""

    for obj in transcripts.iter_records(path):
        entrypoint = transcripts.record_entrypoint(obj)
        if entrypoint and not session_entrypoint:
            session_entrypoint = entrypoint
        typ = obj.get("type")
        msg = obj.get("message") if isinstance(obj.get("message"), dict) else {}
        role = msg.get("role") or typ

        if transcripts.is_human_turn(obj):
            last_user_uuid = obj.get("uuid") or ""
            last_user_text = transcripts.message_text(obj)
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
        # L2b is bulk-only via reclassify_existing / --classify after scan — not per message.

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
                "surface": transcripts.surface_from_entrypoint(entrypoint or session_entrypoint),
            }
        )
    return rows


def _csv_header(path: Path) -> list[str]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        line = fh.readline()
    if not line.strip():
        return []
    return next(csv.reader([line]))


def _backup_usage(path: Path) -> Path:
    """Copy the CSV beside itself before an in-place rewrite."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = path.with_name(path.name + ".bak")
    if backup.exists():
        backup = path.with_name(f"{path.name}.bak-{stamp}")
    shutil.copy2(path, backup)
    return backup


def _resolve_projects(
    root: Path,
    projects_dir: Path | None,
    projects_dirs: list[Path] | None,
) -> list[Path]:
    if projects_dirs:
        return [p for p in projects_dirs if p.is_dir()]
    if projects_dir is not None:
        return [projects_dir] if projects_dir.is_dir() else []
    return default_projects_dirs(root)


def backfill_surface(
    root: Path,
    *,
    projects_dir: Path | None = None,
    projects_dirs: list[Path] | None = None,
    all_projects: bool = False,
) -> tuple[int, int, Path | None]:
    """Add or refresh ``surface`` on existing rows. Update in place.

    Keyed on ``(session_id, message_uuid)``. Copies the CSV to
    ``usage-history.csv.bak`` (or a stamped name if that backup exists)
    before writing. Returns ``(rows_updated, rows_unmatched, backup_path)``.
    Does not append new usage rows.
    """
    path = ensure_usage(root)
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    header = _csv_header(path)
    if not rows and header == HEADER:
        print("surface_rows_updated=0")
        print("surface_rows_unmatched=0")
        return 0, 0, None

    if projects_dirs or projects_dir is not None:
        projs = _resolve_projects(root, projects_dir, projects_dirs)
        files = transcripts.session_files(projs)
    elif all_projects or not header or "surface" not in header:
        files = transcripts.session_files()
    else:
        projs = default_projects_dirs(root)
        files = transcripts.session_files(projs)
        if not files:
            files = transcripts.session_files()

    needed = {(r.get("session_id") or "", r.get("message_uuid") or "") for r in rows}
    by_message, by_session = transcripts.index_message_surfaces(files, needed=needed)

    updated = 0
    unmatched = 0
    column_added = "surface" not in header
    changed = header != HEADER
    for row in rows:
        key = (row.get("session_id") or "", row.get("message_uuid") or "")
        surface = by_message.get(key) or ""
        if not surface:
            surface = transcripts.surface_from_entrypoint(by_session.get(key[0], ""))
        if not surface:
            unmatched += 1
        previous = row.get("surface") or ""
        if previous != surface:
            updated += 1
            changed = True
        row["surface"] = surface
        for column in HEADER:
            row.setdefault(column, "")

    if not changed:
        print("surface_rows_updated=0")
        print(f"surface_rows_unmatched={unmatched}")
        print("surface_backup=none")
        return 0, unmatched, None

    backup = _backup_usage(path)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"surface_rows_updated={updated}")
    print(f"surface_rows_unmatched={unmatched}")
    print(f"surface_rows={len(rows)}")
    print(f"surface_column_added={'yes' if column_added else 'no'}")
    print(f"surface_backup={backup}")
    return updated, unmatched, backup


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
    header = _csv_header(usage_path(root))
    if header and header != HEADER:
        backfill_surface(
            root,
            projects_dir=projects_dir,
            projects_dirs=projects_dirs,
        )
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
    print(f"projects_dirs={len(projs)}")
    print(f"files_scanned={files_total}")
    print(f"rows_appended={appended}")
    print(f"classify={'deferred-bulk' if classify else 'no'}")
    if classify:
        print("running bulk L2b reclassify on other/none rows…")
        reclassify_existing(root, claude_bin=claude_bin)
    return appended, files_total


def reclassify_existing(root: Path, *, claude_bin: str = "") -> int:
    """Run L2b on existing rows still labeled other/none. Updates CSV in place.

    Bulk: many user turns per `claude -p` call (see BULK_BATCH_SIZE). Returns
    count of rows now carrying category_source=l2b.
    """
    path = ensure_usage(root)
    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        print("reclassify_updated=0 (empty history)")
        return 0

    label_cache = _load_label_cache(root)
    pending: dict[str, str] = {}
    for r in rows:
        if (r.get("category") or "") != "other":
            continue
        if (r.get("category_source") or "none") not in ("none", "", "other"):
            continue
        uid = r.get("user_uuid") or ""
        if not uid or uid in pending:
            continue
        # Skip if cache already has a label from a prior run
        if uid in label_cache and _valid_category(label_cache[uid]):
            continue
        pending[uid] = r.get("user_excerpt") or ""

    print(f"reclassify_pending_user_turns={len(pending)}")
    print(f"reclassify_bulk_batch_size={BULK_BATCH_SIZE}")
    classify_l2b_bulk(
        root,
        list(pending.items()),
        label_cache,
        claude_bin=claude_bin,
    )

    for r in rows:
        uid = r.get("user_uuid") or ""
        if uid in label_cache and (r.get("category") or "") == "other":
            r["category"] = label_cache[uid]
            r["category_source"] = "l2b"
        for column in HEADER:
            r.setdefault(column, "")

    _save_label_cache(root, label_cache)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=HEADER, extrasaction="ignore", lineterminator="\n")
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
    by_surface: dict[str, list[int]] = {}
    by_model: dict[str, list[int]] = {}
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
            surface = row.get("surface") or "(blank)"
            model = row.get("model") or "(blank)"
            for bucket, key in ((by_surface, surface), (by_model, model)):
                msgs, tokens = bucket.get(key, [0, 0])
                bucket[key] = [msgs + 1, tokens + tok]
    print(f"last_{days}d_assistant_msgs={totals['msgs']}")
    print(f"input_tokens={totals['input']}")
    print(f"output_tokens={totals['output']}")
    print(f"cache_creation_input_tokens={totals['cache_create']}")
    print(f"cache_read_input_tokens={totals['cache_read']}")
    total_tok = sum(by_cat.values()) or 1
    print("by_category_tokens (not 'tokens saved'):")
    for cat, n in sorted(by_cat.items(), key=lambda x: -x[1])[:12]:
        print(f"  {cat}: {n} ({100.0 * n / total_tok:.1f}%)")
    print("by_surface (terminal=cli, headless=sdk-cli/claude -p, panel=claude-vscode; raw if unknown):")
    for name, (msgs, n) in sorted(by_surface.items(), key=lambda x: -x[1][1]):
        print(f"  {name}: msgs={msgs} tokens={n} ({100.0 * n / total_tok:.1f}%)")
    print("by_model:")
    for name, (msgs, n) in sorted(by_model.items(), key=lambda x: -x[1][1]):
        print(f"  {name}: msgs={msgs} tokens={n} ({100.0 * n / total_tok:.1f}%)")


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
    p.add_argument(
        "--backfill-surface",
        action="store_true",
        help="update surface on existing rows in place (backs up the CSV first)",
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
        parts = [item.strip() for item in args.projects_dir.split(",") if item.strip()]
        projects_dirs = [Path(os.path.expanduser(item)).resolve() for item in parts]
    if args.backfill_surface:
        backfill_surface(
            root,
            projects_dir=projects,
            projects_dirs=projects_dirs,
            all_projects=not args.projects_dir,
        )
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
    acted = args.backfill or args.reclassify or args.backfill_surface
    if args.summary or not acted:
        summarize(root, days=args.days)
    if not acted and not args.summary:
        print(
            "pass --backfill and/or --backfill-surface and/or --reclassify and/or --summary",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
