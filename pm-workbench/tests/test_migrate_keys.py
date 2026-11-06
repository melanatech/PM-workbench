"""migrate_keys: merge subfolder registers into the project key, archive hook-run transcripts."""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[2] / "session-memory"
sys.path.insert(0, str(MODULE))
sys.path.insert(0, str(MODULE / "hooks"))
import migrate_keys as mk  # noqa: E402

SID_A = "11111111-1111-1111-1111-111111111111"
SID_B = "22222222-2222-2222-2222-222222222222"
OLD = time.time() - 3600


def entry(eid, section, text, date, supersedes=()):
    return {"id": eid, "section": section, "text": text, "date": date, "supersedes": list(supersedes), "dropped": False}


def write_jsonl(path, rows, old=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    if old:
        os.utime(path, (OLD, OLD))


def chat_row(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.root = self.tmp / "proj"
        (self.root / "outputs" / "v3").mkdir(parents=True)
        (self.root / "drafts").mkdir()
        (self.root / "my-notes").mkdir()
        self.home = self.tmp / "sm"
        self.projects = self.tmp / "projects"
        self.dest = mk.encode_memory(str(self.root))

    def tearDown(self):
        self._tmp.cleanup()

    def run_main(self, *extra):
        return mk.main(["--root", str(self.root), "--home", str(self.home), "--projects", str(self.projects), *extra])


class Registers(Fixture):
    def test_same_session_in_two_keys_is_merged_and_supersession_survives(self):
        sub = self.home / (self.dest + "-outputs-v3")
        write_jsonl(self.home / self.dest / f"{SID_A}.jsonl", [
            entry("e1", "Goal", "Ship cards", "2026-11-03T10:00:00"),
            entry("e2", "Decisions", "Use CSV", "2026-11-03T10:05:00")])
        write_jsonl(sub / f"{SID_A}.jsonl", [
            entry("e1", "Decisions", "Vendor A", "2026-11-03T11:00:00"),
            entry("e2", "Decisions", "Vendor B", "2026-11-03T11:30:00", ["e1"]),
            entry("e3", "Goal", "Contract vendor B", "2026-11-03T11:45:00")])
        self.assertEqual(self.run_main("--apply"), 0)
        import common
        merged = common.load_entries(str(self.home / self.dest / f"{SID_A}.jsonl"))
        self.assertEqual(len(merged), 5)
        self.assertEqual(len({e["id"] for e in merged}), 5)
        active = sorted(e["text"] for e in common.active_entries(merged))
        self.assertEqual(active, ["Contract vendor B", "Ship cards", "Use CSV", "Vendor B"])
        self.assertFalse(sub.exists())

    def test_register_only_in_a_subfolder_is_moved(self):
        sub = self.home / (self.dest + "-drafts")
        write_jsonl(sub / f"{SID_B}.jsonl", [entry("e1", "Decisions", "Keep it short", "2026-11-04T09:00:00")])
        (sub / "index.json").write_text(json.dumps({SID_B: {"first": "a", "last": "b", "captures": 2, "goal": "Brief"}}))
        self.run_main("--apply")
        self.assertTrue((self.home / self.dest / f"{SID_B}.jsonl").exists())
        index = json.loads((self.home / self.dest / "index.json").read_text())
        self.assertEqual(index[SID_B]["goal"], "Brief")

    def test_index_records_for_one_session_are_combined(self):
        into = {SID_A: {"first": "2026-11-03T10:00:00", "last": "2026-11-03T10:30:00", "captures": 3, "goal": "Old"}}
        other = {SID_A: {"first": "2026-11-03T09:00:00", "last": "2026-11-03T12:00:00", "captures": 2, "goal": "New"}}
        out = mk.merge_index(into, other)[SID_A]
        self.assertEqual((out["first"], out["last"], out["captures"], out["goal"]),
                         ("2026-11-03T09:00:00", "2026-11-03T12:00:00", 5, "Old"))
        self.assertEqual(out["goals"], ["Old", "New"])

    def test_a_similarly_named_other_project_is_left_alone(self):
        other = self.home / (self.dest + "-other-project")   # no such folder under the root
        write_jsonl(other / f"{SID_B}.jsonl", [entry("e1", "Decisions", "x", "2026-11-04T09:00:00")])
        self.run_main("--apply")
        self.assertTrue((other / f"{SID_B}.jsonl").exists())

    def test_a_folder_with_dashes_in_its_name_resolves(self):
        sub = self.home / (self.dest + "-my-notes")
        write_jsonl(sub / f"{SID_B}.jsonl", [entry("e1", "Decisions", "x", "2026-11-04T09:00:00")])
        self.run_main("--apply")
        self.assertTrue((self.home / self.dest / f"{SID_B}.jsonl").exists())

    def test_dry_run_changes_nothing(self):
        sub = self.home / (self.dest + "-drafts")
        write_jsonl(sub / f"{SID_B}.jsonl", [entry("e1", "Decisions", "x", "2026-11-04T09:00:00")])
        self.run_main()
        self.assertTrue((sub / f"{SID_B}.jsonl").exists())
        self.assertFalse((self.home / self.dest).exists())


class Transcripts(Fixture):
    def folder(self, suffix=""):
        return self.projects / (mk.encode_claude(str(self.root)) + suffix)

    def test_only_hook_runs_move_and_a_real_chat_stays(self):
        folder = self.folder()
        plumbing = [chat_row("Judge this team-facing draft. Read it.")] + [{"type": "assistant"}] * 30
        write_jsonl(folder / f"{SID_A}.jsonl", plumbing)
        write_jsonl(folder / "33333333-3333-3333-3333-333333333333.jsonl",
                    [chat_row("# Session register instructions (headless model)\n\nYou keep a register")] * 2)
        write_jsonl(folder / "44444444-4444-4444-4444-444444444444.jsonl",
                    [chat_row("Does this new prompt continue one of these earlier sessions? Prefer none.")])
        write_jsonl(folder / (SID_B.replace("2", "5") + ".jsonl"), [chat_row("lets pick up reseller commission")] * 400)
        write_jsonl(folder / "66666666-6666-6666-6666-666666666666.jsonl",
                    [chat_row("Judge this team-facing draft")] * 500)   # same opening, but a long chat
        self.run_main("--apply")
        archive = self.home / "headless-archive" / folder.name
        self.assertEqual(len(list(archive.glob("*.jsonl"))), 3)
        self.assertEqual(sorted(p.name[:8] for p in folder.glob("*.jsonl")), ["55555555", "66666666"])

    def test_a_run_written_in_the_last_two_minutes_is_left_alone(self):
        folder = self.folder()
        write_jsonl(folder / f"{SID_A}.jsonl", [chat_row("Judge this team-facing draft")], old=False)
        self.run_main("--apply")
        self.assertTrue((folder / f"{SID_A}.jsonl").exists())

    def test_subfolder_project_directories_are_covered_and_other_projects_are_not(self):
        sub = self.folder("-outputs-v3")
        other = self.projects / "-Users-someone-else"
        write_jsonl(sub / f"{SID_A}.jsonl", [chat_row("Judge this team-facing draft")])
        write_jsonl(other / f"{SID_B}.jsonl", [chat_row("Judge this team-facing draft")])
        self.run_main("--apply")
        self.assertFalse((sub / f"{SID_A}.jsonl").exists())
        self.assertTrue((other / f"{SID_B}.jsonl").exists())

    def test_dry_run_moves_nothing(self):
        folder = self.folder()
        write_jsonl(folder / f"{SID_A}.jsonl", [chat_row("Judge this team-facing draft")])
        self.run_main()
        self.assertTrue((folder / f"{SID_A}.jsonl").exists())
        self.assertFalse((self.home / "headless-archive").exists())


if __name__ == "__main__":
    unittest.main()
