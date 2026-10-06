#!/usr/bin/env python3
"""Tests for scripts/extract_document.sh."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "extract_document.sh"


class ExtractDocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-extract-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_extract(self, path: Path):
        return subprocess.run(
            ["bash", str(SCRIPT), str(path)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_copy_through_txt(self):
        src = self.tmp / "note.txt"
        src.write_text("hello kit\n", encoding="utf-8")
        r = self.run_extract(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = Path(r.stdout.strip().splitlines()[-1])
        self.assertTrue(out.is_file())
        self.assertIn("hello kit", out.read_text(encoding="utf-8"))

    @unittest.skipUnless(shutil.which("textutil"), "textutil not available")
    def test_rtf_via_textutil(self):
        plain = self.tmp / "plain.txt"
        plain.write_text("rtf extract works\n", encoding="utf-8")
        rtf = self.tmp / "plain.rtf"
        subprocess.run(
            ["textutil", "-convert", "rtf", str(plain), "-output", str(rtf)],
            check=True,
            capture_output=True,
        )
        r = self.run_extract(rtf)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = Path(r.stdout.strip().splitlines()[-1])
        self.assertIn("rtf extract works", out.read_text(encoding="utf-8"))

    def test_unsupported_extension_exits_2(self):
        src = self.tmp / "deck.pptx"
        src.write_bytes(b"not a real pptx")
        r = self.run_extract(src)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("Unsupported", r.stderr)

    def test_missing_file_exits_1(self):
        r = self.run_extract(self.tmp / "nope.docx")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
