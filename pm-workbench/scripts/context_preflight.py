#!/usr/bin/env python3
"""Cache-first context preflight (like intake_status for analyses).

Usage:
  python3 scripts/context_preflight.py --root ~/pm-live --topic "INIT-033 instrumentation"
  python3 scripts/context_preflight.py --root ~/pm-live --backfill-scan
  python3 scripts/context_preflight.py --root ~/pm-live --topic "…" --allow-repos

Writes state/.context-preflight.json and appends logs/context-preflight.csv.
Exit 0 when root ok (empty hits valid); exit 2 on bad root.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(_SCRIPTS))

import analysis_index  # noqa: E402

SCAN_DIRS = (
    "outputs/daily",
    "outputs/weekly",
    "outputs/monthly",
    "outputs/prds",
    "outputs/research",
    "outputs/todo-drafts",
    "learning",
    "drafts",
    "state/web-search",
    "state/competitive",
)

KIND_HINTS = (
    ("instrumentation", ("instrument", "instrumentation", "tracking")),
    ("events", ("event", "events", "analytics-events")),
    ("code-dive", ("code-dive", "code dive", "code-findings")),
    ("product-flow", ("product-flow", "learn-product")),
    ("competitive", ("competitive", "competitor")),
    ("web-search", ("web-search", "state/web-search")),
    ("strategy", ("strategy", "okr")),
    ("reconcile", ("reconcil",)),
    ("research", ("research",)),
    ("brief", ("product-brief", "explore-brief", "check-in")),
    ("discovery", ("discovery", "evidence")),
)

DATE_RE = re.compile(r"(20\d{2}-\d{2}-\d{2})")
INIT_RE = re.compile(r"\bINIT-\d{3,5}\b", re.I)
COM_RE = re.compile(r"\bCOM-\d{3,5}\b", re.I)
# Table row: | phrase | `path` | meaning |
ALIAS_ROW_RE = re.compile(
    r"^\|\s*([^|]+?)\s*\|\s*`?([^|`]+?)`?\s*\|\s*([^|]*)\|?\s*$",
    re.M,
)


def _load_aliases(root: Path) -> list[dict]:
    """Read reference/context/workspace-aliases.md (or .example.md)."""
    for name in ("workspace-aliases.md", "workspace-aliases.example.md"):
        path = root / "reference" / "context" / name
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        out = []
        for m in ALIAS_ROW_RE.finditer(text):
            phrase = m.group(1).strip()
            dest = m.group(2).strip()
            meaning = m.group(3).strip()
            if phrase.lower() in ("phrase", "---") or phrase.startswith("-"):
                continue
            if not dest or dest.lower() == "path":
                continue
            out.append({"phrase": phrase, "path": dest, "meaning": meaning})
        return out
    return []


def _alias_hits(root: Path, topic: str) -> list[dict]:
    """Match topic against alias phrases (substring, case-insensitive)."""
    topic_l = topic.lower()
    hits = []
    for a in _load_aliases(root):
        # Support "a / b" alternate phrases in the Phrase column
        phrases = [p.strip() for p in re.split(r"\s*/\s*", a["phrase"]) if p.strip()]
        matched = None
        for ph in phrases:
            if ph.lower() in topic_l or topic_l in ph.lower():
                matched = ph
                break
        if not matched:
            continue
        dest = a["path"].split()[0].rstrip(",")  # first path token if extras
        # Strip glob/parenthetical notes like `(e.g. …)`
        dest = dest.split("(")[0].strip()
        rel = dest.lstrip("./")
        full = root / rel
        exists = full.exists()
        hits.append({
            "path": rel if exists or "*" not in rel else rel,
            "kind": "alias",
            "as_of": "",
            "one_line": f"alias '{matched}' → {a['path']}: {a['meaning'][:120]}",
            "primary_sources": "",
            "source": "alias",
            "exists": exists,
        })
    return hits


def _tokens(topic: str) -> list[str]:
    return [t.lower() for t in re.split(r"[\s|,]+", topic) if len(t) >= 2]


def _guess_kind(path: str, text: str = "") -> str:
    blob = f"{path} {text}".lower()
    for kind, hints in KIND_HINTS:
        if any(h in blob for h in hints):
            return kind
    return "other"


def _as_of_from_path(path: str) -> str:
    m = DATE_RE.search(path)
    return m.group(1) if m else ""


def _first_heading(text: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("#"):
            return re.sub(r"^#+\s*", "", s)[:160]
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:160]
    return ""


def _age_days(as_of: str) -> int | None:
    if not as_of:
        return None
    try:
        d = date.fromisoformat(as_of[:10])
        return (date.today() - d).days
    except ValueError:
        return None


def _init_last_updated(root: Path, init_id: str) -> str:
    path = root / "registers" / "initiatives.csv"
    if not path.is_file() or not init_id:
        return ""
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("id") or "").strip().upper() == init_id.upper():
                return (row.get("last_updated") or "").strip()
    return ""


def _scan_files(root: Path, tokens: list[str], limit: int = 12) -> list[dict]:
    hits: list[dict] = []
    seen: set[str] = set()
    for rel_dir in SCAN_DIRS:
        base = root / rel_dir
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*"), key=lambda p: p.stat().st_mtime if p.is_file() else 0, reverse=True):
            if not path.is_file() or path.suffix.lower() not in {".md", ".csv", ".yml", ".yaml"}:
                continue
            rel = path.relative_to(root).as_posix()
            if rel in seen:
                continue
            name = path.name.lower()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:4000]
            except OSError:
                continue
            blob = f"{rel} {name} {text[:800]}".lower()
            if tokens and not any(t in blob for t in tokens):
                continue
            as_of = _as_of_from_path(rel) or date.fromtimestamp(path.stat().st_mtime).isoformat()
            derived = rel.startswith("drafts/")
            hits.append(
                {
                    "path": rel,
                    "as_of": as_of,
                    "one_line": _first_heading(text),
                    "age_days": _age_days(as_of),
                    "source": "scan",
                    "kind": _guess_kind(rel, text),
                    "primary_sources": "",
                    "derived": derived,
                }
            )
            seen.add(rel)
            if len(hits) >= limit:
                return hits
    return hits


def _index_hits(root: Path, tokens: list[str], init_id: str) -> list[dict]:
    out = []
    for r in analysis_index.read_rows(root):
        blob = " ".join(
            [
                r.get("topic_key", ""),
                r.get("initiative_ids", ""),
                r.get("kind", ""),
                r.get("path", ""),
                r.get("one_line", ""),
            ]
        ).lower()
        if init_id and init_id.lower() in blob:
            match = True
        elif tokens:
            match = any(t in blob for t in tokens)
        else:
            match = False
        if not match:
            continue
        as_of = r.get("as_of_date") or _as_of_from_path(r.get("path", ""))
        out.append(
            {
                "path": r.get("path", ""),
                "as_of": as_of,
                "one_line": r.get("one_line", ""),
                "age_days": _age_days(as_of),
                "source": "index",
                "kind": r.get("kind", "other"),
                "primary_sources": r.get("primary_sources", ""),
                "derived": (r.get("path") or "").startswith("drafts/"),
            }
        )
    return out


def _repo_map_rows(root: Path, tokens: list[str]) -> list[dict]:
    path = root / "reference" / "repo-map.md"
    profiles = root / "state" / "repo-profiles.json"
    rows: list[dict] = []
    if profiles.is_file():
        try:
            data = json.loads(profiles.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
        surfaces = data.get("surfaces") or {}
        for surface, candidates in surfaces.items():
            if tokens and not any(t in surface.lower() for t in tokens):
                # keep broad surfaces if topic empty-ish
                if len(tokens) > 2 and not any(t in surface.lower() for t in tokens[:3]):
                    continue
            if isinstance(candidates, list) and candidates:
                top = candidates[0]
                rows.append(
                    {
                        "surface": surface,
                        "repo": top.get("name"),
                        "role": top.get("role"),
                        "commit": top.get("commit"),
                        "as_of": top.get("commit_date"),
                    }
                )
        if rows:
            return rows[:12]
    if path.is_file():
        rows.append({"surface": "(see reference/repo-map.md)", "repo": "", "role": "map", "commit": "", "as_of": ""})
    return rows


def _recommendation(hits: list[dict], newer_signals: list[str]) -> str:
    if not hits:
        return "investigate"
    if newer_signals:
        return "reuse_and_refresh"
    return "reuse"


def _log_preflight(root: Path, topic: str, recommendation: str, hit_count: int, allow_repos: bool) -> None:
    log = root / "logs" / "context-preflight.csv"
    log.parent.mkdir(parents=True, exist_ok=True)
    new = not log.is_file()
    with log.open("a", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        if new:
            w.writerow(["timestamp", "topic", "recommendation", "hit_count", "allow_repos"])
        w.writerow(
            [
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                topic,
                recommendation,
                hit_count,
                "yes" if allow_repos else "no",
            ]
        )


def run_preflight(
    root: Path,
    topic: str,
    init_id: str = "",
    allow_repos: bool = False,
    verify: bool = False,
) -> dict:
    tokens = _tokens(topic)
    if init_id:
        tokens = list(dict.fromkeys(tokens + [init_id.lower()]))
    # pull INIT/COM from topic text
    for m in INIT_RE.findall(topic):
        init_id = init_id or m.upper()
        tokens.append(m.lower())
    for m in COM_RE.findall(topic):
        tokens.append(m.lower())

    alias_hits = _alias_hits(root, topic)
    index_hits = _index_hits(root, tokens, init_id)
    scan_hits = _scan_files(root, tokens)
    # merge: aliases first (name resolution), then index, then scan
    seen: set[str] = set()
    hits: list[dict] = []
    for h in alias_hits + index_hits + scan_hits:
        p = h.get("path") or ""
        if p and p not in seen:
            hits.append(h)
            seen.add(p)

    newer_signals: list[str] = []
    if verify:
        newer_signals.append("PM asked verify")
    init_lu = _init_last_updated(root, init_id)
    if init_lu and hits:
        for h in hits:
            as_of = h.get("as_of") or ""
            if as_of and init_lu[:10] > as_of[:10]:
                newer_signals.append(f"INIT {init_id} last_updated {init_lu} after analysis {as_of}")
                break
    # newer scan file same kind
    by_kind: dict[str, list] = {}
    for h in hits:
        by_kind.setdefault(h.get("kind") or "other", []).append(h)
    for kind, group in by_kind.items():
        dated = sorted(
            [g for g in group if g.get("as_of")],
            key=lambda x: x["as_of"],
            reverse=True,
        )
        if len(dated) >= 2 and dated[0]["as_of"] > dated[-1]["as_of"]:
            if dated[0]["source"] == "scan" and dated[-1]["source"] == "index":
                newer_signals.append(f"newer {kind} digest {dated[0]['path']} vs indexed {dated[-1]['path']}")

    recommendation = _recommendation(hits, newer_signals)
    # allow_repos: empty cache, refresh, or explicit flag
    if allow_repos or recommendation in ("investigate", "reuse_and_refresh"):
        allow = True
    else:
        allow = False

    repo_rows = _repo_map_rows(root, tokens)
    # refresh repo profiles if script present and HEAD drifted
    try:
        import repo_profile  # noqa: WPS433

        repo_profile.ensure_profiles(root)
        repo_rows = _repo_map_rows(root, tokens)
    except Exception:
        pass

    marker = {
        "topic": topic,
        "init": init_id,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "keywords": tokens,
        "hits": hits,
        "newer_signals": newer_signals,
        "recommendation": recommendation,
        "allow_repos": allow,
        "repo_map": repo_rows,
    }
    state = root / "state"
    state.mkdir(parents=True, exist_ok=True)
    (state / ".context-preflight.json").write_text(json.dumps(marker, indent=2) + "\n", encoding="utf-8")
    _log_preflight(root, topic, recommendation, len(hits), allow)
    return marker


def backfill_scan(root: Path) -> int:
    n = 0
    for rel_dir in SCAN_DIRS:
        base = root / rel_dir
        if not base.is_dir():
            continue
        for path in base.rglob("*.md"):
            if not path.is_file():
                continue
            rel = path.relative_to(root).as_posix()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:3000]
            except OSError:
                continue
            as_of = _as_of_from_path(rel) or date.fromtimestamp(path.stat().st_mtime).isoformat()
            kind = _guess_kind(rel, text)
            topic_key = "|".join(
                sorted(
                    {
                        t
                        for t in re.split(r"[^\w-]+", Path(rel).stem.lower())
                        if len(t) > 2 and t not in {"the", "and", "for", "with"}
                    }
                )[:8]
            )
            inits = ";".join(sorted(set(INIT_RE.findall(text)))[:5])
            if analysis_index.append_row(
                root,
                topic_key=topic_key or kind,
                path=rel,
                kind=kind,
                as_of_date=as_of,
                one_line=_first_heading(text),
                primary_sources="",
                initiative_ids=inits,
                source_workflow="backfill-scan",
            ):
                n += 1
                print(f"+ {rel}")
    print(f"backfill_appended={n}")
    return n


def print_marker(marker: dict) -> None:
    print(f"topic={marker.get('topic')}")
    print(f"recommendation={marker.get('recommendation')}")
    print(f"allow_repos={'yes' if marker.get('allow_repos') else 'no'}")
    hits = marker.get("hits") or []
    print(f"hits={len(hits)}")
    for h in hits:
        prim = h.get("primary_sources") or "(none recorded)"
        derived = " derived" if h.get("derived") else ""
        print(
            f"  [{h.get('source')}]{derived} {h.get('path')} | as_of={h.get('as_of')} "
            f"| age_days={h.get('age_days')} | {h.get('one_line')}"
        )
        print(f"    primary_sources: {prim}")
    for s in marker.get("newer_signals") or []:
        print(f"newer_signal: {s}")
    for r in marker.get("repo_map") or []:
        print(
            f"repo_map: surface={r.get('surface')} repo={r.get('repo')} "
            f"role={r.get('role')} commit={r.get('commit')} as_of={r.get('as_of')}"
        )
    print("PREFLIGHT_OK" if hits else "PREFLIGHT_EMPTY")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--topic", default="")
    p.add_argument("--init", default="")
    p.add_argument("--allow-repos", action="store_true")
    p.add_argument("--verify", action="store_true", help="PM asked to verify against newer sources")
    p.add_argument("--backfill-scan", action="store_true")
    args = p.parse_args(argv)

    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2

    analysis_index.ensure_index(root)

    if args.backfill_scan:
        backfill_scan(root)
        if not args.topic:
            return 0

    if not args.topic:
        print("ERROR: --topic required (or use --backfill-scan alone)", file=sys.stderr)
        return 2

    marker = run_preflight(
        root,
        args.topic,
        init_id=args.init,
        allow_repos=args.allow_repos,
        verify=args.verify,
    )
    print_marker(marker)
    return 0


if __name__ == "__main__":
    sys.exit(main())
