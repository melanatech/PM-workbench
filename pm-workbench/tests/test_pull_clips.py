#!/usr/bin/env python3
"""Tests for pull_clips / watch_clips bridge out of Downloads."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPTS = WORKBENCH / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pull_clips  # noqa: E402


class PullClipsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-clips-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.live = self.tmp / "live"
        self.downloads = self.tmp / "Downloads" / "pm-workbench-inbox" / "meetings"
        self.downloads.mkdir(parents=True)
        (self.live / "inbox").mkdir(parents=True)
        (self.downloads / "clip-one.md").write_text("---\ncapture_kind: page\n---\nhello\n", encoding="utf-8")
        original = pull_clips.clip_sources
        pull_clips.clip_sources = lambda: [str(self.tmp / "Downloads" / "pm-workbench-inbox")]
        self.addCleanup(setattr, pull_clips, "clip_sources", original)

    def test_pull_moves_into_live_inbox(self):
        count, moved = pull_clips.pull_clips(str(self.live))
        self.assertEqual(count, 1)
        self.assertEqual(moved, ["inbox/meetings/clip-one.md"])
        dest = self.live / "inbox" / "meetings" / "clip-one.md"
        self.assertTrue(dest.is_file())
        self.assertFalse((self.downloads / "clip-one.md").exists())

    def test_pull_moves_document_csv(self):
        docs = self.tmp / "Downloads" / "pm-workbench-inbox" / "documents"
        docs.mkdir(parents=True)
        (docs / "Reports Roadmap.csv").write_text(
            "Summary,Theme\nInteractive Transactions Report,Reporting\n",
            encoding="utf-8",
        )
        count, moved = pull_clips.pull_clips(str(self.live))
        self.assertEqual(count, 2)  # meetings md from setUp + documents csv
        self.assertIn("inbox/documents/Reports Roadmap.csv", moved)
        self.assertTrue((self.live / "inbox" / "documents" / "Reports Roadmap.csv").is_file())
        self.assertFalse((docs / "Reports Roadmap.csv").exists())

    def test_resolve_live_root_uses_marker(self):
        marker_dir = self.tmp / "marker-home" / ".pm-workbench"
        marker_dir.mkdir(parents=True)
        (marker_dir / "live-root").write_text(str(self.live) + "\n", encoding="utf-8")
        home = os.environ.get("HOME")
        os.environ["HOME"] = str(self.tmp / "marker-home")
        self.addCleanup(os.environ.__setitem__, "HOME", home if home is not None else "")
        os.environ.pop("PM_LIVE_ROOT", None)
        self.assertEqual(
            os.path.realpath(pull_clips.resolve_live_root()),
            os.path.realpath(self.live),
        )


if __name__ == "__main__":
    unittest.main()
