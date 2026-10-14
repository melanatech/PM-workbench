"""Context manifest health: template-empty, stale, and ok."""
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import context_health  # noqa: E402


class ManifestTests(unittest.TestCase):
    def test_manifest_lists_the_context_kinds(self):
        rows = {row["id"]: row for row in context_health.load_manifest(WORKBENCH)}
        for key in (
            "current-priorities",
            "people",
            "systems-map",
            "audiences",
            "writing-style",
            "product-areas",
            "kr-metric-map",
            "identity",
        ):
            self.assertIn(key, rows, key)
        self.assertEqual(rows["kr-metric-map"]["path"], "reference/metric-definitions/kr-metric-map.md")
        self.assertEqual(rows["systems-map"]["path"], "reference/context/systems-map.md")
        self.assertEqual(rows["audiences"]["path"], "reference/context/audiences.md")
        self.assertEqual(rows["people"]["path"], "reference/context/people.md")
        self.assertEqual(rows["current-priorities"]["freshness_days"], 7)
        self.assertEqual(rows["systems-map"]["freshness_days"], 0)


class ClassifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        context = self.root / "reference" / "context"
        context.mkdir(parents=True)
        shutil.copy(WORKBENCH / "reference" / "context" / "_manifest.md", context / "_manifest.md")
        self.today = date(2026, 10, 14)

    def tearDown(self):
        self.tmp.cleanup()

    def _rows(self):
        return {row["id"]: row for row in context_health.assess(self.root, today=self.today)}

    def test_template_empty_stale_and_ok(self):
        (self.root / "reference/context/people.md").write_text(
            "status: template\nlast_updated:\n\n# People\n\n- [NEEDS INPUT]\n",
            encoding="utf-8",
        )
        (self.root / "reference/context/current-priorities.md").write_text(
            "# Priorities\n\nlast_updated: 2020-01-01\n\n1. Ship the export work.\n",
            encoding="utf-8",
        )
        (self.root / "reference/context/writing-style.md").write_text(
            "# Style\n\nlast_updated: 2020-01-01\n\n1. Lead with the ask, then the date.\n",
            encoding="utf-8",
        )
        rows = self._rows()
        self.assertEqual(rows["people"]["status"], "template-empty")
        self.assertEqual(rows["current-priorities"]["status"], "stale")
        self.assertEqual(rows["writing-style"]["status"], "ok")
        self.assertEqual(rows["audiences"]["status"], "missing")
        self.assertEqual(rows["identity"]["status"], "missing")
        line = context_health.brief_line(list(rows.values()))
        self.assertIn("/brief context-setup", line)
        self.assertIn("template-empty", line)
        self.assertIn("stale", line)
        self.assertNotEqual(line, "context: ok")

    def test_brief_line_is_ok_when_filtered_rows_are_filled(self):
        (self.root / "reference/context/people.md").write_text(
            "# People\n\nlast_updated: 2026-10-10\n\n- Ada owns the export surface. Source: notes 2026-10-10.\n",
            encoding="utf-8",
        )
        rows = context_health.assess(self.root, today=self.today, ids=["people"])
        self.assertEqual(context_health.brief_line(rows), "context: ok")

    def test_glossary_placeholder_is_template_empty(self):
        text = (WORKBENCH / "reference/context/glossary.md").read_text(encoding="utf-8")
        self.assertTrue(context_health.is_template_empty(text))

    def test_status_template_wins_over_prose(self):
        self.assertTrue(
            context_health.is_template_empty(
                "status: template\n\n# Priorities\n\nThis file explains itself at length.\n"
            )
        )


if __name__ == "__main__":
    unittest.main()
