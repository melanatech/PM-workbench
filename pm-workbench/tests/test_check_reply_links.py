#!/usr/bin/env python3
"""Stop hook must warn about unlinked paths without asking for another reply."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
HOOK = WORKBENCH / ".claude" / "hooks" / "check_reply_links.py"


class ReplyLinkStopTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pmwb-reply-links-"))
        (self.tmp / "registers").mkdir()
        (self.tmp / "registers" / "todos.csv").write_text("id\n", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_hook(self, transcript: Path):
        payload = {"transcript_path": str(transcript)}
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.tmp)}
        return subprocess.run(
            ["python3", str(HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def write_transcript(self, text: str) -> Path:
        path = self.tmp / "session.jsonl"
        row = {
            "type": "assistant",
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
        }
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        return path

    def test_unlinked_path_warns_and_exits_zero(self):
        transcript = self.write_transcript("Queued in registers/todos.csv with nothing added.")
        result = self.run_hook(transcript)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("registers/todos.csv", result.stderr)
        self.assertNotIn("Rewrite the reply", result.stderr)

    def test_linked_path_is_silent(self):
        transcript = self.write_transcript(
            "Queued in [registers/todos.csv](registers/todos.csv)."
        )
        result = self.run_hook(transcript)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
