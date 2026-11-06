"""A worker started by Claude Code is given the PM's saved rules, read at dispatch."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
HOOK = KIT / ".claude" / "hooks" / "inject_standing_rules.py"
PROFILES = ("settings.json", "settings.core.json", "settings.full.json")


class StandingRulesHook(unittest.TestCase):
    def run_hook(self, root, tool_input, tool="Task"):
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(root)}
        p = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps({"tool_name": tool, "tool_input": tool_input}),
            capture_output=True, text=True, env=env,
        )
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout) if p.stdout.strip() else {}

    def brain(self, root, text):
        path = Path(root) / "reference" / "context" / "pm-brain.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_rule_reaches_the_worker_and_the_original_prompt_survives(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.brain(tmp, "- Status is blockers only.\n")
            tool_input = {"prompt": "Write the cards.", "subagent_type": "general-purpose", "description": "cards"}
            out = self.run_hook(tmp, tool_input)
            updated = out["hookSpecificOutput"]["updatedInput"]
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "allow")
            self.assertIn("Status is blockers only.", updated["prompt"])
            self.assertTrue(updated["prompt"].endswith("Write the cards."))
            self.assertEqual(updated["subagent_type"], "general-purpose")

    def test_a_rule_saved_later_is_picked_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.brain(tmp, "- First rule.\n")
            self.run_hook(tmp, {"prompt": "x"})
            self.brain(tmp, "- First rule.\n- Second rule.\n")
            out = self.run_hook(tmp, {"prompt": "x"})
            self.assertIn("Second rule.", out["hookSpecificOutput"]["updatedInput"]["prompt"])

    def test_dispatch_is_logged_with_the_rules_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.brain(tmp, "- A rule.\n")
            self.run_hook(tmp, {"prompt": "x", "subagent_type": "general-purpose"})
            rows = [json.loads(l) for l in (Path(tmp) / "state" / "hooks" / "hook-log.jsonl").read_text().splitlines()]
            self.assertEqual(rows[-1]["decision"], "injected")
            self.assertEqual(len(rows[-1]["standing_rules_version"]), 12)

    def test_prompt_with_the_block_is_not_doubled(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.brain(tmp, "- A rule.\n")
            first = self.run_hook(tmp, {"prompt": "x"})["hookSpecificOutput"]["updatedInput"]
            self.assertEqual(self.run_hook(tmp, first), {})

    def test_no_rules_file_allows_the_dispatch_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.run_hook(tmp, {"prompt": "x"}), {})

    def test_every_profile_wires_the_hook_to_the_worker_tool(self):
        for name in PROFILES:
            settings = json.loads((KIT / ".claude" / name).read_text(encoding="utf-8"))
            blocks = [b for b in settings["hooks"]["PreToolUse"] if "Task" in b.get("matcher", "")]
            self.assertTrue(blocks, name)
            commands = " ".join(h["command"] for b in blocks for h in b["hooks"])
            self.assertIn("inject_standing_rules.py", commands, name)


if __name__ == "__main__":
    unittest.main()
