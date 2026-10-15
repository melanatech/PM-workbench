"""Tests for scripts/source_index.py."""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import source_index  # noqa: E402


class SourceIndexTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_idempotent_and_csv_quoting(self):
        source_index.append_row(
            self.root,
            source_path="archive/documents/okr.html",
            source_role="strategy",
            temporal_status="current",
            origin="primary",
            outcome="promote",
            reason='Company OKRs, "not" business-level',
            entities="INIT-004,MAPU",
            summary="2027 commerce OKRs",
            content_hash_value="abc",
            sensitivity="none",
        )
        source_index.append_row(
            self.root,
            source_path="archive/documents/okr.html",
            source_role="strategy",
            temporal_status="current",
            origin="primary",
            outcome="hold",
            reason="updated reason",
            entities="INIT-004",
            summary="refreshed",
            content_hash_value="abc",
        )
        rows = source_index.read_rows(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["outcome"], "hold")
        self.assertEqual(rows[0]["reason"], "updated reason")
        # Round-trip through csv module handles commas/quotes.
        with (self.root / "state" / "source-index.csv").open(encoding="utf-8", newline="") as fh:
            reread = list(csv.DictReader(fh))
        self.assertEqual(reread[0]["entities"], "INIT-004")

    def test_match_by_entity(self):
        source_index.append_row(
            self.root,
            source_path="a.md",
            entities="INIT-004,MAPU",
            outcome="hold",
            summary="one",
        )
        source_index.append_row(
            self.root,
            source_path="b.md",
            entities="INIT-009",
            outcome="index",
            summary="two",
        )
        hits = source_index.match_entities(self.root, "MAPU,INIT-009")
        paths = {row["source_path"] for row in hits}
        self.assertEqual(paths, {"a.md", "b.md"})
        held = source_index.match_entities(self.root, "INIT-004", status="open")
        self.assertEqual([row["source_path"] for row in held], ["a.md"])

    def test_promote_sets_status_and_linked_ids(self):
        source_index.append_row(
            self.root,
            source_path="archive/meetings/ideas.md",
            outcome="hold",
            entities="INIT-004",
            summary="ideas",
        )
        ok = source_index.promote(
            self.root, "archive/meetings/ideas.md", linked_ids="EV-001,DEC-002"
        )
        self.assertTrue(ok)
        row = source_index.read_rows(self.root)[0]
        self.assertEqual(row["status"], "promoted")
        self.assertEqual(row["outcome"], "promote")
        self.assertEqual(set(row["linked_ids"].split(",")), {"DEC-002", "EV-001"})
        self.assertFalse(source_index.promote(self.root, "missing.md"))

    def test_find_duplicate_hash_and_stem(self):
        docs = self.root / "docs"
        docs.mkdir()
        a = docs / "report.md"
        b = docs / "report.html"
        a.write_text("Same   content\nhere\n", encoding="utf-8")
        b.write_text("Same content here", encoding="utf-8")
        digest = source_index.content_hash(a)
        source_index.append_row(
            self.root,
            source_path="docs/report.md",
            outcome="promote",
            content_hash_value=digest,
            summary="kept",
        )
        hit = source_index.find_duplicate(self.root, b)
        self.assertEqual(hit["match_kind"], "hash")
        self.assertEqual(hit["same_as"], "docs/report.md")

        # Stem grouping for CSV bundle members.
        c1 = docs / "commissions-new.csv"
        c2 = docs / "commissions-accounting.csv"
        c1.write_text("id,amount\n1,2\n", encoding="utf-8")
        c2.write_text("id,amount\n3,4\n", encoding="utf-8")
        source_index.append_row(
            self.root,
            source_path="docs/commissions-new.csv",
            outcome="index",
            content_hash_value=source_index.content_hash(c1),
            summary="bundle primary",
        )
        stem_hit = source_index.find_duplicate(self.root, c2)
        self.assertEqual(stem_hit["match_kind"], "stem")
        self.assertEqual(stem_hit["same_as"], "docs/commissions-new.csv")

    def test_is_own_output(self):
        self.assertTrue(source_index.is_own_output("outputs/daily/x.md"))
        self.assertTrue(source_index.is_own_output("drafts/jira-2026-10-15.md"))
        self.assertTrue(source_index.is_own_output("prototypes/foo/index.html"))
        self.assertFalse(source_index.is_own_output("archive/documents/okr.html"))
        self.assertFalse(source_index.is_own_output("inbox/meetings/notes.md"))

    def test_own_output_forces_derived_own_origin(self):
        source_index.append_row(
            self.root,
            source_path="outputs/daily/returned.md",
            origin="primary",
            outcome="index",
            summary="kit wrote this",
        )
        row = source_index.read_rows(self.root)[0]
        self.assertEqual(row["origin"], "derived-own")

    def test_cli_append_and_match(self):
        code = source_index.main(
            [
                "append",
                "--root",
                str(self.root),
                "--path",
                "archive/x.md",
                "--source-role",
                "exploratory-thinking",
                "--outcome",
                "hold",
                "--entities",
                "INIT-004",
                "--summary",
                "ideas",
            ]
        )
        self.assertEqual(code, 0)
        code = source_index.main(
            ["match", "--root", str(self.root), "--entities", "INIT-004"]
        )
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
