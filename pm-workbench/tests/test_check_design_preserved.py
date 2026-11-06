"""check_design_preserved.py passes added content and fails a redesign."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from check_design_preserved import compare  # noqa: E402

BEFORE = """<html><head><style>.card { color: red; }</style></head>
<body><div class="wrap"><section class="card"><h2>Orders</h2></section></div></body></html>"""

MORE_CONTENT = """<html><head><style>.card  {  color: red; }</style></head>
<body><div class="wrap"><section class="card"><h2>Orders</h2></section>
<section class="card"><h2>Payments</h2></section></div></body></html>"""

NEW_CSS = BEFORE.replace("color: red", "color: blue")

NEW_LAYOUT = """<html><head><style>.card { color: red; }</style></head>
<body><main><article class="tile"><h2>Orders</h2></article></main></body></html>"""


class CheckDesignPreservedTests(unittest.TestCase):
    def test_added_content_of_an_existing_kind_passes(self):
        self.assertEqual(compare(BEFORE, MORE_CONTENT), [])

    def test_changed_style_fails(self):
        problems = compare(BEFORE, NEW_CSS)
        self.assertTrue(any("<style>" in p for p in problems))

    def test_new_layout_fails(self):
        problems = compare(BEFORE, NEW_LAYOUT)
        self.assertTrue(any("skeleton" in p for p in problems))


if __name__ == "__main__":
    unittest.main()
