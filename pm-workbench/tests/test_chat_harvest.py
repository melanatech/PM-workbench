"""PM-only chat harvest and memory listing. No assistant text, no auto-write."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

WORKBENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WORKBENCH / "scripts"))
import chat_harvest  # noqa: E402
import memory_harvest  # noqa: E402


def _turn(uuid, timestamp, text, *, role="user", entrypoint="cli"):
    return {
        "type": role,
        "uuid": uuid,
        "sessionId": "sess",
        "timestamp": timestamp,
        "entrypoint": entrypoint,
        "cwd": "/tmp/live",
        "message": {"role": role, "content": [{"type": "text", "text": text}]},
    }


class ChatHarvestTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.root = self.base / "live"
        self.root.mkdir()
        self.projects = self.base / "projects"
        self.workspace = self.base / "workspace"
        self.workspace.mkdir()
        slug = chat_harvest.project_slug(self.workspace)
        self.session_dir = self.projects / slug
        self.session_dir.mkdir(parents=True)
        fact = "We decided to ship the export on 2026-10-20 because the review passed."
        rows = [
            _turn("old", "2026-10-01T00:00:00.000Z", fact),
            _turn("ack", "2026-10-12T00:00:00.000Z", "thanks"),
            _turn(
                "assistant-fact",
                "2026-10-13T00:00:00.000Z",
                "We decided the assistant invented this commitment.",
                role="assistant",
            ),
            _turn("new", "2026-10-14T00:00:00.000Z", fact),
        ]
        (self.session_dir / "sess.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_keeps_pm_facts_only_and_advances_the_cursor(self):
        (self.root / "state").mkdir()
        (self.root / "state" / ".chat-harvest-cursor").write_text(
            "2026-10-01T00:00:00.000Z\n",
            encoding="utf-8",
        )
        summary = chat_harvest.harvest(
            self.root,
            projects_root=self.projects,
            workspaces=[self.workspace],
        )
        self.assertEqual(summary["kept"], 1)
        text = (self.root / summary["path"]).read_text(encoding="utf-8")
        self.assertIn("2026-10-14T00:00:00.000Z", text)
        self.assertNotIn("2026-10-01T00:00:00.000Z", text.split("## Candidates", 1)[-1])
        self.assertNotIn("assistant invented", text)
        self.assertNotIn("thanks", text)
        self.assertIn("No assistant text", text)
        cursor = (self.root / "state" / ".chat-harvest-cursor").read_text(encoding="utf-8").strip()
        self.assertEqual(cursor, "2026-10-14T00:00:00.000Z")

        again = chat_harvest.harvest(
            self.root,
            projects_root=self.projects,
            workspaces=[self.workspace],
        )
        self.assertEqual(again["kept"], 0)
        self.assertEqual(again["path"], "")

    def test_fact_filter_drops_acks_and_slash_commands(self):
        self.assertFalse(chat_harvest.is_fact_like("thanks"))
        self.assertFalse(chat_harvest.is_fact_like("/brief daily-brief please catch me up today"))
        self.assertTrue(
            chat_harvest.is_fact_like(
                "We decided to ship the export on 2026-10-20 because the review passed."
            )
        )


class MemoryHarvestTests(unittest.TestCase):
    def test_lists_notes_and_writes_nothing(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name)
        workspace = base / "workspace"
        workspace.mkdir()
        projects = base / "projects"
        slug = chat_harvest.project_slug(workspace)
        memory = projects / slug / "memory"
        memory.mkdir(parents=True)
        note = memory / "user_role.md"
        note.write_text(
            "---\ndescription: \"Role note\"\n---\n\n# Role\n\nPrincipal example.\n",
            encoding="utf-8",
        )
        before = note.read_text(encoding="utf-8")
        notes = memory_harvest.list_notes(projects, [workspace])
        rendered = memory_harvest.format_notes(notes)
        self.assertIn("user_role.md", rendered)
        self.assertIn("list only", rendered)
        self.assertEqual(note.read_text(encoding="utf-8"), before)
        self.assertFalse((workspace / "reference").exists())


if __name__ == "__main__":
    unittest.main()
