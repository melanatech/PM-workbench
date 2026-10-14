#!/usr/bin/env python3
"""Tests for check_prototype_data.py."""
import importlib.util
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "check_prototype_data.py"
FIXTURES = WORKBENCH / "tests" / "fixtures" / "prototype-data"


def load_mod():
    spec = importlib.util.spec_from_file_location("check_prototype_data", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CheckPrototypeDataTests(unittest.TestCase):
    def run_check(self, proto: Path):
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(proto)],
            capture_output=True,
            text=True,
            check=False,
        )

    def write_proto(self, files: dict):
        root = Path(tempfile.mkdtemp(prefix="pmwb-proto-data-"))
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        for rel, content in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        return root

    def test_clean_passes(self):
        result = self.run_check(FIXTURES / "clean")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS literals", result.stdout)
        self.assertIn("PASS invariants", result.stdout)
        self.assertIn("PASS cross-screen", result.stdout)
        self.assertIn("result: pass", result.stdout)

    def test_hardcoded_literal_fails(self):
        result = self.run_check(FIXTURES / "fail-literal")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL literals", result.stdout)
        self.assertIn("Summary.jsx", result.stdout)
        self.assertIn("12", result.stdout)
        self.assertIn("PASS invariants", result.stdout)
        self.assertIn("PASS cross-screen", result.stdout)
        self.assertIn("result: fail", result.stdout)

    def test_broken_parts_sum_fails(self):
        result = self.run_check(FIXTURES / "fail-invariant")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("PASS literals", result.stdout)
        self.assertIn("FAIL invariants", result.stdout)
        self.assertIn("parts sum", result.stdout)
        self.assertIn("PASS cross-screen", result.stdout)

    def test_different_selectors_fail(self):
        result = self.run_check(FIXTURES / "fail-selector")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("PASS literals", result.stdout)
        self.assertIn("PASS invariants", result.stdout)
        self.assertIn("FAIL cross-screen", result.stdout)
        self.assertIn('metric "openCount"', result.stdout)
        self.assertIn("openTaskCount", result.stdout)
        self.assertIn("taskCount", result.stdout)
        self.assertIn("different selectors or copies", result.stdout)

    def test_missing_directory(self):
        result = self.run_check(FIXTURES / "does-not-exist")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    def test_skips_invariants_when_node_missing(self):
        mod = load_mod()
        buf = io.StringIO()
        with mock.patch.object(mod, "resolve_node", return_value=None), redirect_stdout(
            buf
        ):
            code = mod.main([str(FIXTURES / "clean")])
        output = buf.getvalue()
        self.assertEqual(code, 0, output)
        self.assertIn("SKIP invariants", output)
        self.assertIn("node is not available", output)
        self.assertIn("/usr/local/bin/node", output)
        self.assertIn("PASS literals", output)
        self.assertIn("result: pass", output)

    def test_allow_comment_suppresses_adjacent_literal(self):
        flagged = self.write_proto(
            {
                "src/components/Pager.jsx": "export function Pager() {\n"
                "  return <span>24</span>\n"
                "}\n"
            }
        )
        failed = self.run_check(flagged)
        self.assertEqual(failed.returncode, 1, failed.stdout + failed.stderr)
        self.assertIn("FAIL literals", failed.stdout)
        self.assertIn("24", failed.stdout)

        allowed = self.write_proto(
            {
                "src/components/Pager.jsx": "export function Pager() {\n"
                "  // quantity-ok: illustration count, not a fixture quantity\n"
                "  return <span>24</span>\n"
                "}\n"
            }
        )
        passed = self.run_check(allowed)
        self.assertEqual(passed.returncode, 0, passed.stdout + passed.stderr)
        self.assertIn("PASS literals", passed.stdout)
        self.assertIn("SKIP invariants", passed.stdout)

    def test_layout_numbers_and_src_data_are_not_literals(self):
        proto = self.write_proto(
            {
                "src/components/Layout.jsx": (
                    "export function Layout() {\n"
                    "  return (\n"
                    "    <div style={{ width: '50%', padding: 16 }} key={1}>\n"
                    '      <img width="100%" alt="tasks" />\n'
                    "      Tasks\n"
                    "    </div>\n"
                    "  )\n"
                    "}\n"
                ),
                "src/data/fixture.js": (
                    "export const asOf = '2026-10-14'\n"
                    "export const amount = '$1,234.50'\n"
                    "export const sessions = 40\n"
                ),
                "src/index.html": (
                    "<style>.bar { width: 40%; }</style>\n"
                    '<p style="width: 50%">Tasks</p>\n'
                ),
            }
        )
        result = self.run_check(proto)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS literals", result.stdout)

    def test_currency_duration_and_root_index_are_literals(self):
        proto = self.write_proto(
            {
                "src/components/Card.jsx": (
                    "export function Card() {\n"
                    "  return <p>Wait 3 days · $9.50</p>\n"
                    "}\n"
                ),
                "index.html": "<p>7</p>\n",
            }
        )
        result = self.run_check(proto)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL literals", result.stdout)
        self.assertIn("$9.50", result.stdout)
        self.assertIn("3 days", result.stdout)
        self.assertIn("index.html", result.stdout)
        self.assertIn("7", result.stdout)

    def test_local_copies_of_a_metric_fail(self):
        body = (
            "function countOpen(rows) {\n"
            "  return rows.filter((row) => row.status === 'open').length\n"
            "}\n"
            "export function View() {\n"
            '  return <span data-metric="openCount">{countOpen(rows)}</span>\n'
            "}\n"
        )
        proto = self.write_proto(
            {
                "src/components/Summary.jsx": body,
                "src/components/Detail.jsx": body.replace("View", "DetailView"),
            }
        )
        result = self.run_check(proto)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("FAIL cross-screen", result.stdout)
        self.assertIn("local copy countOpen", result.stdout)
        self.assertIn("PASS literals", result.stdout)

    def test_same_imported_selector_agrees(self):
        summary = (
            "import { openTaskCount } from '../data/selectors.js'\n"
            "export function Summary() {\n"
            '  return <span data-metric="openCount">{openTaskCount()}</span>\n'
            "}\n"
        )
        detail = summary.replace("Summary", "Detail")
        proto = self.write_proto(
            {
                "src/components/Summary.jsx": summary,
                "src/components/Detail.jsx": detail,
                "src/data/selectors.js": (
                    "export function openTaskCount() { return 0 }\n"
                ),
            }
        )
        result = self.run_check(proto)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PASS cross-screen", result.stdout)
        self.assertIn("PASS literals", result.stdout)


if __name__ == "__main__":
    unittest.main()
