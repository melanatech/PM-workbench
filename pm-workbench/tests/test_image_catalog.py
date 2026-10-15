"""Tests for scripts/image_catalog.py."""
from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import image_catalog  # noqa: E402


class ImageCatalogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "state").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_idempotent_and_match(self):
        image_catalog.append_row(
            self.root,
            image_path="archive/documents/hub.png",
            kind="design",
            one_line='Reports Hub playground, "checkpoint" view',
            related_ids="INIT-001",
            entities="INIT-001,Reports Hub",
            parent_path="archive/documents/hub.md",
        )
        image_catalog.append_row(
            self.root,
            image_path="archive/documents/hub.png",
            kind="design",
            one_line="Reports Hub playground refreshed note",
            related_ids="INIT-001,EV-010",
            parent_path="archive/documents/hub.md",
        )
        rows = image_catalog.read_rows(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["one_line"], "Reports Hub playground refreshed note")
        self.assertIn("EV-010", rows[0]["related_ids"])
        with (self.root / "state" / "image-catalog.csv").open(encoding="utf-8", newline="") as fh:
            reread = list(csv.DictReader(fh))
        self.assertEqual(reread[0]["one_line"], "Reports Hub playground refreshed note")

        hits = image_catalog.match(self.root, related_ids="INIT-001")
        self.assertEqual([row["image_path"] for row in hits], ["archive/documents/hub.png"])

    def test_guess_kind(self):
        self.assertEqual(image_catalog.guess_kind("archive/x/.pages/page-03.png"), "pdf-page")
        self.assertEqual(image_catalog.guess_kind("walk.step-02.png"), "walkthrough-step")
        self.assertEqual(image_catalog.guess_kind("reports-hub-phase-playground.png"), "design")

    def test_one_line_required(self):
        with self.assertRaises(ValueError):
            image_catalog.append_row(
                self.root, image_path="a.png", kind="screenshot", one_line="  "
            )

    def test_cli(self):
        code = image_catalog.main(
            [
                "append",
                "--root",
                str(self.root),
                "--path",
                "archive/a.png",
                "--kind",
                "screenshot",
                "--one-line",
                "viewport of orders report",
                "--related-ids",
                "INIT-001",
            ]
        )
        self.assertEqual(code, 0)
        code = image_catalog.main(
            ["match", "--root", str(self.root), "--related-ids", "INIT-001"]
        )
        self.assertEqual(code, 0)


class ImageCatalogContractTests(unittest.TestCase):
    def test_workflows_mention_catalog(self):
        import fanout_route

        triage = (WORKBENCH / ".claude/workflows/_source-triage.md").read_text(encoding="utf-8")
        process = (WORKBENCH / ".claude/workflows/process-inbox.md").read_text(encoding="utf-8")
        fanout = (WORKBENCH / ".claude/workflows/_fan-out.md").read_text(encoding="utf-8")
        self.assertIn("image-catalog.csv", triage)
        self.assertIn("image_catalog.py", process)
        self.assertIn("visual", fanout)
        self.assertIn(16, fanout_route.SURFACES)
        self.assertEqual(set(fanout_route.ROUTES["visual"]), {16})


if __name__ == "__main__":
    unittest.main()
