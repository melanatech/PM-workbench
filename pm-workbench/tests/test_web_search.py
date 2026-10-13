#!/usr/bin/env python3
"""Tests for scripts/web_search.py."""
import json
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest import mock

WORKBENCH = Path(__file__).resolve().parents[1]
SCRIPT = WORKBENCH / "scripts" / "web_search.py"

sys.path.insert(0, str(WORKBENCH / "scripts"))
import web_search as ws  # noqa: E402


SAMPLE_DDG = """
<div class="result__body">
  <h2 class="result__title">
    <a class="result__a" href="https://squareup.com/help/us/en/topic/reports">Square Reports</a>
  </h2>
  <a class="result__snippet">Sales and transactions reports overview.</a>
</div>
"""

SAMPLE_BING = """
<li class="b_algo"><h2><a href="https://www.bing.com/ck/a?!&&p=x&u=a1aHR0cHM6Ly9zcXVhcmV1cC5jb20vaGVscC91cy9lbi90b3BpYy9yZXBvcnRz">Reports | Square</a></h2>
<div class="b_caption"><p>Help center reports.</p></div></li>
"""

SAMPLE_STARTPAGE = """
<div class="result">
  <a class="result-title result-link" href="https://squareup.com/help/us/en/topic/reports">
    <h2 class="wgl-title">Reports | Square Support</h2>
  </a>
  <p class="description">Sales and custom reports in the Square Dashboard.</p>
</div>
<div class="result">
  <a class="result-title result-link" href="https://www.merriam-webster.com/dictionary/merchant">
    <h2>Merchant Definition</h2>
  </a>
  <p class="description">Dictionary junk should be filtered.</p>
</div>
<div class="result">
  <a class="result-title result-link" href="/clev?event=Sp_x9&amp;sc=abc">
    <h2>Tracking junk</h2>
  </a>
</div>
"""


class WebSearchUnitTests(unittest.TestCase):
    def test_duckduckgo_parse(self):
        with mock.patch.object(ws, "_http", return_value=SAMPLE_DDG):
            hits = ws.search_duckduckgo("Square reports", max_results=5)
        self.assertEqual(hits[0]["url"], "https://squareup.com/help/us/en/topic/reports")
        self.assertIn("Square", hits[0]["title"])

    def test_bing_decode(self):
        with mock.patch.object(ws, "_http", return_value=SAMPLE_BING):
            hits = ws.search_bing("Square reports", max_results=5)
        self.assertTrue(hits[0]["url"].startswith("https://squareup.com/help"))

    def test_startpage_parse_filters_junk(self):
        with mock.patch.object(ws, "_startpage_form_fields", return_value={"sc": "x"}):
            with mock.patch.object(ws, "_http", return_value=SAMPLE_STARTPAGE):
                hits = ws.search_startpage("Square reports help", max_results=5)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["provider"], "startpage")
        self.assertIn("squareup.com/help", hits[0]["url"])
        self.assertIn("Sales", hits[0]["snippet"])

    def test_fallback_uses_startpage_when_ddg_empty(self):
        good = [
            {
                "title": "Analytics discrepancies - Shopify",
                "url": "https://help.shopify.com/en/manual/reports-and-analytics/discrepancies",
                "snippet": "Why numbers differ",
                "provider": "startpage",
            }
        ]
        with mock.patch.object(ws, "search_duckduckgo", return_value=[]):
            with mock.patch.object(ws, "search_startpage", return_value=good):
                with mock.patch.object(ws, "search_bing", return_value=[]) as bing:
                    hits = ws.search("merchant analytics explanations", max_results=3)
                    bing.assert_not_called()
        self.assertEqual(hits[0]["provider"], "startpage")
        self.assertIn("shopify.com", hits[0]["url"])

    def test_skips_provider_with_only_homepages(self):
        weak = [
            {
                "title": "Square",
                "url": "https://squareup.com/us/en",
                "snippet": "",
                "provider": "bing",
            }
        ]
        good = [
            {
                "title": "Reports help",
                "url": "https://squareup.com/help/us/en/topic/reports",
                "snippet": "reports",
                "provider": "startpage",
            }
        ]
        with mock.patch.object(ws, "search_duckduckgo", return_value=[]):
            with mock.patch.object(ws, "search_startpage", return_value=good):
                with mock.patch.object(ws, "search_bing", return_value=weak):
                    hits = ws.search("Square POS reporting help", max_results=3)
        self.assertEqual(hits[0]["url"], good[0]["url"])

    def test_junk_urls_filtered(self):
        self.assertTrue(ws._is_junk_url("https://www.merriam-webster.com/dictionary/x"))
        self.assertTrue(ws._is_junk_url("https://app.example.com/login"))
        self.assertFalse(ws._is_junk_url("https://help.shopify.com/en/manual/reports"))

    def test_cli_json(self):
        with mock.patch.object(
            ws,
            "search",
            return_value=[
                {
                    "title": "A",
                    "url": "https://example.com/a",
                    "snippet": "s",
                    "provider": "startpage",
                }
            ],
        ):
            buf = StringIO()
            old = sys.stdout
            sys.stdout = buf
            try:
                code = ws.main(["--json", "test query"])
            finally:
                sys.stdout = old
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(buf.getvalue())[0]["url"], "https://example.com/a")


@unittest.skipUnless(
    __import__("os").environ.get("PMWB_NET_TESTS") == "1",
    "set PMWB_NET_TESTS=1 to hit live search endpoints",
)
class WebSearchLiveTests(unittest.TestCase):
    def test_live_square_query(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--urls-only",
                "--max",
                "5",
                "Square POS reporting help",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        urls = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        self.assertTrue(urls)
        self.assertTrue(any("square" in u.lower() for u in urls), urls)

    def test_live_open_ended_not_dictionary(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--json",
                "--max",
                "5",
                "merchant analytics explanations why numbers changed",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        hits = json.loads(result.stdout)
        self.assertTrue(hits)
        joined = " ".join(h["url"] for h in hits).lower()
        self.assertNotIn("merriam-webster", joined)
        self.assertNotIn("dictionary.cambridge", joined)


if __name__ == "__main__":
    unittest.main()
