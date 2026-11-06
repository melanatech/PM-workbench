#!/usr/bin/env python3
"""preToolUse: prepend the workbench dispatch block to every Task (subagent) prompt.

Cursor's Task tool runs its own preToolUse with tool_input
{description, prompt, subagent_type, run_in_background, resume, ...} and merges
`updated_input` into those arguments. Other tools pass through untouched.
A CallDynamicTool wrapper around Task is logged only: rewriting the wrapper's
arguments can be rejected ("hook argument rewrite is not allowed"), and the
inner Task preToolUse still fires.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import (  # noqa: E402
    DEFAULT_ROOT,
    emit,
    load_identity,
    log_decision,
    project_root,
    read_stdin_json,
)

MARKER = "[WORKBENCH DISPATCH BLOCK"
# Coordinators can reference the rendered block instead of pasting it.
DISPATCH_BLOCK_REF = ".cursor/hooks/dispatch-block.md"

FALLBACK_HEADER = (
    "> Edit `<path>` in place. Keep its design, CSS, markup structure, layout, components, "
    "and copy voice; change only the content asked for. A new design, template, or rebuild "
    "needs the PM's explicit ask; if the structure cannot hold the new content, stop and "
    "return the question. For HTML, run `python3 scripts/check_design_preserved.py <path> "
    "--git HEAD` (or `--before <old copy>`) before saving over, committing, or pushing; a "
    "FAIL means restore the previous design."
)
FALLBACK_NUMBER = (
    "Number-consistency gate (every mode, including Fast — not skippable): any external "
    "artifact that carries numbers needs `<artifact-stem>-number-ledger.md` and must pass "
    "`python3 scripts/check_number_consistency.py --ledger <ledger.md> <artifact>` before "
    "it is called ready."
)


def dispatch_header(root: Path) -> str:
    try:
        text = (root / "AGENTS.md").read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_HEADER
    m = re.search(r"## Dispatch header.*?\n((?:>.*\n?)+)", text, re.S)
    return m.group(1).strip() if m else FALLBACK_HEADER


def number_line(root: Path) -> str:
    try:
        text = (root / ".claude" / "workflows" / "_protocol.md").read_text(encoding="utf-8")
    except OSError:
        return FALLBACK_NUMBER
    for line in text.splitlines():
        if "**Number-consistency gate" in line:
            return re.sub(r"^\s*\d+\.\s*", "", line).strip()
    return FALLBACK_NUMBER


def workflow_line(root: Path, prompt: str) -> str:
    wf_dir = root / ".claude" / "workflows"
    names = sorted(
        (p.stem for p in wf_dir.glob("*.md") if not p.stem.startswith("_")),
        key=len,
        reverse=True,
    ) if wf_dir.is_dir() else []
    hits = [n for n in names if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", prompt)]
    if hits:
        paths = ", ".join(f"`.claude/workflows/{n}.md`" for n in hits[:3])
        return (
            f"Workflow: this task names {paths}. Read that workflow file and "
            "`.claude/workflows/_operator-rules.md` in full before acting, and follow its steps. "
            "Do not invent a lighter path."
        )
    return (
        "Workflow: if this task matches a workbench workflow (menu: "
        "`.claude/workflows/_plain-language.md`; files: `.claude/workflows/<name>.md`), read "
        "that workflow file and `.claude/workflows/_operator-rules.md` before acting, and "
        "follow its steps. Do not invent a lighter path."
    )


PM_BRAIN = "reference/context/pm-brain.md"
MAX_RULES_CHARS = 9000


def read_standing_rules(root: Path) -> tuple[str, str]:
    """The PM's saved rules, read from the file now. Returns (text, version)."""
    try:
        text = (root / PM_BRAIN).read_text(encoding="utf-8").strip()
    except OSError:
        return "", ""
    if not text:
        return "", ""
    return text[:MAX_RULES_CHARS], hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def standing_rules_lines(root: Path, embed: bool) -> list[str]:
    conflict = (
        "If the task brief conflicts with one of these rules, do not choose silently: "
        "follow the rule and name the conflict in your result."
    )
    text, version = read_standing_rules(root)
    if not text:
        return []
    if embed:
        return [
            f"Standing rules ({PM_BRAIN}, read at dispatch, version {version}). These are the PM's "
            "saved rules. Apply each one that governs the file you write or the text you draft. "
            + conflict,
            text,
            "",
        ]
    return [
        f"Standing rules: read `{PM_BRAIN}` in full before you write anything, and apply each rule "
        "that governs the file you write or the text you draft. " + conflict,
        "",
    ]


def build_block(root: Path, prompt: str, embed: bool = True) -> str:
    ident = load_identity(root)
    if ident.get("name") and ident.get("email"):
        account = f"; Jira accountId {ident['jira_account_id']}" if ident.get("jira_account_id") else ""
        pm = f"PM: {ident['name']} ({ident['email']}{account})."
        pm_first = ident["name"].split()[0]
    else:
        pm = "PM: [NEEDS INPUT: PM name/email]."
        pm_first = "the PM"
    examples = [e for e in (ident.get("username_examples") or []) if isinstance(e, str) and e]
    example_text = (
        " or ".join(f"`{e}`" for e in examples[:3]) if examples else "your OS username or a cloud account name"
    )
    return "\n".join(
        [
            f"{MARKER} — injected by .cursor/hooks/dispatch_inject.py]",
            f"{pm} \"The PM\", \"me\", and \"my\" in this task mean {pm_first}. Never infer a "
            f"person's name from a username, file path, or account name (for example {example_text}). "
            "Any other person you name must come from a source you cite.",
            "",
            workflow_line(root, prompt),
            "",
            *standing_rules_lines(root, embed),
            "Dispatch header (AGENTS.md) — applies whenever you add to, update, or extend an existing file:",
            dispatch_header(root),
            "",
            "Number gate (_protocol.md Publish step 2): " + number_line(root),
            "",
            "Verification rule: never invent a person, owner, assignee, date, metric, status, or "
            "decision. Any claim that something is absent or stale (\"no ticket\", \"no PRD\", \"no "
            "epic\", \"empty description\", \"stale\", \"needs a PRD\") and any claim that names a "
            "person or assignee (\"assigned to X\", \"owner: X\") must appear in a `## Claim table` "
            "in your final message with columns | Claim | Source | Checked how |. A source is a "
            "Jira key plus the JQL or issue fetch you ran, a Confluence page id plus version, or "
            "file:line. Check an absence claim against the artifact's own links and Sources "
            "section, not one search. If you cannot source a claim, remove it or write "
            "`unverified` as its source. A subagentStop hook sends your result back if these "
            "claims appear without that table.",
            "[END WORKBENCH DISPATCH BLOCK]",
            "",
        ]
    )


def main() -> int:
    if "--write-block" in sys.argv:
        out = DEFAULT_ROOT / DISPATCH_BLOCK_REF
        out.write_text(build_block(DEFAULT_ROOT, "", embed=False), encoding="utf-8")
        print(f"wrote {out}")
        return 0
    payload = read_stdin_json()
    root = project_root(payload)
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if (root / "state" / "hooks" / ".debug-pretooluse").exists():
        log_decision(root, {"hook": "preToolUse", "decision": "debug", "tool_name": tool_name,
                            "payload_keys": sorted(payload.keys()),
                            "tool_input_keys": sorted(tool_input.keys()) if isinstance(tool_input, dict) else str(type(tool_input))})
    if not isinstance(tool_input, dict):
        emit({})
        return 0

    is_task = tool_name.lower() in {"task", "subagent"} or (
        "prompt" in tool_input and "subagent_type" in tool_input
    )
    is_dynamic_task = (
        tool_name == "CallDynamicTool"
        and str(tool_input.get("toolName", "")).lower() == "task"
    )

    if is_dynamic_task:
        log_decision(
            root,
            {
                "hook": "preToolUse",
                "decision": "log",
                "reason": "CallDynamicTool(Task) wrapper; inner Task preToolUse injects",
                "tool_name": tool_name,
                "payload_keys": sorted(payload.keys()),
                "conversation_id": payload.get("conversation_id"),
                "parent_tool_call_id": payload.get("parent_tool_call_id"),
            },
        )
        emit({})
        return 0

    if not is_task:
        emit({})
        return 0

    prompt = tool_input.get("prompt") or ""
    base = {
        "hook": "preToolUse",
        "tool_name": tool_name,
        "payload_keys": sorted(payload.keys()),
        "tool_input_keys": sorted(tool_input.keys()),
        "conversation_id": payload.get("conversation_id"),
        "parent_tool_call_id": payload.get("parent_tool_call_id"),
        "resume": bool(tool_input.get("resume")),
    }
    if MARKER in prompt:
        log_decision(root, {**base, "decision": "allow", "reason": "block already present"})
        emit({"permission": "allow"})
        return 0

    block = build_block(root, prompt)
    log_decision(
        root,
        {
            **base,
            "decision": "inject",
            "block_chars": len(block),
            "standing_rules_version": read_standing_rules(root)[1],
            "needs_input": "[NEEDS INPUT" in block,
            "prompt_preview": prompt[:160],
        },
    )
    emit({"permission": "allow", "updated_input": {"prompt": block + "\n" + prompt}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
