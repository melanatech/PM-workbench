"""Tests for scripts/recurring_corrections.py."""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))

import recurring_corrections as rc  # noqa: E402


class ThemeMatchTests(unittest.TestCase):
    def test_assume_vs_search(self):
        self.assertEqual(rc._match_theme("you assumed glossary for term registers"), "assume_vs_search")

    def test_nonexistent_id(self):
        self.assertEqual(rc._match_theme("COM-032 doesn't exist in commitments"), "nonexistent_id")

    def test_links_paths(self):
        self.assertEqual(rc._match_theme("make every path a clickable markdown link"), "links_paths")

    def test_workspace_sources(self):
        self.assertEqual(rc._match_theme("incomplete transcript — please recapture with clipper"), "workspace_sources")


class SummarizeTests(unittest.TestCase):
    def test_needs_two_hits(self):
        rows = [
            {"user_excerpt": "term registers wrong file", "timestamp": "2026-10-10T12:00:00"},
            {"user_excerpt": "you guessed the glossary", "timestamp": "2026-10-13T12:00:00"},
            {"user_excerpt": "one-off random complaint", "timestamp": "2026-10-13T13:00:00"},
        ]
        items = rc.summarize(rows, min_count=2)
        themes = {i["theme"] for i in items}
        self.assertIn("assume_vs_search", themes)
        self.assertNotIn("other_correction", themes)
        self.assertTrue(any(i["count"] >= 2 for i in items))

    def test_cli_on_temp_root(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state").mkdir()
            hist = root / "state" / "usage-history.csv"
            with hist.open("w", encoding="utf-8", newline="") as fh:
                w = csv.DictWriter(
                    fh,
                    fieldnames=[
                        "session_id",
                        "message_uuid",
                        "timestamp",
                        "user_excerpt",
                        "category",
                    ],
                )
                w.writeheader()
                for i in range(2):
                    w.writerow(
                        {
                            "session_id": "s",
                            "message_uuid": str(i),
                            "timestamp": f"2026-10-1{i}T00:00:00",
                            "user_excerpt": "bare path not a clickable link rule 20",
                            "category": "rework_correction",
                        }
                    )
            code = rc.main(["--root", str(root)])
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
