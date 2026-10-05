#!/usr/bin/env python3
"""Tests for clipboard → live inbox capture."""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPTS = WORKBENCH / "scripts"
sys.path.insert(0, str(SCRIPTS))

import capture_clipboard  # noqa: E402


class CaptureClipboardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-clipb-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.live = self.tmp / "live"
        (self.live / "inbox").mkdir(parents=True)

    def test_write_capture_lands_in_live_inbox(self):
        path = capture_clipboard.write_capture(
            str(self.live), "discovery", "Harbor Dental asked about exports", title="slack"
        )
        self.assertTrue(path.startswith(str(self.live)))
        self.assertIn("/inbox/discovery/", path.replace("\\", "/"))
        text = Path(path).read_text(encoding="utf-8")
        self.assertIn("capture_kind: clipboard", text)
        self.assertIn("Harbor Dental asked about exports", text)

    def test_empty_body_raises(self):
        with self.assertRaises(ValueError):
            capture_clipboard.write_capture(str(self.live), "captures", "   ")

    def test_main_uses_live_root_not_kit(self):
        with mock.patch.object(capture_clipboard, "read_clipboard", return_value="from slack"):
            with mock.patch.object(capture_clipboard, "choose_category_gui", return_value=None):
                with mock.patch.object(capture_clipboard, "choose_category_tty", return_value="captures"):
                    rc = capture_clipboard.main(["--root", str(self.live)])
        self.assertEqual(rc, 0)
        files = list((self.live / "inbox" / "captures").glob("*.md"))
        self.assertEqual(len(files), 1)


if __name__ == "__main__":
    unittest.main()
