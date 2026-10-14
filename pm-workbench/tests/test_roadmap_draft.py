"""Fixture checks for roadmap draft rules the workflow states in prose.

Dates on Now / Next / Later items must cite a tracker issue or a commitment.
Derived priority lines must carry the protocol label and a source.
Context health is what decides that the confirmation batch is required.
"""
import re
import shutil
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path


WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import context_health  # noqa: E402


DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
SOURCE_RE = re.compile(
    r"\b(?:EV|DEC|COM|INIT|RISK|TODO)-\d+\b"
    r"|commitments\.csv"
    r"|\b[A-Z][A-Z0-9]{1,9}-\d+\b"
)
DERIVED_LABEL = "derived, not stated priorities"
BUCKETS = ("Now", "Next", "Later")


def _bucket_items(markdown: str) -> list[str]:
    items = []
    capture = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            capture = title in BUCKETS
            continue
        if capture and stripped.startswith("- "):
            items.append(stripped[2:])
    return items


def unsourced_item_dates(markdown: str) -> list[str]:
    """Item dates with no tracker key, commitment id, or commitments.csv cite."""
    found = []
    for item in _bucket_items(markdown):
        if DATE_RE.search(item) and not SOURCE_RE.search(item):
            found.append(item)
    return found


def derived_label_gaps(markdown: str) -> list[str]:
    """A line that says it is derived must use the protocol label and cite a source."""
    gaps = []
    for line in markdown.splitlines():
        if "derived" not in line.lower():
            continue
        if DERIVED_LABEL not in line or not SOURCE_RE.search(line):
            gaps.append(line.strip())
    return gaps


class RoadmapDraftRuleTests(unittest.TestCase):
    def test_item_date_without_a_source_is_flagged(self):
        draft = "\n".join(
            [
                "# Roadmap — 2026-10-14",
                "## Now",
                "- Ship the export. 2026-11-01.",
                "## Next",
                "- Retry alerts. 2026-12-01. Source: COM-004.",
                "## Later",
                "- Mobile layout. [NEEDS INPUT]",
            ]
        )
        self.assertEqual(
            unsourced_item_dates(draft),
            ["Ship the export. 2026-11-01."],
        )
        self.assertEqual(derived_label_gaps(draft), [])

    def test_sourced_date_and_labeled_derivation_pass(self):
        draft = "\n".join(
            [
                "# Roadmap — 2026-10-14",
                "## Now",
                "- Export retry. 2026-11-01. Source: COM-004 in commitments.csv.",
                "- Tracker date 2026-11-15 from ABC-120.",
                "## Next",
                "- (derived, not stated priorities) Close the gap. Source: INIT-002.",
            ]
        )
        self.assertEqual(unsourced_item_dates(draft), [])
        self.assertEqual(derived_label_gaps(draft), [])

    def test_derived_without_the_label_or_a_source_is_flagged(self):
        draft = "\n".join(
            [
                "## Now",
                "- derived priority: ship export",
                "- derived, not stated priorities: ship export",
            ]
        )
        gaps = derived_label_gaps(draft)
        self.assertEqual(len(gaps), 2)

    def test_blank_priorities_are_a_health_gap(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        context = root / "reference" / "context"
        context.mkdir(parents=True)
        shutil.copy(
            WORKBENCH / "reference" / "context" / "_manifest.md",
            context / "_manifest.md",
        )
        (context / "current-priorities.md").write_text(
            "status: template\n\n# Priorities\n\n- [NEEDS INPUT]\n",
            encoding="utf-8",
        )
        rows = {
            row["id"]: row
            for row in context_health.assess(
                root,
                today=date(2026, 10, 14),
                ids=["current-priorities", "kr-metric-map"],
            )
        }
        self.assertIn(rows["current-priorities"]["status"], {"template-empty", "missing", "stale"})
        self.assertNotEqual(rows["current-priorities"]["status"], "ok")
        self.assertEqual(rows["kr-metric-map"]["status"], "missing")
        workflow = (WORKBENCH / ".claude" / "workflows" / "roadmap-build.md").read_text(encoding="utf-8")
        self.assertIn("confirm derived priorities", workflow)
        self.assertIn("before sequencing", workflow)
