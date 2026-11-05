#!/usr/bin/env python3
"""Install session memory at user level for Claude Code (Plan E Part 2). Standard library only.

  python3 session-memory/install.py --dry-run     # print every change; write nothing
  python3 session-memory/install.py               # back up ~/.claude/settings.json, then install
  python3 session-memory/install.py --uninstall   # remove exactly what install added

Adds four hooks to ~/.claude/settings.json (Stop, SessionStart, UserPromptSubmit, PostToolUse on reads),
the session-reader agent, the /pickup command, and a marked block in ~/.claude/CLAUDE.md. Re-running is
idempotent. Every hook exits 0 on a Cursor Agent payload, so this does nothing in Cursor chats until the
PM decides otherwise. Weekly review and the autocompact threshold are not scheduled or set here.
"""
import argparse
import datetime
import json
import os
import shutil
import sys

MODULE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.join(MODULE, "hooks")
MARK = "/session-memory/hooks/"
BEGIN, END = "<!-- BEGIN SESSION MEMORY -->", "<!-- END SESSION MEMORY -->"
CLAUDE_BLOCK = f"""{BEGIN}
## Session memory

Session registers live in `~/.claude/session-memory/<project>/<session>.jsonl` (per-session working context: goal, where it stands, decisions, constraints, corrections, don't-retry, open questions). Check them when asked what was decided in a session. Follow its Constraints, Corrections and Don't retry entries, and flag in one line any conflict between an entry and what the user just said; the newer statement wins. A project's own durable memory (for example `reference/context/pm-brain.md` with its CLAUDE.md rule) stays the record for durable facts: when a session entry states one, save it the way that project's rule says. Session memory never edits project files.
{END}
"""


def hook_entries():
    py = sys.executable or "/usr/bin/python3"

    def cmd(name):
        return {"type": "command", "command": f"'{py}' '{os.path.join(HOOKS, name)}'", "timeout": 30}
    return {
        "Stop": [{"matcher": "", "hooks": [cmd("keeper.py")]}],
        "SessionStart": [{"matcher": "", "hooks": [cmd("restore.py")]}],
        "UserPromptSubmit": [{"matcher": "", "hooks": [cmd("prompt.py")]}],
        "PostToolUse": [{"matcher": "Read|Grep|Glob|WebFetch|WebSearch|Skill", "hooks": [cmd("reading.py")]}],
    }


def strip_ours(settings):
    hooks = settings.get("hooks") or {}
    for event in list(hooks):
        kept = []
        for group in hooks[event]:
            inner = [h for h in group.get("hooks", []) if MARK not in str(h.get("command", ""))]
            if inner:
                kept.append({**group, "hooks": inner})
        if kept:
            hooks[event] = kept
        else:
            del hooks[event]
    if hooks:
        settings["hooks"] = hooks
    else:
        settings.pop("hooks", None)
    return settings


def add_ours(settings):
    settings = strip_ours(settings)
    hooks = settings.setdefault("hooks", {})
    for event, groups in hook_entries().items():
        hooks.setdefault(event, []).extend(groups)
    return settings


def claude_md(text, install):
    if BEGIN in text:
        text = text[:text.index(BEGIN)].rstrip("\n") + "\n" + text[text.index(END) + len(END):].lstrip("\n")
        text = text if text.strip() else ""
    if install:
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + CLAUDE_BLOCK
    return text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--home", default=os.path.expanduser("~"), help="for tests")
    args = parser.parse_args(argv)
    claude = os.path.join(args.home, ".claude")
    settings_path = os.path.join(claude, "settings.json")
    try:
        settings = json.load(open(settings_path, encoding="utf-8"))
    except FileNotFoundError:
        settings = {}
    new_settings = strip_ours(json.loads(json.dumps(settings))) if args.uninstall else add_ours(json.loads(json.dumps(settings)))
    md_path = os.path.join(claude, "CLAUDE.md")
    md_old = open(md_path, encoding="utf-8").read() if os.path.exists(md_path) else ""
    md_new = claude_md(md_old, not args.uninstall)
    agent_dest = os.path.join(claude, "agents", "session-reader.md")
    command_dest = os.path.join(claude, "commands", "pickup.md")
    command_text = open(os.path.join(MODULE, "commands", "pickup.md"), encoding="utf-8").read().replace(
        "SESSION_MEMORY_DIR", MODULE)

    if args.dry_run:
        print(f"# {settings_path} (hooks after {'uninstall' if args.uninstall else 'install'})")
        print(json.dumps(new_settings.get("hooks", {}), indent=2))
        print(f"# {md_path}: {'remove' if args.uninstall else 'add'} the session-memory block")
        print(f"# {agent_dest}: {'remove' if args.uninstall else 'write'}")
        print(f"# {command_dest}: {'remove' if args.uninstall else 'write'}")
        return 0

    os.makedirs(claude, exist_ok=True)
    if os.path.exists(settings_path):
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = f"{settings_path}.session-memory-backup-{stamp}"
        shutil.copy2(settings_path, backup)
        print(f"backup: {backup}")
    with open(settings_path, "w", encoding="utf-8") as handle:
        json.dump(new_settings, handle, indent=2)
        handle.write("\n")
    if md_new != md_old:
        with open(md_path, "w", encoding="utf-8") as handle:
            handle.write(md_new)
    if args.uninstall:
        for path in (agent_dest, command_dest):
            if os.path.exists(path):
                os.remove(path)
        print("session memory uninstalled (registers under ~/.claude/session-memory/ are kept)")
        return 0
    os.makedirs(os.path.dirname(agent_dest), exist_ok=True)
    shutil.copy2(os.path.join(MODULE, "agents", "session-reader.md"), agent_dest)
    os.makedirs(os.path.dirname(command_dest), exist_ok=True)
    with open(command_dest, "w", encoding="utf-8") as handle:
        handle.write(command_text)
    print("session memory installed: 4 hooks, session-reader agent, /pickup, CLAUDE.md block")
    return 0


if __name__ == "__main__":
    sys.exit(main())
