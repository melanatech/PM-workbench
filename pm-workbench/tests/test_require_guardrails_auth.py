#!/usr/bin/env python3
"""PreToolUse hook blocks prototypes/ only while the needs-auth cache lists ux_guardrails."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
HOOK = WORKBENCH / ".claude" / "hooks" / "require_guardrails_auth_for_prototypes.py"


class GuardrailsAuthHookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-guardrails-auth-"))
        (self.tmp / "prototypes").mkdir()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_hook(self, file_path, cache, raw=None, missing=False):
        if missing:
            cache_path = self.tmp / "no-such-cache.json"
        else:
            cache_path = self.tmp / "mcp-needs-auth-cache.json"
            if raw is not None:
                cache_path.write_text(raw, encoding="utf-8")
            else:
                cache_path.write_text(json.dumps(cache or {}), encoding="utf-8")
        payload = {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": "x"}}
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(self.tmp),
            "MCP_NEEDS_AUTH_CACHE": str(cache_path),
            "GUARDRAILS_SKIP_FILE": str(self.tmp / "no-skip"),
        }
        return subprocess.run(
            ["python3", str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def test_blocks_prototypes_when_cache_lists_ux_guardrails(self):
        result = self.run_hook(
            "prototypes/home/index.html",
            {"ux_guardrails": {"timestamp": 1, "ttlMs": 90000}},
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Guardrails is not signed in", result.stderr)
        self.assertIn("ux_guardrails", result.stderr)

    def test_allows_prototypes_when_cache_does_not_list_ux_guardrails(self):
        result = self.run_hook(
            "prototypes/home/index.html",
            {"plugin:slack:slack": {"timestamp": 1}},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_allows_outside_prototypes_even_when_listed(self):
        result = self.run_hook(
            "drafts/note.md",
            {"ux_guardrails": {"timestamp": 1, "ttlMs": 90000}},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_allows_prototypes_when_pm_skip_file_exists(self):
        skip = self.tmp / "guardrails-skip"
        skip.write_text("skip\n", encoding="utf-8")
        cache_path = self.tmp / "mcp-needs-auth-cache.json"
        cache_path.write_text(
            json.dumps({"ux_guardrails": {"timestamp": 1, "ttlMs": 90000}}),
            encoding="utf-8",
        )
        payload = {
            "tool_name": "Write",
            "tool_input": {"file_path": "prototypes/home/index.html", "content": "x"},
        }
        env = {
            **os.environ,
            "CLAUDE_PROJECT_DIR": str(self.tmp),
            "MCP_NEEDS_AUTH_CACHE": str(cache_path),
            "GUARDRAILS_SKIP_FILE": str(skip),
        }
        result = subprocess.run(
            ["python3", str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")

    def test_allows_when_cache_missing_or_unreadable(self):
        missing = self.run_hook("prototypes/home/index.html", None, missing=True)
        self.assertEqual(missing.returncode, 0, missing.stderr)
        broken = self.run_hook("prototypes/home/index.html", None, raw="{")
        self.assertEqual(broken.returncode, 0, broken.stderr)


if __name__ == "__main__":
    unittest.main()
