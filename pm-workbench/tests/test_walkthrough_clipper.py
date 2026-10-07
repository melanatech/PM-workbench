"""Walkthrough clipper + intake wiring (static checks; no Chrome)."""
from pathlib import Path
import unittest

WORKBENCH = Path(__file__).resolve().parents[1]
CLIPPER = WORKBENCH / "tools" / "workbench-clipper"
WORKFLOWS = WORKBENCH / ".claude" / "workflows"


class WalkthroughClipperTests(unittest.TestCase):
    def test_manifest_v05_permissions(self):
        text = (CLIPPER / "manifest.json").read_text(encoding="utf-8")
        self.assertIn('"0.5.0"', text)
        self.assertIn("storage", text)
        self.assertIn("alarms", text)
        self.assertIn("pmwb-wt-mark", text)
        self.assertIn("host_permissions", text)

    def test_walkthrough_session_and_content_scripts_exist(self):
        self.assertTrue((CLIPPER / "walkthrough-session.js").is_file())
        self.assertTrue((CLIPPER / "content-walkthrough.js").is_file())
        bg = (CLIPPER / "background.js").read_text(encoding="utf-8")
        self.assertIn("importScripts('walkthrough-session.js')", bg)
        self.assertIn("wtHandleMenu", bg)
        self.assertIn("wtAppendMenus", bg)
        wt = (CLIPPER / "walkthrough-session.js").read_text(encoding="utf-8")
        self.assertIn("WT_MAX_STEPS", wt)
        self.assertIn("capture_kind: walkthrough", wt)
        self.assertIn("walkthroughs/", wt)
        self.assertIn("scroll_settle", wt)
        self.assertIn("mark_step", wt)
        content = (CLIPPER / "content-walkthrough.js").read_text(encoding="utf-8")
        self.assertIn("password", content)
        self.assertIn("pmwb-walkthrough", content)

    def test_pull_clips_and_process_inbox_walkthroughs(self):
        import sys
        sys.path.insert(0, str(WORKBENCH / "scripts"))
        import pull_clips
        self.assertIn("walkthroughs", pull_clips.CATEGORIES)
        layout = (WORKBENCH / "scripts" / "workspace_layout.py").read_text(encoding="utf-8")
        self.assertIn("inbox/walkthroughs", layout)
        inbox = (WORKFLOWS / "process-inbox.md").read_text(encoding="utf-8")
        self.assertIn("capture_kind: walkthrough", inbox)
        self.assertIn("inbox/walkthroughs/", inbox)
        learn = (WORKFLOWS / "learn-product-flow.md").read_text(encoding="utf-8")
        self.assertIn("walkthrough", learn.lower())
        self.assertIn("logged-in Chrome", learn)

    def test_readme_documents_viewport_and_mark_step(self):
        readme = (CLIPPER / "README.md").read_text(encoding="utf-8")
        self.assertIn("Walkthrough", readme)
        self.assertIn("viewport", readme.lower())
        self.assertIn("Mark step", readme)
        self.assertIn("0.5.0", readme)


if __name__ == "__main__":
    unittest.main()
