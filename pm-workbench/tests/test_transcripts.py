"""Tests for scripts/transcripts.py — user turns and surface labels."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import transcripts  # noqa: E402


class SurfaceTests(unittest.TestCase):
    def test_known_entrypoints(self):
        self.assertEqual(transcripts.surface_from_entrypoint("cli"), "terminal")
        self.assertEqual(transcripts.surface_from_entrypoint("sdk-cli"), "headless")
        self.assertEqual(transcripts.surface_from_entrypoint("claude-vscode"), "panel")

    def test_unknown_stays_raw_and_blank_stays_blank(self):
        self.assertEqual(transcripts.surface_from_entrypoint("remote"), "remote")
        self.assertEqual(transcripts.surface_from_entrypoint(""), "")
        self.assertEqual(transcripts.surface_from_entrypoint("  cli  "), "terminal")


class UserTurnTests(unittest.TestCase):
    def test_iter_user_turns_skips_meta_sidechain_and_tool_results(self):
        tmp = Path(tempfile.mkdtemp(prefix="pmwb-turns-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        path = tmp / "sess.jsonl"
        rows = [
            {
                "type": "user",
                "uuid": "human",
                "sessionId": "sess",
                "timestamp": "2026-10-12T12:00:00.000Z",
                "entrypoint": "claude-vscode",
                "cwd": "/tmp/live",
                "message": {"role": "user", "content": [{"type": "text", "text": "done with TODO-7"}]},
            },
            {
                "type": "user",
                "uuid": "meta",
                "timestamp": "2026-10-12T12:00:01.000Z",
                "entrypoint": "cli",
                "isMeta": True,
                "message": {"role": "user", "content": "meta noise"},
            },
            {
                "type": "user",
                "uuid": "side",
                "timestamp": "2026-10-12T12:00:02.000Z",
                "entrypoint": "cli",
                "isSidechain": True,
                "message": {"role": "user", "content": "sidechain"},
            },
            {
                "type": "user",
                "uuid": "tool",
                "timestamp": "2026-10-12T12:00:03.000Z",
                "entrypoint": "sdk-cli",
                "sourceToolAssistantUUID": "a",
                "message": {"role": "user", "content": "tool output done with TODO-7"},
            },
            {
                "type": "assistant",
                "uuid": "a",
                "timestamp": "2026-10-12T12:00:04.000Z",
                "entrypoint": "claude-vscode",
                "message": {"role": "assistant", "content": "ok"},
            },
        ]
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        turns = list(transcripts.iter_user_turns([path]))
        self.assertEqual(len(turns), 1)
        turn = turns[0]
        self.assertEqual(turn.timestamp, "2026-10-12T12:00:00.000Z")
        self.assertEqual(turn.session_id, "sess")
        self.assertEqual(turn.entrypoint, "claude-vscode")
        self.assertIn("TODO-7", turn.text)
        self.assertEqual(turn.uuid, "human")


if __name__ == "__main__":
    unittest.main()
