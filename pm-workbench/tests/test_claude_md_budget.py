"""CLAUDE.md stays a short core contract; the 27 standing rules live in
`_operator-rules.md` and moved rules keep their numbers at the new home."""
import re
import unittest
from pathlib import Path


WORKBENCH = Path(__file__).resolve().parents[1]
CLAUDE = WORKBENCH / "CLAUDE.md"
OPERATOR_RULES = WORKBENCH / ".claude" / "workflows" / "_operator-rules.md"
MAX_WORDS = 400

# rule number → (path relative to the kit, anchor that must appear there)
MOVED = {
    5: (".claude/workflows/okr-refresh.md", "Rule 5"),
    18: (".claude/workflows/_protocol.md", "Rule 18"),
    19: (".claude/workflows/_protocol.md", "Rule 19"),
    20: (".claude/workflows/_protocol.md", "Rule 20"),
    23: (".claude/workflows/_protocol.md", "Rule 23"),
    25: (".claude/skills/authority-lookup/SKILL.md", "Rule 25"),
    26: (".claude/skills/authority-lookup/SKILL.md", "Rule 26"),
}


class ClaudeMdBudgetTests(unittest.TestCase):
    def test_word_budget(self):
        words = CLAUDE.read_text(encoding="utf-8").split()
        self.assertLessEqual(
            len(words),
            MAX_WORDS,
            f"CLAUDE.md is {len(words)} words; budget is {MAX_WORDS}",
        )

    def test_core_contract_names_both_modes_and_the_rules_file(self):
        claude = CLAUDE.read_text(encoding="utf-8")
        self.assertIn("_operator-rules.md", claude)
        self.assertIn("partner", claude.lower())
        self.assertIn("Hard lines", claude)

    def test_rule_numbers_stay_in_operator_rules(self):
        text = OPERATOR_RULES.read_text(encoding="utf-8")
        numbered = {int(n) for n in re.findall(r"(?m)^(\d+)\. ", text)}
        self.assertEqual(numbered, set(range(1, 28)))

    def test_moved_rules_keep_their_number_at_the_new_home(self):
        rules = OPERATOR_RULES.read_text(encoding="utf-8")
        for number, (rel, anchor) in MOVED.items():
            home = WORKBENCH / rel
            body = home.read_text(encoding="utf-8")
            self.assertIn(anchor, body, f"rule {number} missing from {rel}")
            self.assertIn(str(number), rules)
            self.assertIn(
                rel.split("/")[-1], rules, f"_operator-rules.md does not point at {rel}"
            )


if __name__ == "__main__":
    unittest.main()
