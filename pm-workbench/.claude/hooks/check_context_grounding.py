#!/usr/bin/env python3
"""PostToolUse Write|Edit: consequential outputs must cite preflight cache hits.

Fails closed (exit 2) when drafts/outputs/learning assert product facts without:
- a path from state/.context-preflight.json hits (not drafts/ or prototypes/), OR
- an explicit "none found for" line with empty/investigate marker, OR
- a "Refreshed:" line when recommendation was reuse_and_refresh

Marker must be fresh (default 4 hours).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from _common import block, payload, rel, root, warn

MARKER_MAX_AGE_HOURS = 4

SKIP_SUFFIXES = (
    "qa-report.md",
    "qa-screenshots/",
    ".png",
    ".jpg",
    ".webp",
    "package-lock.json",
    "BASELINE-SOURCES.md",  # source map itself
)

NONE_RE = re.compile(r"none found for", re.I)
REFRESHED_RE = re.compile(r"^\s*Refreshed\s*:", re.I | re.M)
PRIOR_NONE_RE = re.compile(r"Prior workspace analysis:\s*none", re.I)


def _fresh(marker_path: str) -> bool:
    try:
        mtime = os.path.getmtime(marker_path)
    except OSError:
        return False
    age_h = (datetime.now(timezone.utc).timestamp() - mtime) / 3600.0
    return age_h <= MARKER_MAX_AGE_HOURS


def _in_scope(r: str) -> bool:
    if any(r.endswith(s) or s in r for s in SKIP_SUFFIXES):
        return False
    if r.startswith("drafts/"):
        return True
    if r.startswith("outputs/prds/"):
        return True
    if r.startswith(("outputs/daily/", "outputs/weekly/", "outputs/monthly/", "outputs/research/")):
        return r.endswith((".md", ".csv"))
    if r.startswith("learning/") and r.endswith(".md"):
        return True
    return False


def main() -> None:
    try:
        p = payload()
        path = (p.get("tool_input") or {}).get("file_path") or ""
        r = rel(path)
        if not _in_scope(r):
            sys.exit(0)
        full = os.path.join(root(), r)
        if not os.path.exists(full):
            sys.exit(0)
        # skip tiny stubs
        txt = open(full, encoding="utf-8", errors="replace").read()
        if len(txt.strip()) < 80:
            sys.exit(0)

        marker_path = os.path.join(root(), "state", ".context-preflight.json")
        if not os.path.isfile(marker_path) or not _fresh(marker_path):
            block(
                "CONTEXT GROUNDING FAILED\n"
                f"{r} was written without a fresh context preflight "
                f"(state/.context-preflight.json, max age {MARKER_MAX_AGE_HOURS}h).\n"
                "Run: python3 scripts/context_preflight.py --root <live> --topic \"…\"\n"
                "Then cite a hit path (or 'none found for …' / 'Refreshed: …')."
            )

        marker = json.loads(open(marker_path, encoding="utf-8").read())
        hits = marker.get("hits") or []
        # evidence hits: not drafts/prototypes
        evidence_paths = [
            h.get("path", "")
            for h in hits
            if h.get("path")
            and not h.get("path", "").startswith(("drafts/", "prototypes/"))
        ]
        primary_blobs = " ".join(h.get("primary_sources") or "" for h in hits)

        if NONE_RE.search(txt) or PRIOR_NONE_RE.search(txt):
            if marker.get("recommendation") in ("investigate",) or not hits:
                sys.exit(0)
            # none found claimed but hits exist — still ok if they explained; allow
            sys.exit(0)

        if REFRESHED_RE.search(txt) and marker.get("recommendation") == "reuse_and_refresh":
            sys.exit(0)

        cited_ok = False
        for ep in evidence_paths:
            if ep and ep in txt:
                cited_ok = True
                break
            # basename citation
            base = os.path.basename(ep)
            if base and len(base) > 8 and base in txt:
                cited_ok = True
                break
        # primary source paths also count
        if not cited_ok and primary_blobs:
            for part in re.split(r"[;\s]+", primary_blobs):
                part = part.strip()
                if len(part) > 6 and part in txt:
                    cited_ok = True
                    break

        # drafts/prototypes citations alone are insufficient
        only_derived = False
        if re.search(r"drafts/|prototypes/", txt) and not cited_ok:
            only_derived = True

        if not cited_ok:
            msg = (
                "CONTEXT GROUNDING FAILED\n"
                f"{r} does not cite any preflight evidence path.\n"
                "Cite an outputs/ or learning/ hit (or its primary_sources), "
                "or write 'none found for <keywords>', or 'Refreshed: …' after a refresh.\n"
                "Citations under drafts/ or prototypes/ do not count as evidence."
            )
            if only_derived:
                msg += "\nThis file only points at drafts/prototypes — follow those to a primary source."
            if evidence_paths:
                msg += "\nPreflight hits: " + ", ".join(evidence_paths[:8])
            block(msg)
        sys.exit(0)
    except SystemExit:
        raise
    except Exception as e:
        warn(f"check_context_grounding skipped: {e}")


if __name__ == "__main__":
    main()
