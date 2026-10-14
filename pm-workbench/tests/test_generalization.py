"""Kit surfaces must not anchor on one company, person, or internal role.

Extends the local bans in test_routing.py (gdcorp-commerce, project keys) to a
walk of instruction files. Excludes the fictional Lumenly fixture, gitignored
local context, and tests/ (tests may quote a banned token inside an assertion).
"""
import unittest
from pathlib import Path


WORKBENCH = Path(__file__).resolve().parents[1]

# Substrings that mark a company, person, product area, or internal ticket.
BANNED = (
    "Antonio",
    "Seamless",
    "GoDaddy",
    "godaddy",
    "gdcorp",
    "iGCR",
    "explanations-transactions",
    "cx-reports",
    "commerce-intelligence",
    "CP-5835",
    "REPORT-1915",
    "DATASHEET-VS-CUBE",
    "term registers",
    "term-registers",
)

SKIP_DIR_NAMES = {
    ".git",
    "__pycache__",
    "node_modules",
    "fixtures",
    "tests",
    "inbox",
    "archive",
    "state",
    "logs",
    "registers",
    "repos",
    "outputs",
    "browser-profiles",
}
SKIP_FILES = {
    WORKBENCH / ".claude" / "CLAUDE.local.md",
}
TEXT_SUFFIXES = {".md", ".py", ".json", ".yml", ".yaml", ".html", ".js", ".jsx", ".sh", ".css"}


def kit_texts():
    for path in WORKBENCH.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {"Run PM Workflow.command"}:
            continue
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(WORKBENCH).parts):
            continue
        if path in SKIP_FILES or path.name == "CLAUDE.local.md":
            continue
        # fixtures/ is skipped via the directory name; lumenly lives there.
        yield path


class GeneralizationTests(unittest.TestCase):
    def test_no_company_person_or_role_anchors(self):
        hits = []
        for path in kit_texts():
            text = path.read_text(encoding="utf-8", errors="replace")
            for token in BANNED:
                if token in text:
                    line_no = text[: text.index(token)].count("\n") + 1
                    rel = path.relative_to(WORKBENCH)
                    hits.append(f"{rel}:{line_no}: {token}")
        self.assertEqual(hits, [], "company/person anchors:\n" + "\n".join(hits))

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
