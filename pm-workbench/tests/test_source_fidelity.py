"""Fidelity classification for summaries, previews, and full threads."""
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import capture_clipboard  # noqa: E402
import source_fidelity  # noqa: E402

SLACK_PREVIEW = """Export question
Alex: Can we change the filter?
3 replies
View thread
"""

AI_RECAP = """AI summary
The group reviewed the export filter.
Decision: ship the filter next week.
Owner: Pat
Due: 2026-10-20
"""

AI_RECAP_QUIET = """AI summary
The group looked at the dashboard layout.
"""

FULL_THREAD = """2026-10-14 09:01 Pat: Let's walk the export flow.
2026-10-14 09:04 Alex: The filter is in review.
2026-10-14 09:06 Pat: No decision yet. We still need a second pass.
"""


class FidelityTests(unittest.TestCase):
    def test_preview_recap_and_full_thread(self):
        self.assertEqual(source_fidelity.classify_fidelity(SLACK_PREVIEW), "excerpt")
        self.assertEqual(source_fidelity.classify_fidelity(AI_RECAP), "summary")
        self.assertEqual(source_fidelity.classify_fidelity(FULL_THREAD), "full")

    def test_only_a_material_summary_asks(self):
        material = source_fidelity.fidelity_gate(AI_RECAP)
        self.assertTrue(material["material"])
        self.assertTrue(material["ask"])
        self.assertEqual(material["action"], "ask")
        self.assertEqual(material["tag"], "source_fidelity=summary")

        quiet = source_fidelity.fidelity_gate(AI_RECAP_QUIET)
        self.assertFalse(quiet["material"])
        self.assertFalse(quiet["ask"])
        self.assertEqual(quiet["action"], "proceed-labeled")
        self.assertEqual(quiet["tag"], "source_fidelity=summary")

        full = source_fidelity.fidelity_gate(FULL_THREAD)
        self.assertTrue(full["material"])
        self.assertFalse(full["ask"])
        self.assertEqual(full["action"], "proceed")

        preview = source_fidelity.fidelity_gate(SLACK_PREVIEW)
        self.assertFalse(preview["ask"])
        self.assertEqual(preview["fidelity"], "excerpt")

    def test_unattended_labels_and_does_not_ask(self):
        gate = source_fidelity.fidelity_gate(AI_RECAP, unattended=True)
        self.assertFalse(gate["ask"])
        self.assertEqual(gate["action"], "proceed-labeled")
        self.assertEqual(gate["tag"], "source_fidelity=summary")

    def test_frontmatter_fidelity_wins(self):
        text = "---\nfidelity: full\n---\nAI summary\nDecision: ship it.\n"
        self.assertEqual(source_fidelity.classify_fidelity(text), "full")

    def test_clipboard_writes_a_fidelity_hint(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        live = Path(tmp.name)
        (live / "inbox").mkdir()
        path = capture_clipboard.write_capture(str(live), "slack", SLACK_PREVIEW, title="thread")
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("fidelity: excerpt", text)
        path = capture_clipboard.write_capture(str(live), "meetings", FULL_THREAD, title="sync")
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("fidelity: full", text)


if __name__ == "__main__":
    unittest.main()
