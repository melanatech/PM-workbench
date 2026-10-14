"""CLAUDE.md stays a short index. Moved rules keep their numbers at the new home."""
import re
import unittest
from pathlib import Path


WORKBENCH = Path(__file__).resolve().parents[1]
CLAUDE = WORKBENCH / "CLAUDE.md"
MAX_LINES = 120

# rule number → (path relative to the kit, anchor that must appear there)
MOVED = {
    5: (".claude/workflows/okr-refresh.md", "Rule 5"),
    18: (".claude/workflows/_protocol.md", "Rule 18"),
    19: (".claude/workflows/_protocol.md", "Rule 19"),
    20: (".claude/workflows/_protocol.md", "Rule 20"),
    23: (".claude/workflows/_protocol.md", "Rule 23"),
    24: (".claude/workflows/_protocol.md", "Rule 24"),
    25: (".claude/skills/authority-lookup/SKILL.md", "Rule 25"),
    26: (".claude/skills/authority-lookup/SKILL.md", "Rule 26"),
}


class ClaudeMdBudgetTests(unittest.TestCase):
    def test_line_budget(self):
        lines = CLAUDE.read_text(encoding="utf-8").splitlines()
        self.assertLessEqual(
            len(lines),
            MAX_LINES,
            f"CLAUDE.md is {len(lines)} lines; budget is {MAX_LINES}",
        )
        self.assertGreaterEqual(len(lines), 40, "CLAUDE.md lost the standing rules")

    def test_rule_numbers_stay_in_claude_md(self):
        text = CLAUDE.read_text(encoding="utf-8")
        numbered = {int(n) for n in re.findall(r"(?m)^(\d+)\. ", text)}
        self.assertEqual(numbered, set(range(1, 27)))

    def test_moved_rules_keep_their_number_at_the_new_home(self):
        claude = CLAUDE.read_text(encoding="utf-8")
        for number, (rel, anchor) in MOVED.items():
            home = WORKBENCH / rel
            body = home.read_text(encoding="utf-8")
            self.assertIn(anchor, body, f"rule {number} missing from {rel}")
            self.assertIn(str(number), claude)
            self.assertIn(rel.split("/")[-1], claude, f"CLAUDE.md does not point at {rel}")


if __name__ == "__main__":
    unittest.main()
