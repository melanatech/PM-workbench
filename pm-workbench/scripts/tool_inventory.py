#!/usr/bin/env python3
"""Print tool and plugin names only. Never print values or tokens."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def names_from_json(path: Path, keys: tuple[str, ...]) -> list[str]:
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return [f"{path.name}: unreadable"]
    found: list[str] = []
    if isinstance(data, dict):
        for key in keys:
            block = data.get(key)
            if isinstance(block, dict):
                found.extend(sorted(str(k) for k in block))
            elif isinstance(block, list):
                for item in block:
                    if isinstance(item, str):
                        found.append(item)
                    elif isinstance(item, dict) and "name" in item:
                        found.append(str(item["name"]))
        if not found:
            found.extend(sorted(str(k) for k in data if k not in ("env", "headers", "token")))
    return found


def skill_names(root: Path) -> list[str]:
    skills = root / ".claude" / "skills"
    if not skills.is_dir():
        return []
    return sorted(p.name for p in skills.iterdir() if (p / "SKILL.md").is_file())


def toml_server_names(path: Path) -> list[str]:
    if not path.is_file():
        return []
    names = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if line.startswith("[mcp_servers.") or line.startswith("[mcp.servers."):
            names.append(line.split(".", 1)[-1].rstrip("]").strip("\"'"))
    return names


def main() -> int:
    root = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else Path.cwd()
    home = Path.home()
    sections = {
        "claude settings plugin keys": names_from_json(home / ".claude" / "settings.json", ("enabledPlugins", "plugins")),
        "installed plugins file keys": names_from_json(
            home / ".claude" / "plugins" / "installed_plugins.json", ("plugins",)
        ),
        "workspace mcp servers": names_from_json(root / ".mcp.json", ("mcpServers",)),
        "codex mcp servers": toml_server_names(root / ".codex" / "config.toml"),
        "cursor hook names": names_from_json(root / ".cursor" / "hooks.json", ("hooks",)),
        "workspace skills": skill_names(root),
    }
    for title, items in sections.items():
        print(f"## {title}")
        if not items:
            print("(none found)")
        else:
            for item in items:
                print(f"- {item}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
