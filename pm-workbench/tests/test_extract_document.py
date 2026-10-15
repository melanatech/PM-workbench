#!/usr/bin/env python3
"""Tests for scripts/extract_document.sh."""
import shutil
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "extract_document.sh"


def _write_minimal_xlsx(path: Path, headers, row, formula_cells=None):
    """Build a tiny OOXML workbook with one sheet (stdlib only).

    formula_cells: optional list of (ref, formula_body, cached_value) e.g.
    ("C2", "A2+B2", "10").
    """
    shared = list(headers) + list(row)
    sst_items = "".join(f'<si><t>{escape(s)}</t></si>' for s in shared)
    shared_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        f'count="{len(shared)}" uniqueCount="{len(shared)}">{sst_items}</sst>'
    )
    # A1.. headers as shared string indices 0..n-1; row as n..
    cells = []
    for i, _ in enumerate(headers):
        col = chr(ord("A") + i)
        cells.append(f'<c r="{col}1" t="s"><v>{i}</v></c>')
    for i, _ in enumerate(row):
        col = chr(ord("A") + i)
        cells.append(f'<c r="{col}2" t="s"><v>{len(headers) + i}</v></c>')
    formula_xml = []
    for ref, body, cached in formula_cells or []:
        formula_xml.append(
            f'<c r="{ref}"><f>{escape(body)}</f><v>{escape(str(cached))}</v></c>'
        )
    row2_extra = "".join(formula_xml)
    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData><row r="1">{"".join(cells[: len(headers)])}</row>'
        f'<row r="2">{"".join(cells[len(headers) :])}{row2_extra}</row></sheetData></worksheet>'
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Metrics" sheetId="1" r:id="rId1"/></sheets></workbook>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
        'Target="worksheets/sheet1.xml"/></Relationships>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '<Override PartName="/xl/sharedStrings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
        "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/></Relationships>'
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
        zf.writestr("xl/sharedStrings.xml", shared_xml)


class ExtractDocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-extract-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def run_extract(self, path: Path, *extra: str):
        return subprocess.run(
            ["bash", str(SCRIPT), str(path), *extra],
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

    def test_html_includes_embedded_javascript_data_when_visible_text_is_sparse(self):
        src = self.tmp / "okr.html"
        src.write_text(
            """<!doctype html>
<html>
<head><title>Commerce OKRs</title><style>.app { display: grid; }</style></head>
<body>
  <main id="app">DOP Q&amp;A prep</main>
  <script>
    const OBJS = [
      {n: 1, objective: "Grow commerce", krs: ["Increase adoption to 40%"]},
      {n: 2, objective: "Improve retention", krs: ["Reduce churn to 5%"]}
    ];
    function render() { return OBJS.map(x => x.objective).join(", "); }
  </script>
</body>
</html>
""",
            encoding="utf-8",
        )
        r = self.run_extract(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        text = Path(r.stdout.strip().splitlines()[-1]).read_text(encoding="utf-8")
        self.assertIn("Commerce OKRs", text)
        self.assertIn("## Embedded JavaScript data", text)
        self.assertIn('objective: "Grow commerce"', text)
        self.assertIn('krs: ["Reduce churn to 5%"]', text)
        self.assertNotIn("function render", text)

    def test_unsupported_extension_exits_2(self):
        src = self.tmp / "deck.pptx"
        src.write_bytes(b"not a real pptx")
        r = self.run_extract(src)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("Unsupported", r.stderr)

    def test_xlsx_extracts_cell_text(self):
        src = self.tmp / "okr.xlsx"
        _write_minimal_xlsx(src, ["metric", "value"], ["activation", "12.4"])
        r = self.run_extract(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = Path(r.stdout.strip().splitlines()[-1])
        text = out.read_text(encoding="utf-8")
        self.assertIn("### Sheet: Metrics", text)
        self.assertIn("activation", text)
        self.assertIn("12.4", text)
        self.assertNotIn("## Formulas", text)

    def test_xlsx_formulas_flag(self):
        src = self.tmp / "calc.xlsx"
        _write_minimal_xlsx(
            src,
            ["a", "b"],
            ["1", "2"],
            formula_cells=[("C2", "A2+B2", "3")],
        )
        r = self.run_extract(src, "--formulas")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = Path(r.stdout.strip().splitlines()[-1]).read_text(encoding="utf-8")
        self.assertIn("## Formulas", text)
        self.assertIn("C2\t=A2+B2\t[cached: 3]", text)
        # Default path still values-only
        r2 = self.run_extract(src)
        self.assertNotIn("## Formulas", Path(r2.stdout.strip().splitlines()[-1]).read_text())

    def test_xlsm_uses_same_path(self):
        src = self.tmp / "model.xlsm"
        _write_minimal_xlsx(src, ["a"], ["hello-xlsm"])
        r = self.run_extract(src)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = Path(r.stdout.strip().splitlines()[-1])
        self.assertIn("hello-xlsm", out.read_text(encoding="utf-8"))

    def test_legacy_xls_still_unsupported(self):
        src = self.tmp / "old.xls"
        src.write_bytes(b"not ole")
        r = self.run_extract(src)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_missing_file_exits_1(self):
        r = self.run_extract(self.tmp / "nope.docx")
        self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
