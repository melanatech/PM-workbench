"""Background jobs stay resumable but read as jobs, not chats, in the resume list."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_scheduled  # noqa: E402


class SchedulerNames(unittest.TestCase):
    def test_a_scheduled_run_is_named_for_its_task(self):
        command = run_scheduled.build_command("claude", "do the thing", "weekly-brief")
        self.assertEqual(command[command.index("-n") + 1], "scheduled: weekly-brief")

    def test_no_task_means_no_name_flag(self):
        self.assertNotIn("-n", run_scheduled.build_command("claude", "do the thing"))

    def test_a_scheduled_run_is_still_saved(self):
        self.assertNotIn("--no-session-persistence", run_scheduled.build_command("claude", "x", "t"))


if __name__ == "__main__":
    unittest.main()
