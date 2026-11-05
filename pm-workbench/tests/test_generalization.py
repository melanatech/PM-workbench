"""Kit surfaces must not anchor on one person, company, project, or internal system.

The terms themselves live in the gitignored `.claude/kit-private-terms.txt` and the
local PM identity file, so this public test never lists them. Built-in patterns
(emails, home-directory paths, private wiki or dashboard URLs) run even without
that file. See `scripts/check_kit_generic.py`.
"""
import subprocess
import sys
import unittest
from pathlib import Path


WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))

import check_kit_generic  # noqa: E402


class GeneralizationTests(unittest.TestCase):
    def test_no_private_terms_in_any_kit_file(self):
        hits = check_kit_generic.scan(check_kit_generic.kit_files())
        self.assertEqual(hits, [], "private terms in the kit:\n" + "\n".join(hits))

    def test_terms_file_and_local_context_are_gitignored(self):
        root = WORKBENCH.parent
        for rel in (".claude/kit-private-terms.txt", ".claude/CLAUDE.local.md", ".cursor/hooks/pm-identity.json"):
            r = subprocess.run(["git", "check-ignore", "-q", f"{WORKBENCH.name}/{rel}"], cwd=root)
            self.assertEqual(r.returncode, 0, f"{rel} must be gitignored")

    def test_checker_catches_a_planted_term(self):
        terms = [("Acme Widgets", check_kit_generic._plain("Acme Widgets"))]
        hits = check_kit_generic.scan_text("Ask the Acme Widgets team.\nmail a.b@" + "corpmail.com", terms)
        labels = {h[1] for h in hits}
        self.assertIn("Acme Widgets", labels)
        self.assertIn("email address", labels)
        self.assertEqual(check_kit_generic.scan_text("See /Users/someone/x and a@example.com", terms), [])

    def test_named_surfaces_point_at_aliases_not_a_company_workbook(self):
        claude = (WORKBENCH / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("workspace-aliases", (WORKBENCH / ".claude/skills/authority-lookup/SKILL.md").read_text(encoding="utf-8"))
        self.assertNotIn("DATASHEET", claude)
        example = (WORKBENCH / "reference/context/workspace-aliases.example.md").read_text(encoding="utf-8")
        self.assertNotIn("Orders", example)
        self.assertNotIn("Payments", example)
        self.assertNotIn("Cube", example)


if __name__ == "__main__":
    unittest.main()
