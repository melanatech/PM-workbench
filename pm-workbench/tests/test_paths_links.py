#!/usr/bin/env python3
"""Tests for .claude/hooks/_paths.py link detection."""
import tempfile
import unittest
from pathlib import Path
import sys

HOOKS = Path(__file__).resolve().parents[1] / ".claude" / "hooks"
sys.path.insert(0, str(HOOKS))
from _paths import find_unlinked_paths, file_relative_href  # noqa: E402


class PathLinkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-paths-"))
        (self.tmp / "registers").mkdir()
        (self.tmp / "registers" / "risks.csv").write_text("id\n", encoding="utf-8")
        (self.tmp / "inbox" / "documents").mkdir(parents=True)
        (self.tmp / "outputs" / "daily").mkdir(parents=True)
        (self.tmp / "outputs" / "daily" / "note.md").write_text("# hi\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_bare_file_fails(self):
        text = "See registers/risks.csv for details."
        self.assertEqual(find_unlinked_paths(text, self.tmp), ["registers/risks.csv"])

    def test_bare_folder_fails(self):
        text = "Still in inbox/documents/ waiting."
        self.assertEqual(find_unlinked_paths(text, self.tmp), ["inbox/documents/"])

    def test_backtick_only_fails(self):
        text = "Open `registers/risks.csv` please."
        self.assertEqual(find_unlinked_paths(text, self.tmp), ["registers/risks.csv"])

    def test_linked_passes(self):
        text = "See [registers/risks.csv](registers/risks.csv) for details."
        self.assertEqual(find_unlinked_paths(text, self.tmp), [])

    def test_code_block_ignored(self):
        text = "```\nregisters/risks.csv\n```\nDone."
        self.assertEqual(find_unlinked_paths(text, self.tmp), [])

    def test_missing_path_ignored(self):
        text = "Will write outputs/daily/never-created.md later."
        self.assertEqual(find_unlinked_paths(text, self.tmp), [])

    def test_file_relative_href(self):
        href = file_relative_href("outputs/daily/note.md", "registers/risks.csv")
        self.assertEqual(href, "../../registers/risks.csv")

    def test_yaml_frontmatter_sources_ignored(self):
        text = (
            "---\n"
            "sources: [registers/risks.csv, inbox/documents/]\n"
            "---\n"
            "Body mentions nothing.\n"
        )
        self.assertEqual(find_unlinked_paths(text, self.tmp), [])
        text2 = text + "But see registers/risks.csv in prose.\n"
        self.assertEqual(find_unlinked_paths(text2, self.tmp), ["registers/risks.csv"])


if __name__ == "__main__":
    unittest.main()
