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

    def test_fallback_to_bing_when_ddg_empty(self):
        with mock.patch.object(ws, "search_duckduckgo", return_value=[]):
            with mock.patch.object(
                ws,
                "search_bing",
                return_value=[
                    {
                        "title": "A",
                        "url": "https://example.com/a",
                        "snippet": "",
                        "provider": "bing",
                    }
                ],
            ):
                hits = ws.search("q", max_results=3)
        self.assertEqual(hits[0]["provider"], "bing")

    def test_cli_json(self):
        with mock.patch.object(
            ws,
            "search",
            return_value=[
                {
                    "title": "A",
                    "url": "https://example.com/a",
                    "snippet": "s",
                    "provider": "bing",
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


if __name__ == "__main__":
    unittest.main()
