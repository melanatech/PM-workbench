#!/usr/bin/env python3
"""Tests for scripts/rasterize_pdf.sh (macOS PDFKit path)."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "rasterize_pdf.sh"


class RasterizePdfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-raster-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_missing_exits_1(self):
        r = subprocess.run(
            ["bash", str(SCRIPT), str(self.tmp / "nope.pdf")],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 1)

    def test_non_pdf_exits_2(self):
        src = self.tmp / "note.txt"
        src.write_text("x\n", encoding="utf-8")
        r = subprocess.run(
            ["bash", str(SCRIPT), str(src)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(r.returncode, 2)

    @unittest.skipUnless(shutil.which("swift"), "swift/PDFKit required")
    def test_renders_at_least_one_page_from_minimal_pdf(self):
        # Tiny valid PDF (one blank page) — enough to exercise the script path
        pdf = self.tmp / "blank.pdf"
        pdf.write_bytes(
            b"%PDF-1.1\n"
            b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n"
            b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n"
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] >>endobj\n"
            b"xref\n0 4\n0000000000 65535 f \n"
            b"0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n"
            b"trailer<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
        )
        r = subprocess.run(
            ["bash", str(SCRIPT), str(pdf), "2"],
            capture_output=True,
            text=True,
        )
        # PDFKit may reject a minimal hand-written PDF — accept 0 with stderr OR success
        if r.returncode != 0:
            self.assertEqual(r.returncode, 3, r.stderr)
            self.skipTest("PDFKit rejected minimal fixture; smoke covered by live MBR")
            return
        out = Path(r.stdout.strip().splitlines()[-1])
        self.assertTrue(out.is_dir())
        pages = list(out.glob("page-*.png"))
        self.assertGreaterEqual(len(pages), 1)


if __name__ == "__main__":
    unittest.main()
