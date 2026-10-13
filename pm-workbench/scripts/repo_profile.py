#!/usr/bin/env python3
"""Profile repos/ for surface coverage, role (product vs mock), and freshness.

Usage:
  python3 scripts/repo_profile.py --root ~/pm-live
  python3 scripts/repo_profile.py --root ~/pm-live --force

Writes state/repo-profiles.json and reference/repo-map.md.
Heuristics are org-agnostic (no company names). Classification changes are
listed as NEEDS_CONFIRM for the PM.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

PATH_RE = re.compile(
    r"""path\s*[=:]\s*['"]([^'"]+)['"]|path:\s*['"]([^'"]+)['"]""",
    re.I,
)
TICKET_COMMIT_RE = re.compile(r"\b[A-Z]{2,10}-\d{2,6}\b")
SCOPED_PKG_RE = re.compile(r'"name"\s*:\s*"(@[^/"]+/[^"]+)"')


def _git(root: Path, *args: str) -> str:
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), *args],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return ""


def _collect_routes(repo: Path) -> list[str]:
    routes: set[str] = set()
    patterns = ("*.js", "*.jsx", "*.ts", "*.tsx", "*.mjs", "*.cjs")
    candidates = []
    for name in (
        "nav-config.js",
        "nav-config.ts",
        "App.js",
        "App.tsx",
        "routes.js",
        "routes.tsx",
        "index.js",
        "index.jsx",
        "index.ts",
        "index.tsx",
        "Routes.js",
        "Routes.tsx",
    ):
        p = repo / "src" / name
        if p.is_file():
            candidates.append(p)
    for pat in patterns:
        for p in list((repo / "src").rglob(pat))[:400] if (repo / "src").is_dir() else []:
            low = p.as_posix().lower()
            if any(x in low for x in ("route", "nav", "router", "pages", "/index.")):
                candidates.append(p)
    seen_files: set[Path] = set()
    for p in candidates:
        if p in seen_files or not p.is_file():
            continue
        seen_files.add(p)
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in PATH_RE.finditer(text):
            route = m.group(1) or m.group(2)
            if route and route.startswith("/") and "*" not in route:
                routes.add(route.rstrip("/") or "/")
    # pages directory names as soft surfaces
    pages = repo / "src" / "pages"
    if pages.is_dir():
        for child in pages.iterdir():
            stem = child.stem if child.is_file() else child.name
            if stem and not stem.startswith(".") and stem[0].isupper():
                slug = re.sub(r"([a-z])([A-Z])", r"\1-\2", stem).lower()
                routes.add("/" + slug.replace("_", "-"))
    return sorted(routes)


def _is_runnable(repo: Path) -> bool:
    npmrc = repo / ".npmrc"
    if npmrc.is_file():
        text = npmrc.read_text(encoding="utf-8", errors="replace").lower()
        if "registry=" in text and any(
            x in text for x in ("artifactory", "npm.pkg.github.com", "pkgs.", "nexus", "verdaccio")
        ):
            return False
        if "@" in text and "registry=" in text:
            return False
    pkg = repo / "package.json"
    if pkg.is_file():
        text = pkg.read_text(encoding="utf-8", errors="replace")
        # private scoped deps often need registry
        if re.search(r'"@[^/"]+/[^"]+"\s*:', text) and "file:" not in text[:500]:
            # heuristic: many scoped deps → likely private
            scoped = len(re.findall(r'"@[^/"]+/[^"]+"\s*:', text))
            if scoped >= 3:
                return False
    return (repo / "package.json").is_file()


def _classify(repo: Path, package_name: str, routes: list[str], commit_msgs: str) -> tuple[str, list[str]]:
    signals: list[str] = []
    role = "other"
    readme = ""
    for name in ("README.md", "readme.md", "CLAUDE.md"):
        p = repo / name
        if p.is_file():
            readme += p.read_text(encoding="utf-8", errors="replace")[:3000].lower()
    pages = list((repo / "src" / "pages").rglob("*")) if (repo / "src" / "pages").is_dir() else []
    docsish = sum(
        1
        for p in pages
        if any(x in p.name.lower() for x in ("docs", "design", "sandbox", "vision", "mock"))
    )
    versioned = sum(1 for p in pages if re.search(r"v\d+", p.name, re.I))

    mock_score = 0
    product_score = 0
    if any(w in readme for w in ("mock", "replica", "prototype demo", "not production", "demo only")):
        mock_score += 2
        signals.append("readme_mock_language")
    if docsish >= 3:
        mock_score += 2
        signals.append(f"docs_pages={docsish}")
    if versioned >= 2:
        mock_score += 1
        signals.append(f"versioned_pages={versioned}")
    if len(routes) >= 15:
        mock_score += 1
        signals.append(f"broad_routes={len(routes)}")

    if package_name.startswith("@"):
        product_score += 2
        signals.append("scoped_package")
    tickets = len(TICKET_COMMIT_RE.findall(commit_msgs))
    if tickets >= 2:
        product_score += 2
        signals.append(f"ticket_commits={tickets}")
    if (repo / ".github").is_dir() or (repo / ".circleci").is_dir():
        product_score += 1
        signals.append("ci_config")
    tests = list(repo.rglob("*.test.*"))[:20] + list(repo.rglob("*.spec.*"))[:20]
    if len(tests) >= 3:
        product_score += 1
        signals.append(f"tests={len(tests)}")
    if len(routes) <= 25 and product_score >= 2:
        product_score += 1
        signals.append("narrow_surface")

    if product_score > mock_score and product_score >= 2:
        role = "product"
    elif mock_score > product_score and mock_score >= 2:
        role = "mock"
    elif mock_score == product_score and mock_score >= 2:
        role = "mock" if mock_score >= product_score else "product"
        signals.append("tie_broken")
    return role, signals


def profile_repo(repo: Path) -> dict:
    name = repo.name
    commit = _git(repo, "rev-parse", "--short", "HEAD")
    commit_date = _git(repo, "log", "-1", "--format=%ci")[:10]
    commit_msgs = _git(repo, "log", "-15", "--format=%s")
    package_name = ""
    pkg = repo / "package.json"
    if pkg.is_file():
        m = SCOPED_PKG_RE.search(pkg.read_text(encoding="utf-8", errors="replace"))
        if m:
            package_name = m.group(1)
        else:
            try:
                data = json.loads(pkg.read_text(encoding="utf-8"))
                package_name = data.get("name") or ""
            except json.JSONDecodeError:
                pass
    routes = _collect_routes(repo)
    role, signals = _classify(repo, package_name, routes, commit_msgs)
    runnable = _is_runnable(repo)
    return {
        "name": name,
        "path": str(repo.resolve()),
        "package": package_name,
        "commit": commit,
        "commit_date": commit_date,
        "role": role,
        "runnable": runnable,
        "routes": routes,
        "signals": signals,
        "profiled_date": date.today().isoformat(),
        "confirmed": False,
    }


def build_surfaces(profiles: list[dict]) -> dict[str, list[dict]]:
    surfaces: dict[str, list[dict]] = {}
    role_rank = {"product": 0, "mock": 1, "other": 2}
    for prof in profiles:
        for route in prof.get("routes") or []:
            surfaces.setdefault(route, []).append(
                {
                    "name": prof["name"],
                    "role": prof["role"],
                    "commit": prof.get("commit"),
                    "commit_date": prof.get("commit_date"),
                    "runnable": prof.get("runnable"),
                }
            )
    for route, cands in surfaces.items():
        cands.sort(
            key=lambda c: (
                role_rank.get(c.get("role") or "other", 9),
                # newer first: invert date string by sorting reverse
                "0000" if not c.get("commit_date") else c["commit_date"],
            ),
            reverse=False,
        )
        # product first: sort by role_rank ascending, then commit_date descending
        cands.sort(
            key=lambda c: (
                role_rank.get(c.get("role") or "other", 9),
                -(int((c.get("commit_date") or "1970-01-01").replace("-", "")[:8]) if c.get("commit_date") else 0),
            )
        )
        surfaces[route] = cands
    return surfaces


def write_repo_map(root: Path, profiles: list[dict], surfaces: dict[str, list[dict]], needs_confirm: list[str]) -> None:
    lines = [
        "# Repo map (generated)",
        "",
        f"Generated {date.today().isoformat()} by `scripts/repo_profile.py`. "
        "Product repos beat mocks on overlapping surfaces; fresher commit wins ties within a role.",
        "",
        "## Repos",
        "",
        "| Repo | Role | Commit | Date | Runnable | Routes |",
        "|---|---|---|---|---|---|",
    ]
    for p in profiles:
        lines.append(
            f"| {p['name']} | {p['role']} | `{p.get('commit') or ''}` | {p.get('commit_date') or ''} | "
            f"{'yes' if p.get('runnable') else 'no'} | {len(p.get('routes') or [])} |"
        )
    lines += ["", "## Surfaces (top source)", "", "| Surface | Top source | Role | As-of |", "|---|---|---|---|"]
    for surface in sorted(surfaces.keys()):
        top = surfaces[surface][0]
        lines.append(
            f"| `{surface}` | {top['name']} | {top['role']} | {top.get('commit_date') or ''} |"
        )
    if needs_confirm:
        lines += ["", "## NEEDS_CONFIRM", ""]
        for msg in needs_confirm:
            lines.append(f"- {msg}")
    out = root / "reference" / "repo-map.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")


def ensure_profiles(root: Path, force: bool = False) -> dict:
    repos_dir = root / "repos"
    state_path = root / "state" / "repo-profiles.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    prev = {}
    if state_path.is_file():
        try:
            prev = json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}
    prev_by_name = {p["name"]: p for p in prev.get("repos") or []}

    profiles = []
    needs_confirm = []
    if repos_dir.is_dir():
        for child in sorted(repos_dir.iterdir()):
            if child.name.startswith("."):
                continue
            target = child.resolve() if child.is_symlink() or child.is_dir() else None
            if not target or not target.is_dir():
                continue
            # skip if HEAD unchanged
            commit = _git(target, "rev-parse", "--short", "HEAD")
            old = prev_by_name.get(child.name)
            if not force and old and old.get("commit") == commit and old.get("role"):
                profiles.append(old)
                continue
            prof = profile_repo(target)
            # preserve confirmation
            if old and old.get("confirmed") and old.get("role") == prof["role"]:
                prof["confirmed"] = True
            elif not old or old.get("role") != prof["role"]:
                needs_confirm.append(
                    f"{prof['name']} looks like **{prof['role']}** "
                    f"(signals: {', '.join(prof.get('signals') or [])}). Confirm and record in links.csv notes."
                )
            profiles.append(prof)

    surfaces = build_surfaces(profiles)
    data = {
        "generated": date.today().isoformat(),
        "repos": profiles,
        "surfaces": surfaces,
        "needs_confirm": needs_confirm,
    }
    state_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    write_repo_map(root, profiles, surfaces, needs_confirm)
    return data


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)
    root = Path(os.path.expanduser(args.root)).resolve()
    if not root.is_dir():
        print(f"ERROR: root not found: {root}", file=sys.stderr)
        return 2
    data = ensure_profiles(root, force=args.force)
    print(f"repos_profiled={len(data.get('repos') or [])}")
    print(f"surfaces={len(data.get('surfaces') or {})}")
    for msg in data.get("needs_confirm") or []:
        print(f"NEEDS_CONFIRM: {msg}")
    print(f"wrote state/repo-profiles.json and reference/repo-map.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
